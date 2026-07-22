from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Awaitable, Callable, Optional


from .confirmation_gate import ConfirmationGate, ConfirmationRequest
from .execution_monitor import ExecutionMonitor
from .goal_planner import GoalPlanner
from .goal_tree import GoalNode, GoalStatus, GoalTree
from .intent_renderer import IntentRenderer
from .retry_engine import RetryEngine

ConfirmationResolver = Callable[[ConfirmationRequest], Awaitable[str]]


class _AbortGoal(Exception):
    """Raised internally when the user aborts a destructive goal."""

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id)
        self.node_id = node_id


class IntentKernel:
    """Goal-executor that plans, walks, monitors, retries, and confirms."""

    def __init__(
        self,
        agent_manager: Any,
        planner: GoalPlanner | None = None,
        renderer: IntentRenderer | None = None,
        monitor: ExecutionMonitor | None = None,
        retry_engine: RetryEngine | None = None,
        confirmation_gate: ConfirmationGate | None = None,
        memory: Any | None = None,
        memory_top_k: int = 3,
        max_retries: int = 2,
        tool_timeout: float = 30.0,
    ) -> None:
        self.agent_manager = agent_manager
        kernel = getattr(agent_manager, "kernel", None)
        self.planner = planner or GoalPlanner(
            llm_manager=getattr(kernel, "llm", None),
            available_tools=getattr(agent_manager, "tools", {}).keys(),
            memory=getattr(kernel, "memory", None),
            memory_top_k=getattr(kernel, "memory_top_k", 3),
        )
        self.renderer = renderer or IntentRenderer()
        self.monitor = monitor or ExecutionMonitor(timeout_seconds=tool_timeout)
        self.retry_engine = retry_engine or RetryEngine()
        self.confirmation_gate = confirmation_gate or ConfirmationGate()
        self.memory = memory or getattr(kernel, "memory", None)
        self.memory_top_k = memory_top_k
        self.max_retries = max_retries
        self.tool_timeout = tool_timeout
        self._last_tree: Optional[GoalTree] = None
        # Idempotency for confirmation: (node_text, tool) already approved this session.
        self._approved: set[tuple[str, Optional[str]]] = set()

    # ------------------------------------------------------------------
    # Public API — single-shot request/response (collects all stream frames)
    # ------------------------------------------------------------------
    async def receive(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        resolver: ConfirmationResolver | None = None,
    ) -> dict[str, Any]:
        updates: list[dict[str, Any]] = []
        async for message in self.receive_streaming(
            text, context=context, resolver=resolver
        ):
            updates.append(message)
        if not updates:
            return {"ok": False, "error": "Intent produced no response"}
        final = updates[-1]
        if final.get("type") == "goal_update":
            final = {
                "ok": True,
                "type": "goal_complete",
                "summary": (
                    self.renderer.render(self._last_tree) if self._last_tree else ""
                ),
                "tree": self._last_tree.to_dict() if self._last_tree else None,
            }
        final["updates"] = updates[:-1]
        return final

    # ------------------------------------------------------------------
    # Public API — streaming
    # ------------------------------------------------------------------
    async def receive_streaming(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        resolver: ConfirmationResolver | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ctx = context or {}
        try:
            tree = await self.planner.decompose(text, context=ctx)
        except Exception as exc:
            yield {"ok": False, "type": "plan_failed", "error": str(exc)}
            return

        self._last_tree = tree
        if tree.clarification_needed:
            yield {
                "ok": True,
                "type": "clarification_needed",
                "question": tree.clarification_question
                or "Could you clarify your goal?",
                "tree": tree.to_dict(),
            }
            return

        yield {
            "ok": True,
            "type": "goal_update",
            "tree": tree.to_dict(),
            "message": f"Planning complete. {len(tree.leaf_nodes())} steps queued.",
            "awaiting_confirmation": False,
        }

        try:
            await self._execute_streaming(tree, resolver)
        except _AbortGoal as exc:
            self._mark_descendants_blocked(tree, exc.node_id)
            yield {
                "ok": True,
                "type": "goal_update",
                "tree": tree.to_dict(),
                "message": "Goal aborted by user.",
                "awaiting_confirmation": False,
            }
            yield {
                "ok": True,
                "type": "goal_complete",
                "summary": self.renderer.render(tree),
                "tree": tree.to_dict(),
                "aborted": True,
            }
            return
        except Exception as exc:
            yield {
                "ok": False,
                "type": "goal_failed",
                "error": str(exc),
                "tree": tree.to_dict(),
            }
            return

        tree.root.mark_done(self.renderer.render(tree))
        await self._persist_memory(tree)
        yield {
            "ok": True,
            "type": "goal_complete",
            "summary": self.renderer.render(tree),
            "tree": tree.to_dict(),
        }

    # ------------------------------------------------------------------
    # Tree walking with monitoring, retry, and confirmation
    # ------------------------------------------------------------------
    async def _execute_streaming(
        self,
        tree: GoalTree,
        resolver: ConfirmationResolver | None,
    ) -> None:
        for child in tree.root.children:
            await self._walk(child, tree, resolver)

    async def _walk(
        self,
        node: GoalNode,
        tree: GoalTree,
        resolver: ConfirmationResolver | None,
    ) -> None:
        node.status = GoalStatus.RUNNING
        self.monitor.emit("TASK_STARTED", node.id, node.text)

        if node.children:
            for child in node.children:
                await self._walk(child, tree, resolver)
            node.mark_done()
            self.monitor.emit("TASK_DONE", node.id, node.text)
            return

        # Leaf: confirmation gate first.
        if self._needs_confirmation(node):
            approved = await self._handle_confirmation(node, tree, resolver)
            if not approved:
                return

        # Execute with retry ladder.
        attempt = 0
        while True:
            attempt += 1
            try:
                result = await asyncio.wait_for(
                    self._execute_leaf(node), timeout=self.tool_timeout
                )
                node.mark_done(result)
                self.monitor.emit("TASK_DONE", node.id, node.text)
                return
            except asyncio.TimeoutError:
                error = f"Tool '{node.tool}' timed out after {self.tool_timeout}s"
            except (
                Exception
            ) as exc:  # noqa: BLE001 — surface any tool failure for retry
                error = str(exc) or exc.__class__.__name__

            self.monitor.emit("TASK_FAILED", node.id, error)
            decision = self.retry_engine.decide(node, error)
            if not decision.should_retry or attempt > self.max_retries:
                node.mark_failed(error)
                raise RuntimeError(error)
            # Retry the same leaf with its original tool binding. The failed
            # attempt has already been recorded by RetryEngine.decide().
            yield_frame = {
                "ok": True,
                "type": "goal_update",
                "tree": tree.to_dict(),
                "message": f"Retrying '{node.text}' after: {error}",
                "awaiting_confirmation": False,
            }
            # Streaming callers pick this up via the monitor log; we continue the loop.
            self.monitor.emit("TASK_RETRY", node.id, yield_frame["message"])

    # ------------------------------------------------------------------
    # Confirmation gate
    # ------------------------------------------------------------------
    def _needs_confirmation(self, node: GoalNode) -> bool:
        key = (node.text, node.tool)
        if key in self._approved:
            return False
        return self.confirmation_gate.requires_confirmation(node)

    async def _handle_confirmation(
        self,
        node: GoalNode,
        tree: GoalTree,
        resolver: ConfirmationResolver | None,
    ) -> bool:
        request = self.confirmation_gate.build_request(node, step_id=node.id)
        if resolver is None:
            # No interactive resolver available — default to skip so the goal
            # still completes without silently running destructive ops.
            node.status = GoalStatus.BLOCKED
            node.error = "Destructive step skipped (no confirmation resolver)"
            self.monitor.emit("TASK_SKIPPED", node.id, node.error)
            return False

        decision = await resolver(request)
        if decision == "approve":
            self._approved.add((node.text, node.tool))
            return True
        if decision == "skip":
            node.status = GoalStatus.BLOCKED
            node.error = "Skipped by user"
            self.monitor.emit("TASK_SKIPPED", node.id, node.error)
            return False
        if decision == "abort":
            raise _AbortGoal(node.id)
        # "explain" or anything else: treat as skip for safety.
        node.status = GoalStatus.BLOCKED
        node.error = "Skipped (unrecognised confirmation response)"
        self.monitor.emit("TASK_SKIPPED", node.id, node.error)
        return False

    # ------------------------------------------------------------------
    # Leaf execution via AgentManager
    # ------------------------------------------------------------------
    async def _execute_leaf(self, node: GoalNode) -> str:
        if node.tool and hasattr(self.agent_manager, "_execute_tool_call"):
            outcome = await self.agent_manager._execute_tool_call(
                node.tool, node.tool_params or {}
            )
            if isinstance(outcome, str):
                if outcome.lower().startswith("unknown tool"):
                    return str(await self.agent_manager.execute(node.text))
                return outcome
            if isinstance(outcome, dict):
                error = str(outcome.get("error", ""))
                if outcome.get("ok") is True and "result" in outcome:
                    return str(outcome["result"])
                if "unknown tool" in error.lower():
                    return str(await self.agent_manager.execute(node.text))
                raise RuntimeError(error or "Tool execution failed")
        if hasattr(self.agent_manager, "execute"):
            return str(await self.agent_manager.execute(node.text))
        raise RuntimeError("No execution backend configured")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _mark_descendants_blocked(self, tree: GoalTree, aborted_node_id: str) -> None:
        aborted = next((n for n in tree.iter_nodes() if n.id == aborted_node_id), None)
        if aborted is None:
            return

        def block(node: GoalNode) -> None:
            if node.status in (GoalStatus.PENDING, GoalStatus.RUNNING):
                node.status = GoalStatus.BLOCKED
                node.error = "Blocked by upstream abort"
            for child in node.children:
                block(child)

        block(aborted)

    async def _persist_memory(self, tree: GoalTree) -> None:
        if self.memory is None or not hasattr(self.memory, "store_text"):
            return
        try:
            payload = tree.to_dict()
            # Store the root goal text as the embedding key plus a compact
            # outcome summary so future planning can retrieve it.
            summary = self.renderer.render(tree)
            await self.memory.store_text(
                tree.root_goal,
                metadata={"kind": "intent_goal", "summary": summary, "tree": payload},
            )
        except Exception:
            # Memory persistence must never break goal completion.
            pass
