# demo_mcp_server.py

from mcp.server.fastmcp import FastMCP

# Give your server a name (it’ll show up as the MCP server id)
mcp = FastMCP("demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

def main() -> None:
    # Run over stdio so your Python backend can spawn this as a subprocess.
    # IMPORTANT: Don't use print() in this file – stdout is reserved for MCP traffic.
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
