from __future__ import annotations

from dataclasses import dataclass

from .goal_tree import GoalNode


@dataclass(slots=True)
class ConfirmationRequest:
    node_id: str
    description: str
    impact: str


class ConfirmationGate:
    def requires_confirmation(self, node: GoalNode) -> bool:
        return node.destructive

    def build_request(self, node: GoalNode) -> ConfirmationRequest:
        return ConfirmationRequest(
            node_id=node.id,
            description=node.text,
            impact="Potentially destructive operation",
        )
