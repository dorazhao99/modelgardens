# main.py
import os
import json
import sys
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
print("MCP_SERVER_PATH", MCP_SERVER_PATH)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="MCP Tool-Calling Agent")

# ---------- Request/response models for FastAPI ----------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------- MCP + OpenAI bridge ----------
REVIEW = """
cohen's kappa of 0.748 and accuracy of >95%... is there anything potentially fishy here
"""

SYSTEM_PROMPT = f"""
Goal: Produce an 'Inspiration Harvest' document that identifies and summarizes transferable writing strategies, frameworks, and approaches found in high-achievers' research statements from the specified field, providing actionable guidance framed as 'techniques you can adapt', not direct achievement comparison.

Step-by-step instructions:

1. Use web search to collect 3–5 successful faculty application research statement examples from high-achievers in the specified field Human-Computer Interaction. Prioritize up-to-date, credible, and well-regarded sources (e.g., university personal pages,  academic portfolios).

2. Download or read the accessible research statements. If direct full-text access is unavailable, gather available excerpts or extended summaries.

3. For each statement, extract and summarize actionable writing strategies, organizational frameworks, rhetorical moves, and presentational techniques. Focus strictly on replicable approaches (e.g., structure, argumentation, narrative technique, use of evidence) rather than content or level of accomplishment.

4. Use the LLM endpoint to analyze all gathered material for common or especially effective writing strategies and distill them into a synthesized list of 'techniques you can adapt'. Ensure a positive, constructive, and non-comparative tone. Do NOT compare or benchmark Michelle’s work or qualifications.

5. Write a clearly structured local plain text document titled 'Inspiration Harvest – Transferable Strategies from Exemplary Research Statements'. Include at least these sections:
- Introduction (purpose and non-comparative framing)
- Techniques You Can Adapt (bulleted or numbered list, each with a brief description or example)
- Optional: References/Links (list of statements reviewed)

6. Save the document to references.txt on the local file system.

Extraction & Formatting Rules:
• Only extract and synthesize strategies, not individual achievements or field-specific technical content
• Maintain a constructive, encouragement-focused tone
• Avoid attributing strategies to specific individuals; focus on generalized forms
• Use clear section headings and concise, actionable descriptions of each strategy

Safety:
• Do not include any content that could be considered personal data, private evaluations, or negatively comparative statements.

Output only the result in the specified local file. Do not output any content to the user except confirmation and the file path.
"""

SYSTEM_PROMPT_V2 = """
GOAL: Support the user (Dora) in building reflective confidence after drafting a review section by analyzing her writing and surfacing back explicit evidence of her analytical strengths, as reflected in her own words, with validating feedback.

STEPS:
1. RECEIVE the user-supplied draft review section as input:
Furthermore, the paper claims that LLMs are changing the topics of fortune-telling (e.g., to include academics and career). However, it is unclear if this is a genuine shift caused by technology or simply a reflection of the young demographic's typical life concerns. For example, there seems to be some evidence that people are talking about these topics even in non-LLM settings (https://restofworld.org/2023/tencent-cece-spirituality-app/). The analysis would be stronger if it could compare the topics found in LLM fortune-telling to those prevalent in traditional fortune-telling within the same demographic. For instance, an angle (if it is reflected in the data) that I think would be interesting is leaning into LLMs as reviving cultural practices for the younger generations. One of the questions I would be curious to know is if this technology is attracting new users who were previously skeptical of LLM fortunetelling / had not considered fortunetelling before even in offline spaces, or is it simply a more accessible medium for existing believers?
I also have some concerns regarding the execution of the methods in the paper. For one, the classifiers performance is surprisingly high. Especially since the authors are dealing with social media data which can be quite messy and are relying on a BERT model, the performance is higher than I expected, which raises questions about the methodology. Given the high accuracy, I would suggest the authors double-check that there was no train-test contamination or data leakage. To bolster the claims, the authors should provide more detail on their data splitting and validation procedures used. As a minor point, the authors could also benchmark the trained classifier's performance against a strong baseline. For example, how well would a zero-shot or few-shot prompted LLM perform on this classification task?
2. PARSE the section to identify phrases or sentences that demonstrate analytical strengths (e.g., critical thinking, insightful observation, clear reasoning, methodological awareness, nuanced synthesis).
3. For each identified strength, EXTRACT a representative quote or paraphrased example from the user's text.
4. For each strength, DRAFT a validating feedback statement in the style of a 'confidence mirror.' Example format: 'Your observation about [topic] demonstrates strong [analytical strength].' Ensure all language is specific, evidence-based, and positive.
5. COMPILE all feedback statements and supporting examples into a concise, readable summary, under appropriate headings:
    - "Identified Analytical Strengths"
    - (sub-bulleted feedback + user text evidence)
6. NOTE INSTRUCTIONS: Do NOT reference external benchmarks, external authorities, or compare to norms—feedback must be entirely grounded in Dora's own words and reasoning.
7. TONE INSTRUCTION: Language should be warm, validating, direct, and focused on explicit skills demonstrated in the draft.
8. FORMAT the feedback summary as Markdown or plain text, as appropriate to file extension.
9. SAVE the output file as reflection.txt in the specified location: reflection.txt. Use the 'WRITE document' tool for local files, or 'WRITE documents' via the appropriate MCP server for saving to Google Drive.
10. RETURN the file path or Drive location and a one-sentence confirmation message.
"""



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
        self._stdio_cm = None
        self._stdio = None
        self._write = None

    async def connect(self) -> None:
        if getattr(self, "session", None) is not None:
            # already connected
            return

        is_python = self.server_script_path.endswith(".py")
        is_js = self.server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("MCP server must be a .py or .js file")

        # Use the same interpreter that runs your backend, so it sees the same deps
        command = sys.executable if is_python else "node"

        server_params = StdioServerParameters(
            command=command,
            args=[self.server_script_path],
            env=None,
        )

        # stdio_client is an async context manager; keep it around so you can close later
        self._stdio_cm = stdio_client(server_params)
        read, write = await self._stdio_cm.__aenter__()
        self._stdio, self._write = read, write

        # ClientSession is also an async context manager
        self._session_cm = ClientSession(self._stdio, self._write)
        self.session = await self._session_cm.__aenter__()

        print("Session created", self.session, file=sys.stderr)

        try:
            # 🔹 Don’t hang forever: fail after 5 seconds if the server doesn’t respond
            await asyncio.wait_for(self.session.initialize(), timeout=5)
            print("Session initialized", self.session, file=sys.stderr)

            tools_response = await asyncio.wait_for(self.session.list_tools(), timeout=5)
            print("Tools response", tools_response, file=sys.stderr)
            tool_names = [t.name for t in tools_response.tools]
            print(f"[MCP] Connected. Tools: {tool_names}", file=sys.stderr)

        except asyncio.TimeoutError:
            print(
                "[MCP] Timed out waiting for server to initialize. "
                "Check MCP_SERVER_PATH, imports, and that the server uses mcp.run(transport='stdio').",
                file=sys.stderr,
            )
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Gracefully close the MCP session and underlying transport."""
        if self.session is not None:
            await self.session.close()
            self.session = None
        if self._stdio_cm is not None:
            await self._stdio_cm.__aexit__(None, None, None)
            self._stdio_cm = None
        self._stdio = None
        self._write = None

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
        print("Building tools")
        tools = await self._build_openai_tools()
        print(tools)
        # First call: ask the model, giving it the tools list
        response = openai_client.responses.create(
            model="gpt-4.1",
            tools=tools,
            # Using chat-like input format with role & content 
            input=[
                {
                    "role": "user",
                    "content": SYSTEM_PROMPT_V2,
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
        print("Function calls", function_calls)
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

    async def run_multi_step_agent(self, user_message: str, max_steps: int = 5) -> str:
        """
        Full multi-step agent:

        - spins up the MCP server over stdio
        - lets the model call ANY MCP tool (add, web_search, write_file, etc.)
        - can call tools multiple times over multiple rounds
        - returns the final natural-language answer

        Drop this into main.py and call it from your /chat endpoint.
        """
        # Choose how to run the MCP server (Python or Node)
        await self.connect()
        assert self.session is not None
        print("Building tools")
        tools = await self._build_openai_tools()
        print(tools)
        print("User message", user_message)

        # Conversation state the model sees
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        for _ in range(max_steps):
            # Ask the model what to do next (may or may not use tools)
            resp = openai_client.responses.create(
                model="gpt-4.1",
                tools=tools,
                input=messages,
            )

            # Look for tool calls in the output
            function_calls = [
                item
                for item in resp.output
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                # No tool calls => final answer
                if resp.output_text:
                    return resp.output_text
                return self._extract_text_from_output(resp.output)

            # We DID get tool calls: run them via MCP and append results
            print("Function calls", function_calls)
            for fc in function_calls:
                func_name = fc.name
                args_dict = json.loads(fc.arguments or "{}")

                # Call the MCP tool
                mcp_result = await self.session.call_tool(func_name, args_dict)

                # Add a short "tool used" message (optional, mostly for context)
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Calling tool {func_name} with {json.dumps(args_dict)}",
                    }
                )

                # Add the tool result as text the model can see
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Result from {func_name}: {json.dumps(mcp_result, default=str)}",
                    }
                )

        # Safety: if we hit max_steps without a final answer
        return "I tried calling tools multiple times but hit the maximum number of steps without finishing."

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
    print("here")
    reply = await mcp_service.run_multi_step_agent(body.message)
    return ChatResponse(reply=reply)


@app.get("/health")
async def health():
    return {"status": "ok"}