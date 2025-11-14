from pydantic import BaseModel
from typing import List, Dict, Any

AGENT_CONSTRAINTS_V1 = """
The proposed solutions must be actions or plans for a tool-calling agent. By default, the agent can return text outputs into a chat interface. It also has the following capabilities.
- Query an LLM endpoint 
- Access MCP servers for Google Drive (READ / WRITE / EDIT documents)  
- Access MCP servers for Google Calendar (READ / WRITE / EDIT events)  
- Conduct a web search
- Call a computer-using agent to complete a task on the web  
- Create single-page applications in React

### The tool-calling agent **CANNOT**:
- Store data or remember previous interactions (stateless)  
- Maintain user profiles, logs, or history  
- Execute physical-world actions

Actions do NOT need to use all of the capabilities. Always defer to the most minimal implementation that can achieve the desired solution. 
"""

AGENT_CONSTRAINTS = """
The proposed solutions must be actions or plans for a tool-calling agent. The agent has the following capabilities.
- Query an LLM endpoint
- Access MCP servers for Google Drive (READ / WRITE documents)
- Access MCP servers for Google Calendar (READ / WRITE events)
- Conduct a web search
- Draft text (e.g., email, Slack message, text message)
- Call a computer-using agent to complete a task on the browser

### The tool-calling agent **CANNOT**:
- Store data or remember previous interactions (stateless)
- Maintain user profiles, logs, or history
- Execute physical-world actions
- Use external human input beyond the LLM and APIs listed above
- Take multiple actions

Actions do NOT need to use all of the capabilities. Always defer to the most minimal implementation that can achieve the desired solution.
"""

AGENT_PROMPT_V1 = """
You are an expert in design-thinking, specialized in the IDEATE and PROTOTYPE stage. You are given a DESIGN SCENARIO, USER INSIGHT, and HOW MIGHT WE question that reframes the design scenario. Your task is to proposed {limit} diverse solutions that a tool-calling agent can take to address the HOW MIGHT WE question. 

# Guidelines
1. Review the problem reframing and ideate a wide range of potential actions the tool-calling agent can take based on the HOW MIGHT WE question. 
2. For each action, evaluate how beneficial they would be to {user_name} given the USER INSIGHT. Rank the actions by how much they would benefit her.
3. Next, for each action, evaluate its implementability given the IMPLEMENTATION CONSTRAINTS. For each action, decide whether it can implemented under these constraints. If it can be implemented, reflect on how beneficial it would be to {user_name}. Update the ranking of solutions after accounting for implementation. 
4. Select the top {limit} actions that are implementable and beneficial to {user_name}. 

# Input
DESIGN SCENARIO:
{scenario}

USER INSIGHT: 
{user_insight}

HOW MIGHT WE:
{hmw}

IMPLEMENTATION CONSTRAINTS:
{constraints}

## Output
Return just the solutions and a short description (2-3 sentences) of how it works
"""

AGENT_PROMPT_V2 = """
You are an expert in design-thinking, specialized in the IDEATE and PROTOTYPE stage. 
ou are given a DESIGN SCENARIO, USER INSIGHT, and HOW MIGHT WE question that reframes the design scenario. 
Your task is to proposed 3 diverse actions that a tool-calling agent can take to proactively address the HOW MIGHT WE question.

# Guidelines
1. Review the problem reframing and ideate a wide range of potential actions the tool-calling agent can take based on the HOW MIGHT WE question.
2. For each action, evaluate how beneficial they would be to Dora given the USER INSIGHT. Rank the actions by how much they would benefit her.
3. Next, for each action, evaluate its implementability given the IMPLEMENTATION CONSTRAINTS. For each action, decide whether it can implemented under these constraints. If it can be implemented, reflect on how beneficial it would be to Dora. Update the ranking of solutions after accounting for implementation.
4. Select the top {limit} actions that are implementable and beneficial to Dora.

# Input
DESIGN SCENARIO:
{scenario}

HOW MIGHT WE:
{hmw}

IMPLEMENTATION CONSTRAINTS:
{constraints}

## Output
Return just the solutions and a 1-2 sentence description of what they do. 
"""

BASELINE_AGENT_PROMPT = """
You are given a user-centered PROBLEM. 
Your task is to proposed {limit} diverse actions that a tool-calling agent can take to proactively address the user-centerd PROBLEM. 

# Guidelines
1. Review the PROBLEM and ideate a wide range of potential actions the tool-calling agent can take.
2. For each action, evaluate how beneficial they would be to {user_name}. Rank the actions by how much they would benefit her.
3. Next, for each action, evaluate its implementability given the IMPLEMENTATION CONSTRAINTS. For each action, decide whether it can implemented under these constraints. If it can be implemented, reflect on how beneficial it would be to {user_name}. Update the ranking of solutions after accounting for implementation. 
4. Select the top {limit} actions that are implementable and beneficial to {user_name}. 

# Input
DESIGN PROBLEM:
{scenario}

IMPLEMENTATION CONSTRAINTS:
{constraints}

## Output
Return the top {limit} actions and a short description (2-3 sentences) of how it works
"""

class UserInput(BaseModel):
    placeholder_name: str
    description: str
    modality: str

class AgentSpec(BaseModel):
    user_inputs: List[UserInput]
    execution_prompt: str
    expected_output_format: str

AGENT_SPEC = """
Your task is to transform the following prose description into a full descriptive design specification for a tool-using agent that has access to the following capabilities:
- Query an LLM endpoint
- Access to local file systems (READ / WRITE documents)
- Access MCP servers for Google Drive (READ / WRITE documents)
- Access MCP servers for Google Calendar (READ / WRITE events)
- Conduct a web search
- Draft text (e.g., message, email, Slack message, text message)
- Call a computer-using agent to complete a task on the browser

Your output must include (1) user inputs needed, (2) the execution prompt that will be fed to the agent (with explicit tool-use instructions), and (3) the expected output format.

# Criteria
When generating the execution prompt, it must be specific and make reference to the specific tools and actions that the agent can take.

## Examples of Execution Prompts:
- Draft a one-page IRB data-sensitivity checklist and 'Do NOT create DB until' gate saved to checklist.md that enumerates exact verification steps (IAM least-privilege checks, encryption/transit confirmation, backup/restore test steps, SMTP verification, key rotation requirements) and the precise console/gcloud commands or screenshot instructions needed to prove each item.
- Generate a one-page executive summary and a 3–5 minute speaker script (saved as "summary.txt") covering objectives, methodology, participant protections/consent plan, technical security appendix, current metrics/status, open questions, and next steps.

# Input 
Give the following DESIGN SCENARIO and PROBLEM, we provide a prose description of the solution to convert. 
DESIGN SCENARIO:
{scenario}

PROBLEM:
{problem}

PROSE DESCCRIPTION:
{solution}

# Requirements
Requirements for your output:
1. User Input Needed
List all missing parameters, contextual details, preferences, constraints, or file-storage details that the agent should request from the user before running the workflow. 
Only ask for user input that is **absolutely necessary**. 

For each input, specify **how** the input will be solicited from the user. The ONLY option is TEXTBOX.

2. Agent Execution Prompt
Produce a ready-to-run system prompt containing. Use placeholders in the prompt to insert user input. 
- The overall goal
- A clear, numbered sequence of steps the agent must execute
- Explicit tool-use directions (e.g., web search, API calls, repo manipulations, Drive file creation, etc.)
- Extraction/analysis rules
- Safety/tone/formatting constraints
- Instructions for where and how to save artifacts (e.g., paths, filenames)
- Structural requirements for generated content

This prompt should be directly usable as a system prompt for a tool-enabled agent.

3. Expected Output Format
Define the exact shape of the agent’s output.
Examples:
- Message to user
- JSON spec
- Browser extension code 
- Saved Google Drive file paths
- Markdown with specific headings
- Filenames and folder paths
- Multi-file instructions

Be precise and unambiguous.

**IMPORTANT**
Your role is not to perform the task in the prose description.
Your role is to produce the specification that another agent will follow to perform it.

# Output
Return just the specification in the following format:
{{
    "user_inputs": [{{
        "placeholder_name": "Name of placeholder in the prompt where the input will be added", 
        "description": "Description of input", 
        "modality": [TEXTBOX]
    }}],
    "execution_prompt": "The execution prompt that will be fed to the agent",
    "expected_output_format": "The expected output format"
}}
"""