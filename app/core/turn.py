"""Per-request turn context: tool-call budget and cost accumulation (R12).

Set by the Captain at the start of every user-triggered turn; read by agents (tool budget)
and by the LLM gateway (tier / tokens / INR). Lives in a contextvar so concurrent requests
never share counters.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field


class ToolBudgetExceeded(RuntimeError):
    pass


@dataclass
class TurnContext:
    case_id: str
    subject_id: str
    actor_id: str
    channel: str
    session_id: str | None = None
    max_tool_calls: int = 30
    tool_calls: int = 0
    llm_calls: int = 0
    tokens: int = 0
    cost_inr: float = 0.0
    tier: int = 0  # highest tier used in this turn
    offer_made: bool = False
    language: str = "hi"
    degraded: bool = False
    degrade_reasons: list[str] = field(default_factory=list)

    def count_tool_call(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > self.max_tool_calls:
            raise ToolBudgetExceeded(
                f"Turn {self.case_id} exceeded {self.max_tool_calls} tool calls"
            )

    def add_llm(self, tier: int, tokens: int, cost_inr: float) -> None:
        self.llm_calls += 1
        self.tokens += tokens
        self.cost_inr += cost_inr
        self.tier = max(self.tier, tier)

    def cost_summary(self) -> dict:
        return {
            "tier": self.tier,
            "llm_calls": self.llm_calls,
            "tokens": self.tokens,
            "cost_inr": round(self.cost_inr, 4),
            "tool_calls": self.tool_calls,
        }


_current: contextvars.ContextVar[TurnContext | None] = contextvars.ContextVar(
    "saarthi_turn", default=None
)


def current_turn() -> TurnContext | None:
    return _current.get()


def set_turn(ctx: TurnContext | None) -> contextvars.Token:
    return _current.set(ctx)


def reset_turn(token: contextvars.Token) -> None:
    _current.reset(token)
