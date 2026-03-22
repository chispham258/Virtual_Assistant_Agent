# Virtual Assistant Agent

A multi-agent personal virtual assistant that integrates Notion, Gmail, and Google Calendar through a streaming FastAPI backend and a Streamlit UI. Built with LangGraph, LangChain MCP Adapters, and Claude.

---

## Architecture

```text
User (Streamlit UI)
    │  HTTP POST /chat_stream  (NDJSON streaming)
    ▼
FastAPI backend  (main.py)
    │
    ▼
LangGraph StateGraph
    │
    ├─► Router node  (Claude + structured output)
    │       │
    │       ├─► notion agent   (ReAct + Notion MCP tools)
    │       ├─► gmail agent    (ReAct + Gmail MCP tools)
    │       └─► calendar agent (ReAct + Google Calendar MCP tools)
    │
    └─► END  (streamed AIMessageChunk tokens back to client)
```

### Request lifecycle

1. The Streamlit frontend sends the user message to `POST /chat_stream` with a stable `thread_id`.
2. FastAPI passes the message into the LangGraph graph via `graph.astream(..., stream_mode="messages")`.
3. The **router node** invokes Claude with a structured-output schema (`RouteDecision`) to pick exactly one agent (`notion | gmail | calendar`). It uses `Command(goto=<agent>)` to jump directly to that node.
4. The selected **agent node** runs a `create_react_agent` loop with its scoped MCP tools until it produces a final answer.
5. `AIMessageChunk` tokens are serialised as NDJSON lines and streamed back; the UI renders them token-by-token with `st.write_stream()`.
6. `InMemorySaver` checkpointer persists the full conversation per `thread_id` across turns.

---

## Project structure

```text
.
├── main.py                  # FastAPI app — lifespan, /chat_stream endpoint
├── app.py                   # Streamlit UI
│
├── agents/
│   ├── registry.py          # AgentDefinition dataclass + REGISTRY dict
│   └── factory.py           # create_agent() — wraps create_react_agent
│
├── graph/
│   └── orchestrator.py      # build_graph() — StateGraph wiring
│
├── prompts/
│   ├── router.py            # ROUTER_PROMPT — assistant persona + routing rules
│   ├── notion.py            # SYSTEM_PROMPT for Notion agent
│   ├── gmail.py             # SYSTEM_PROMPT for Gmail agent
│   └── calendar.py         # SYSTEM_PROMPT for Google Calendar agent
│
├── utils/
│   └── mcp_loader.py        # load_mcp_config() + $VAR expansion
│
├── config/
│   └── mcp_config.json      # MCP server definitions (env vars via $VAR)
│
└── .env                     # API keys and secrets (never committed)
```

---

## Key design decisions

### Agent registry pattern

`agents/registry.py` is the single source of truth. Each agent is described by:

| Field | Purpose |
| --- | --- |
| `server_key` | Must match a key in `mcp_config.json` |
| `description` | Fed to the router so it knows when to pick this agent |
| `system_prompt` | Injected into the agent's ReAct loop |

Adding a new agent requires only three steps: add an entry to `REGISTRY`, add a prompt file under `prompts/`, and add the MCP server config to `mcp_config.json`.

### Router

The router is a Claude call with `with_structured_output(RouteDecision)` where `RouteDecision` is a Pydantic model with a `@field_validator` that rejects any agent key not in `REGISTRY`. This avoids dynamic `Literal` types and keeps validation close to the model.

The router prompt gives Claude an assistant persona so routing decisions are contextual ("email me the Notion summary" → gmail, because the *action* is sending an email).

### MCP tool isolation

Each agent only receives tools from its own MCP server. `MultiServerMCPClient.get_tools(server_name=...)` is called per unique `server_key` at startup and the results are stored in `server_tools: dict[str, list[BaseTool]]`. This prevents cross-contamination of tools between agents.

### Streaming

`graph.astream(..., stream_mode="messages")` yields `(chunk, metadata)` pairs. Only `AIMessageChunk` with non-empty `.content` is forwarded. The FastAPI response is `StreamingResponse` with `media_type="application/x-ndjson"`. The Streamlit client reads lines with `requests` in `stream=True` mode and feeds them to `st.write_stream()`.

---

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Node.js (for `npx` to run MCP servers)
- Anthropic API key
- Notion integration token
- Google OAuth credentials for Gmail and Calendar

### Install dependencies

```bash
uv sync
```

### Configure environment

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
NOTION_TOKEN=ntn_...
GOOGLE_OAUTH_CREDENTIALS=/path/to/.calendar-mcp/gcp-oauth.keys.json
```

### Google OAuth setup

The Gmail and Google Calendar MCP servers use OAuth. On first run they will open a browser window to complete the OAuth flow. Credentials are cached locally afterward.

### Run

Start the backend (terminal 1):

```bash
uv run python main.py
```

Start the UI (terminal 2):

```bash
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Dependencies

| Package | Role |
| --- | --- |
| `fastapi` | HTTP backend |
| `langchain-mcp-adapters` | Bridges MCP servers to LangChain tools |
| `langgraph` | Multi-agent graph execution and memory |
| `langchain-anthropic` | Claude model integration |
| `langchain-core` | Base message and tool abstractions |
| `streamlit` | Chat UI |
| `python-dotenv` | `.env` loading |
| `pydantic` | Structured router output validation |
| `requests` | Streaming HTTP client in Streamlit |

---

## Adding a new agent

1. **MCP server** — add an entry to `config/mcp_config.json`:

   ```json
   "my-service": {
       "command": "npx",
       "args": ["my-mcp-package"],
       "env": { "MY_TOKEN": "$MY_TOKEN" },
       "transport": "stdio"
   }
   ```

2. **Prompt** — create `prompts/my_service.py` with a `SYSTEM_PROMPT` string.

3. **Registry** — add to `agents/registry.py`:

   ```python
   from prompts import my_service

   REGISTRY["my_service"] = AgentDefinition(
       server_key="my-service",
       description="Handles ... — describe when the router should pick this agent",
       system_prompt=my_service.SYSTEM_PROMPT,
   )
   ```

No changes to `main.py`, `graph/orchestrator.py`, or `app.py` are needed.
