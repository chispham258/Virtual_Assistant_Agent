from dotenv import load_dotenv
from langchain_anthropic import Anthropic
from langchain.agents import create_agent, AgentExecutor, AgentType

load_dotenv()

llm = Anthropic(model = "claude-3-haiku-20240307")
response = llm.invoke("What is UIT?")

agent = create_agent(
    llm, 
    tools = [], 
    agent_type = "zero-shot-react-description"
)

agent_executor = AgentExecutor(agent=agent, tools=[])
agent_response = agent_executor.invoke("What is UIT?")

print("LLM Response:", response)

