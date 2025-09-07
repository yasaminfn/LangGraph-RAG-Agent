from mcp.server.fastmcp import FastMCP
from langchain_tool_to_mcp_adapter import add_langchain_tool_to_server

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# Import custom  langchain tools
from tools.tools import TOOLs

# Create an MCP server instance with a custom name
mcp = FastMCP("MyTools")

# Register each LangChain tool with the MCP server
for t in TOOLs:
    print(f"MCP tool registered: {t.name}")
    add_langchain_tool_to_server(mcp, t)
    
if __name__ == "__main__":
    
    # Start the MCP server with streamable HTTP transport and default mount path
    mcp.run(transport="streamable-http", mount_path="/mcp")