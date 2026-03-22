"""
Agent registry — the single source of truth for all agents in the system.

To add a new agent:
  1. Add its MCP server entry to config/mcp_config.json.
  2. Create prompts/<agent_name>.py with a SYSTEM_PROMPT string.
  3. Add an AgentDefinition entry to REGISTRY below.
  That's it — the graph and router pick it up automatically.
"""

from dataclasses import dataclass

from prompts import calendar, gmail, notion


@dataclass(frozen=True)
class AgentDefinition:
    server_key: str   # Must match a key in mcp_config.json
    description: str  # One-line description used by the router to decide routing
    system_prompt: str


REGISTRY: dict[str, AgentDefinition] = {
    "notion": AgentDefinition(
        server_key="Notion",
        description="Handles Notion pages, databases, and notes — searching, reading, and writing content",
        system_prompt=notion.SYSTEM_PROMPT,
    ),
    "gmail": AgentDefinition(
        server_key="gmail",
        description="Handles Gmail — reading, drafting, sending, replying to, and searching emails",
        system_prompt=gmail.SYSTEM_PROMPT,
    ),
    "calendar": AgentDefinition(
        server_key="google-calendar",
        description="Handles Google Calendar — listing events, creating or editing meetings, and checking availability",
        system_prompt=calendar.SYSTEM_PROMPT,
    ),
}
