# main.py
import os
import json
import asyncio
from typing import Optional, List, Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from openai import OpenAI

# MCP imports (client + stdio transport) 
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MCP_SERVER_PATH = os.environ["MCP_SERVER_PATH"]  # path to your MCP server script

openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="MCP Tool-Calling Agent")

# ---------- Request/response models for FastAPI ----------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------- MCP + OpenAI bridge ----------

class MCPChatService:
    """
    Holds a connection to an MCP server and provides
    a `chat_once` method that:
      1) lists tools from MCP
      2) calls OpenAI with those tools via function calling
      3) executes any tool calls against the MCP server
    """
    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self._stdio = None
        self._write = None

    async def connect(self) -> None:
        """Connect to the MCP server over stdio and initialize the session."""
        if self.session is not None:
            return  # already connected

        is_python = self.server_script_path.endswith(".py")
        is_js = self.server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("MCP server must be a .py or .js file")

        command = "python" if is_python else "node"

        server_params = StdioServerParameters(
            command=command,
            args=[self.server_script_path],
            env=None,
        )

        # stdio_client handles spawning the MCP server process and wiring stdin/stdout 
        stdio_transport = await stdio_client(server_params)
        self._stdio, self._write = stdio_transport
        self.session = ClientSession(self._stdio, self._write)

        await self.session.initialize()

        tools_response = await self.session.list_tools()
        tool_names = [t.name for t in tools_response.tools]
        print(f"[MCP] Connected. Tools: {tool_names}")

    async def _build_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Convert MCP tool definitions into OpenAI function-tools.
        We map MCP's inputSchema directly to the OpenAI `parameters` field. 
        """
        assert self.session is not None, "MCP session not initialized"

        tools_response = await self.session.list_tools()
        openai_tools = []
        for t in tools_response.tools:
            # Depending on SDK version, this may be `t.input_schema` or `t.inputSchema`.
            input_schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)

            openai_tools.append(
                {
                    "type": "function",
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": input_schema or {
                        "type": "object",
                        "properties": {},
                    },
                }
            )

        return openai_tools

    async def chat_once(self, user_message: str) -> str:
        """
        Single-turn interaction:
        - user_message → OpenAI (with MCP tools)
        - run any function_call outputs via MCP
        - send function_call_output back to OpenAI
        - return final assistant text
        """
        await self.connect()
        assert self.session is not None

        tools = await self._build_openai_tools()

        # First call: ask the model, giving it the tools list
        response = openai_client.responses.create(
            model="gpt-4.1",
            tools=tools,
            # Using chat-like input format with role & content 
            input=[
                {
                    "role": "user",
                    "content": user_message,
                    "type": "message",
                }
            ],
        )

        # Collect tool calls, if any
        function_calls = []
        for item in response.output:
            if item.type == "function_call":
                function_calls.append(item)

        if not function_calls:
            # No tools, just return the assistant text
            return response.output_text or self._extract_text_from_output(response.output)

        # If there ARE tool calls, execute them via MCP and send outputs back
        tool_outputs_for_model = []

        for fc in function_calls:
            func_name = fc.name
            call_id = fc.call_id
            # Arguments are a JSON string in Responses function calling example 
            args_dict = json.loads(fc.arguments or "{}")

            # Call MCP tool
            mcp_result = await self.session.call_tool(func_name, args_dict)

            # mcp_result.shape can vary by tool; we just JSON-encode it
            tool_outputs_for_model.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(mcp_result, default=str),
                }
            )

        # Second call: give tool outputs back to the model and ask for final answer
        second_response = openai_client.responses.create(
            model="gpt-4.1",
            previous_response_id=response.id,
            input=tool_outputs_for_model,
        )

        return (
            second_response.output_text
            or self._extract_text_from_output(second_response.output)
            or ""
        )

    @staticmethod
    def _extract_text_from_output(output_items: List[Any]) -> str:
        """Fallback: pull text out of message-style output."""
        chunks: List[str] = []
        for item in output_items:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) in ("output_text", "input_text"):
                        chunks.append(getattr(c, "text", "") or "")
        return "\n".join(chunks)


mcp_service = MCPChatService(MCP_SERVER_PATH)


# ---------- FastAPI routes ----------

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest) -> ChatResponse:
    """
    Electron will call this with:
      POST /chat
      { "message": "..." }
    and get back:
      { "reply": "..." }
    """
    reply = await mcp_service.chat_once(body.message)
    return ChatResponse(reply=reply)


@app.get("/health")
async def health():
    return {"status": "ok"}