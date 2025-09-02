from graph import Agent
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools

# Initialize the language model (OpenAI GPT-4o-mini)
model = ChatOpenAI(model="gpt-4o-mini")

async def create_agent_from_session(session):
    """
    Create an agent from an existing MCP session.

    This function:
    - Loads all available tools from the given MCP session
    - Initializes an Agent with the specified language model and tools
    - Performs a quick test call to verify MCP tools are working
    - Returns the configured Agent instance

    Args:
        session: An active MCP session object

    Returns:
        Agent: Configured Agent instance with MCP tools
    """
    
    # Load available tools from the MCP session
    tools = await load_mcp_tools(session)
    print("✅ Tools loaded:", [tool.name for tool in tools])
    
    # Create an Agent instance with model and tools
    agent = Agent(
        model=model,
        tools=tools,
        system="You are a helpful assistant",
    )
    
    # Attach MCP session to the agent for clean shutdown later (for FastAPI app)
    agent._mcp_session = session
    
    # Quick test: Call the 'safe_tavily' tool with a sample query
    tav = next(t for t in tools if t.name == "safe_tavily")
    print(await tav.ainvoke(input={"query": "LA weather"}))

    # Quick test: Call the 'get_price' tool for Bitcoin price
    price_tool = next(t for t in tools if t.name == "get_price")
    print(await price_tool.ainvoke(input={"slug": "bitcoin"}))
    
    return agent