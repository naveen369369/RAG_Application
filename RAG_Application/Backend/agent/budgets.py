from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class BudgetTracker:
    """
    Tracks four hard budget limits for an agent run.
    Call record_step() after every LLM call (including mid-loop calls).
    Call check() after every tool_node to enforce limits.
    """
    max_iterations: int = 8
    max_tokens: int = 6000
    max_cost_usd: float = 0.02
    wall_clock_sec: float = 30.0

    # Groq llama-3.3-70b-versatile pricing (update when model changes)
    cost_per_input_token: float = 0.0000003    # $0.30 / 1M tokens
    cost_per_output_token: float = 0.0000006   # $0.60 / 1M tokens

    _iterations: int = field(default=0, init=False, repr=False)
    _tokens_used: int = field(default=0, init=False, repr=False)
    _cost_usd: float = field(default=0.0, init=False, repr=False)
    _start_time: float = field(default_factory=time.monotonic, init=False, repr=False)

    def record_step(self, input_tokens: int, output_tokens: int) -> None:
        """Must be called inside llm_node on EVERY iteration — not just the last."""
        self._iterations += 1
        self._tokens_used += input_tokens + output_tokens
        self._cost_usd += (
            input_tokens * self.cost_per_input_token
            + output_tokens * self.cost_per_output_token
        )

    def check(self) -> Tuple[bool, str]:
        """
        Returns (over_budget, reason).
        All four limits are checked — the first one hit is reported.
        An unenforced budget is a comment; this method enforces all four.
        """
        elapsed = time.monotonic() - self._start_time

        if self._iterations >= self.max_iterations:
            return True, (
                f"max_iterations={self.max_iterations} reached "
                f"({self._iterations} completed)"
            )
        if self._tokens_used >= self.max_tokens:
            return True, (
                f"max_tokens={self.max_tokens} reached "
                f"({self._tokens_used} used)"
            )
        if self._cost_usd >= self.max_cost_usd:
            return True, (
                f"max_cost_usd=${self.max_cost_usd:.4f} reached "
                f"(${self._cost_usd:.6f} spent)"
            )
        if elapsed >= self.wall_clock_sec:
            return True, (
                f"wall_clock={self.wall_clock_sec}s exceeded "
                f"({elapsed:.1f}s elapsed)"
            )
        return False, ""

    def summary(self) -> dict:
        return {
            "iterations": self._iterations,
            "tokens_used": self._tokens_used,
            "cost_usd": round(self._cost_usd, 8),
            "elapsed_sec": round(time.monotonic() - self._start_time, 2),
            "limits": {
                "max_iterations": self.max_iterations,
                "max_tokens": self.max_tokens,
                "max_cost_usd": self.max_cost_usd,
                "wall_clock_sec": self.wall_clock_sec,
            },
        }
