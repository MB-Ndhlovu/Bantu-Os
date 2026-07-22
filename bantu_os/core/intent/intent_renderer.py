from __future__ import annotations

from .goal_tree import GoalNode, GoalStatus, GoalTree


class IntentRenderer:
    def render(self, tree: GoalTree, verbose: bool = False) -> str:
        lines = [f"Goal: {tree.root_goal}"]
        for child in tree.root.children:
            self._render_node(
                child,
                lines,
                prefix="",
                is_last=child is tree.root.children[-1],
                verbose=verbose,
            )
        return "\n".join(lines)

    def _render_node(
        self,
        node: GoalNode,
        lines: list[str],
        prefix: str,
        is_last: bool,
        verbose: bool,
    ) -> None:
        status_symbol = {
            GoalStatus.PENDING: "○",
            GoalStatus.RUNNING: "⟳",
            GoalStatus.DONE: "✓",
            GoalStatus.FAILED: "✗",
            GoalStatus.BLOCKED: "⊘",
        }[node.status]
        connector = "└─" if is_last else "├─"
        extra = f" [{node.tool}]" if verbose and node.tool else ""
        lines.append(f"{prefix}{connector} {status_symbol} {node.text}{extra}")
        next_prefix = f"{prefix}{'   ' if is_last else '│  '}"
        for index, child in enumerate(node.children):
            self._render_node(
                child, lines, next_prefix, index == len(node.children) - 1, verbose
            )
