# Virtual Assistant Agent

A **multi-agent virtual assistant** that integrates Notion, Gmail, and Google Calendar through a unified interface. The system uses a routing-based architecture to delegate user requests to specialized agents, enabling structured and scalable task execution.

## Overview

This project is built around a **router–agent pattern**, where a central routing model determines which agent should handle a given request. Each agent is responsible for a specific domain and operates with its own tools and context.

The system combines:
- **LangGraph** for orchestration
- **Claude** for routing and reasoning
- **MCP tools** for external service integration
- **FastAPI + Streamlit** for real-time interaction



## Project Structure
```text=
Project
├── main.py                  # FastAPI backend
├── app.py                   # Streamlit frontend
│
├── agents/
│   ├── registry.py          # Agent definitions
│   └── factory.py           # Agent creation logic
│
├── graph/
│   └── orchestrator.py      # LangGraph workflow
│
├── prompts/                 # System prompts per agent
│   ├── router.py
│   ├── notion.py
│   ├── gmail.py
│   └── calendar.py
│
├── utils/
│   └── mcp_loader.py        # MCP configuration loader
│
├── config/
│   └── mcp_config.json      # MCP server definitions
│
└── .env                     # Environment variables
```
## Setup
### Install dependencies

```terminal=
uv sync
```

### Configure environment

Create a `.env` file in the project root:

```env=
ANTHROPIC_API_KEY=sk-ant-...
NOTION_TOKEN=ntn_...
GOOGLE_OAUTH_CREDENTIALS=/path/to/.calendar-mcp/gcp-oauth.keys.json
```

### Google OAuth setup

The Gmail and Google Calendar MCP servers use OAuth. On first run they will open a browser window to complete the OAuth flow. Credentials are cached locally afterward.

### Run

Start the backend (terminal 1):

```terminal=
uv run python main.py
```

Start the UI (terminal 2):

```terminal=
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.


## Adding a New Agent (Module)
To extend the system with a new capability, follow these steps:
### 1. Define MCP server
Add a new entry in `config/mcp_config.json`:
```json=
{
  "my-service": {
    "command": "npx",
    "args": ["my-mcp-package"],
    "env": {
      "MY_TOKEN": "$MY_TOKEN"
    },
    "transport": "stdio"
  }
}
```
### 2. Create system prompt
Add a new prompt file in `prompts/`:

```python=
# prompts/my_service.py
SYSTEM_PROMPT = """
    You are an assistant specialized in ...
"""
```

### 3. Register the agent
Update `agents/registry.py`:

```python=
from prompts import my_service

REGISTRY["my_service"] = AgentDefinition(
    server_key="my-service",
    description="Handles ... (used by router to decide when to call this agent)",
    system_prompt=my_service.SYSTEM_PROMPT,
)
```

### 4. (Optional) Add environment variables
If the MCP server requires credentials, update `.env`:
```=
MY_TOKEN=...
```

### 5. Run the system

Restart the backend to load the new agent:
```terminal=
uv run python main.py
```
