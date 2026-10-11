"""
crew_orchestrator.py
====================
Official CrewAI Multi-Agent System re-export.
All logic is consolidated in `agent.multi_agent_orchestrator` using the exact `crewai` library.
"""

from agent.multi_agent_orchestrator import (
    Agent,
    Crew,
    LLM,
    Process,
    Task,
    build_crewai_tools,
    get_crewai_llm,
    stream_crew_agent,
    stream_multi_agent,
)

__all__ = [
    "Agent",
    "Task",
    "Crew",
    "Process",
    "LLM",
    "build_crewai_tools",
    "get_crewai_llm",
    "stream_crew_agent",
    "stream_multi_agent",
]
