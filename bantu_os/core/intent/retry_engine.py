from __future__ import annotations

from dataclasses import dataclass

from .goal_tree import GoalNode, RetryRecord


@dataclass(slots=True)
class RetryDecision:
    should_retry: bool
    explanation: str = ""


class RetryEngine:
    def decide(self, node: GoalNode, error: str) -> RetryDecision:
        if node.retry_count >= 2:
            return RetryDecision(False, "Retry limit reached")
        node.retry_history.append(RetryRecord(reason="retry", error=error, attempted_plan=node.text))
        node.retry_count += 1
        return RetryDecision(True, "Retry scheduled")
