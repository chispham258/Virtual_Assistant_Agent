from dotenv import load_dotenv

load_dotenv()

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from agents.registry import REGISTRY
from graph.orchestrator import build_graph
from utils.mcp_loader import load_mcp_config

checkpointer = InMemorySaver()
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph

    mcp_config = load_mcp_config()
    client = MultiServerMCPClient(mcp_config)

    # Load tools per server so each agent only gets its own tools
    server_tools: dict = {}
    for agent_def in REGISTRY.values():
        server_key = agent_def.server_key
        if server_key not in server_tools:
            server_tools[server_key] = await client.get_tools(server_name=server_key)

    graph = build_graph(server_tools, checkpointer)
    print(f"Graph built with agents: {list(REGISTRY.keys())}")

    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def stream_response(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    async for chunk, metadata in graph.astream(
        {"messages": [HumanMessage(query)]},
        stream_mode="messages",
        config=config,
    ):
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            data = {
                "type": chunk.__class__.__name__,
                "content": chunk.content,
            }
            if chunk.tool_calls:
                data["tool_calls"] = chunk.tool_calls

            yield (json.dumps(data) + "\n").encode()


@app.get("/")
async def root():
    return {"message": "Hello World"}


class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query")
    thread_id: str = Field(..., description="The thread ID for conversation memory")


@app.post("/chat_stream")
async def chat_stream(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Empty prompt!")

    try:
        return StreamingResponse(
            stream_response(request.query, request.thread_id),
            media_type="application/x-ndjson",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8080)
