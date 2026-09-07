from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    question: str
    customer_id: str = "C001"
    item_status: Optional[str] = None          # unopened | opened | damaged | missing
    session_id: str = ""                        # empty = no persistent memory
    namespace: str = "all"
    temperature: float = 0.2
    return_sources: bool = True
    enabled_tools: Optional[List[str]] = None  # None = all tools
    budget_config: Optional[Dict[str, Any]] = None  # override BudgetTracker defaults


class WorkflowRequest(BaseModel):
    question: str
    customer_id: str = "C001"
    item_status: Optional[str] = None
    namespace: str = "all"
    temperature: float = 0.2


class ToolCallRecord(BaseModel):
    tool: str
    args: Dict[str, Any]
    result: Any
    duration_ms: float


class AgentResponse(BaseModel):
    question: str
    answer: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    latency_ms: float
    session_id: str
    budget: Dict[str, Any] = Field(default_factory=dict)
    budget_hit: bool = False
    budget_hit_reason: str = ""


class WorkflowResult(BaseModel):
    question: str
    answer: str
    steps_completed: List[str] = Field(default_factory=list)
    latency_ms: float
    total_tokens: int = 0
    cost_usd: float = 0.0


class RaceTicketResult(BaseModel):
    ticket_id: str
    mode: str                   # "agent" | "workflow"
    passed: bool
    latency_ms: float
    total_tokens: int
    cost_usd: float
    answer: str = ""
    error: str = ""
    budget_hit: bool = False
    budget_hit_reason: str = ""


class RaceReport(BaseModel):
    agent_pass_rate: float
    agent_p50_latency_ms: float
    agent_total_tokens: int
    agent_cost_per_ticket_usd: float
    workflow_pass_rate: float
    workflow_p50_latency_ms: float
    workflow_total_tokens: int
    workflow_cost_per_ticket_usd: float
    ticket_results: List[RaceTicketResult]
    verdict: str
