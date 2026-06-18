from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .goal_tree import GoalNode


@dataclass(slots=True)
class ConfirmationRequest:
    node_id: str
    description: str
    impact: str
    options: list[str]


class ConfirmationGate:
    _DANGEROUS = ("delete", "remove", "destroy", "kill", "rm -rf", "payment", "send", "network")

    def requires_confirmation(self, node: GoalNode) -> bool:
        if node.destructive:
            return True
        haystack = f"{node.text} {node.tool or ''}".lower()
        return any(token in haystack for token in self._DANGEROUS)

    def build_request(self, node: GoalNode, step_id: Optional[str] = None) -> ConfirmationRequest:
        impact = self._describe_impact(node)
        return ConfirmationRequest(
            node_id=step_id or node.id,
            description=node.text,
            impact=impact,
            options=["approve", "skip", "abort", "explain"],
        )

    def _describe_impact(self, node: GoalNode) -> str:
        haystack = f"{node.text} {node.tool or ''}".lower()
        if "delete" in haystack or "remove" in haystack or "rm -rf" in haystack:
            return "May delete files or directories"
        if "kill" in haystack:
            return "May stop a running process"
        if "payment" in haystack:
            return "May move money or trigger a financial action"
        if "send" in haystack or "network" in haystack:
            return "May send data over the network"
        return "Potentially destructive operation"
