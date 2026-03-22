from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

MODEL_NAME = "claude-3-5-haiku-20241022"


def create_agent(system_prompt: str, tools: list[BaseTool]):
    """Create a ReAct agent with the given system prompt and tools."""
    model = ChatAnthropic(model=MODEL_NAME)
    return create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )
