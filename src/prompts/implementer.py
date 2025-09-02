SIMILAR_PROMPT = """
You will be given a proposed tool idea. Your task is to evaluate (1) the utility of the tool and (2) whether tool already exists. 

# Existing Tools
{existing_tools}

# Proposed Tool
{new_tool}

# Actions
{user_actions}

## Exists Labels
Use exactly these labels:
1 - The existing tools contains a tool similar to the proposed tool
0 - The existing tools do NOT contain a tool similar to the proposed tool or there are no existing tools

## Utility Scale
Generate a support score from 1-10 that captures how much evidence you have to support the user will find the tool useful.
Be **conservative** in your support estimates.

Just because an application appears on the screen does not mean they have deeply engaged with it. They may have only glanced at it for a second, making it difficult to draw strong conclusions.
Assign high support scores (e.g., 8-10) only when there is strong evidence that the user would actively engage with this tool and need it in their workflow.

Score: 1 (not that useful of a tool) to 10 (best tool the user has ever used).

# Output
Return **only** JSON in the following format:
{{
    exists: [Exists label (0 / 1)],
    utility: [Utility score (1-10)]
}}
"""

IMPLEMENT_PROMPT = """
You are an excellent software engineer that will generate a standalone React
component given a description of the tool's purpose and brief information on the
required inputs / outputs.

The tool should be able to compile and render on the user's screen without
downloading any additional packages. Always prioritize the simplest solution over
complexity. You can import components from flowbite-react. 

## Task
Your task is to implement the tool, {name}. 
Tool Description: {description}.

## Design 
The tool will be displayed on the sidebar of the user's window.
Decide what a good frontend design would look like for this tool given the spatial
constraints. 

Use best practices in React when creating the tool.

## Implementation Specifications
- If the application must query a commercial LLM, it should use the environment key
GEMINI_KEY. 
- Do not set the temperature parameter. 
- If the tool requires user input, it should require minimal processing from the user. Instead, use an LLM to convert the user input into the needed format.
- By default, if the task requires an LLM use gemini-2.5-flash. If the task requires reasoning, use gemini-2.5-pro. If the task requires external knowledge or search, enable search in the API. 

Return just the code for the tool and nothing else. 
"""

CRITIQUE_PROMPT="""
You are a senior software engineer. Your task is to review a React component.

# Task
Review the application code to ensure it is fulfilling its purpose. Then, thoroughly inspect and critique the code and to ensure each component functions correctly. 
Consider:
- Does the application process user input correct;y?
- Will outputs be rendered correctly?

## Implementation Details
Do not set the temperature parameter. 
If the tool requires user input, it should require minimal processing from the user. Instead, use an LLM to convert the user input into the needed format.
If the task requires reasoning, use o3-mini.
If the task requires external knowledge, such as looking up papers or restaurants, use an LLM with search enabled in the API. Otherwise, default to gpt-4o-mini. 

The purpose of the app is: {description}.

Application Code:
{react_code}

Return just the code and any critiques in the following format:
{{
    code: [Insert HTML code for the application here]
    critique: [Insert any critiques here]
}} 
"""
