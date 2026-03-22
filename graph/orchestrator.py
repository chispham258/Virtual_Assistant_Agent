"""
Multi-agent orchestrator built with LangGraph.

Flow:
  User message → router (decides which agent) → specialized agent → response

Adding a new agent only requires updating agents/registry.py.
The graph discovers all agents from the registry automatically.
"""

from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
from pydantic import BaseModel, field_validator

from agents.factory import MODEL_NAME, create_agent
from agents.registry import REGISTRY
from prompts.router import ROUTER_PROMPT


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _build_router_node(model: ChatAnthropic):
    """Return a router node function closed over the model."""

    valid_agents = list(REGISTRY.keys())
    agent_list = "\n".join(
        f"  - {key}: {defn.description}" for key, defn in REGISTRY.items()
    )
    system_message = SystemMessage(ROUTER_PROMPT.format(agents=agent_list))

    class RouteDecision(BaseModel):
        agent: str
        reasoning: str

        @field_validator("agent")
        @classmethod
        def must_be_valid(cls, v: str) -> str:
            if v not in valid_agents:
                raise ValueError(f"'{v}' is not a valid agent. Choose from: {valid_agents}")
            return v

    router_model = model.with_structured_output(RouteDecision)

    def router_node(state: State) -> Command:
        messages = [system_message] + state["messages"]
        decision = router_model.invoke(messages)
        return Command(goto=decision.agent)

    return router_node


def _make_agent_node(agent):
    """Wrap a compiled ReAct agent as a graph node function."""

    async def agent_node(state: State) -> dict:
        result = await agent.ainvoke({"messages": state["messages"]})
        return {"messages": result["messages"]}

    return agent_node


def build_graph(
    server_tools: dict[str, list[BaseTool]],
    checkpointer: BaseCheckpointSaver,
):
    """
    Build and compile the multi-agent LangGraph graph.

    Args:
        server_tools: Mapping of MCP server key → list of tools for that server.
        checkpointer: LangGraph checkpointer for conversation memory.

    Returns:
        A compiled LangGraph StateGraph.
    """
    model = ChatAnthropic(model=MODEL_NAME)

    graph = StateGraph(State)

    # Router node
    graph.add_node("router", _build_router_node(model))
    graph.add_edge(START, "router")

    # Agent nodes — auto-discovered from registry
    for agent_key, agent_def in REGISTRY.items():
        tools = server_tools.get(agent_def.server_key, [])
        agent = create_agent(agent_def.system_prompt, tools)
        graph.add_node(agent_key, _make_agent_node(agent))
        graph.add_edge(agent_key, END)

    return graph.compile(checkpointer=checkpointer)
