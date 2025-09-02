PATTERN_INDUCTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the design pattern",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the design pattern",
                    },
                    "reasoning": {
                        "type": "object",
                        "properties": {
                            "1_domain_knowledge": {
                                "type": "string",
                                "description": "Domain knowledge unique to the genre and content of what the user is working on",
                            },
                            "2_workflows": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Workflows that would be most helpful to fulfill the user's goals",
                                },
                            },
                        },
                    },
                    "input_type": {
                        "type": "string",
                        "description": "Expected input to this design pattern",
                    },
                    "output_type": {
                        "type": "string",
                        "description": "Expected output from this design pattern",
                    },
                    "user_behavior": {
                        "type": "string",
                        "description": "How the user is expected to interact with the UI sequentially at each point of interaction",
                    },
                    "ui_features": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Descriptions of core interface features; how the UI is expected to look and behave",
                        },
                    },
                    "design_guidelines": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Guidelines for selecting this design pattern; situations when it is most suitable",
                        },
                    },
                },
                "required": [
                    "name",
                    "description",
                    "input_type",
                    "output_type",
                ],
            },
        }
    },
    "required": ["patterns"],
}

TOOL_PROMPT = """
You are a helpful assistant tasked with generating tools to support a user's tasks.

# Generate Tools

Using a description of the user's current task, generate examples of tools that would help Dora complete the task. Provide concrete and concise descriptions of tools. 

Consider these points when coming up with tools:
- What specific tasks is Dora working on?
- What are parts of their workflows that could be aided by tools?

# Input

Below is a description of the user's goal:
{scenario}

# Task

Generate **5 distinct, well-supported tools** that can support Dora in her task. 

Return your results in this exact JSON format:

{{
"tools": [
  {{
    "name": [Insert the name of the tool],
    "tool": "[Insert a 3-4 sentence description of the tool here with details on how the tool would work. Be as specific as possible.]",
    "reasoning": "[Provide 1-2 sentence rationale as to why the tool would be useful.]",
  }},
]
}}
"""




TOOL_NEEDS_PROMPT = """
You are a helpful assistant tasked with generating tools to support a user's tasks.

# Generate Tools

Using a description of the user's current needs, generate examples of tools that would help Dora complete the task. Provide concrete and concise descriptions of tools. 

Consider these points when coming up with tools:
- What specific tasks is Dora working on?
- What are parts of their workflows that could be aided by tools?

# Input

User's needs:
{needs}

# Task

Generate **5 distinct, well-supported tools** that can support Dora in her task. 

Return your results in this exact JSON format:

{{
"tools": [
  {{
    "name": [Insert the name of the tool],
    "tool": "[Insert a 3-4 sentence description of the tool here with details on how the tool would work. Be as specific as possible.]",
    "reasoning": "[Provide 1-2 sentence rationale as to why the tool would be useful.]",
  }},
]
}}
"""

TOOL_UPDATE_PROMPT = """
## **Role**
I have learned about the following USER NEEDS that need to be fulfilled:  
{needs}

Your task is to **update and refine the tool** so that it better fits the users' needs.

## **Instructions**

### **1. Understand the Inputs**
- Carefully analyze the **original tool description**:
    - What is its current purpose and workflow?
    - What are its core features and assumptions?
    - What constraints or technical dependencies exist?
- Study the **user needs**:
    - Which needs are explicit vs. implicit?
    - Which needs are critical vs. optional?
    - Where do the needs conflict with the existing tool design?

### **2. Perform a Gap Analysis**
- Identify mismatches between the **current tool** and the **user needs**:
    - Missing features  
    - Misaligned workflows  
    - Underserved edge cases  
    - Misfit assumptions (e.g., requiring too much technical expertise)
- Prioritize fixes based on:
    - **High-value needs** → Features that unlock core workflows.
    - **Feasibility** → Changes that can realistically be implemented.
    - **Scalability** → Designs that support future expansion.


## Input
Tool Description: 
{tool}

User Needs:
{needs}

## Output**
Please respond ONLY with a JSON that matches the following json_schema:
{json_schema}
"""


PATTERN_INDUCTION_PROMPT = """I have the following CONTEXT for creating a helpful tool:

CONTEXT:
{context}

PREP WORK:
1. Based on the user CONTEXT, what are some norms and domain knowledge unique to the genre and content they are working on? 
2. A workflow is defined as a solution to a user need that can be instantiated in many different ways; it behaves like a function, taking in some input, performs some work, and returns some output. Drawing on specialized domain knowledge from the genre and content of what the user is working on, what would be some workflows that would be most helpful to fulfill the user's GOALS? 

Taking into account the PREP WORK, what {limit} design patterns would be most helpful for accomplishing the user's GOALS?

Ideal tools are intuitive, easy to use, and generally have a single-step interaction with the user.

Please respond ONLY with a JSON that matches the following json_schema:
{json_schema}

DO NOT INCLUDE ANY OTHER TEXT IN YOUR RESPONSE."""

PATTERN_INDUCTION_PROMPT_NEEDS = """I have the following CONTEXT and USER NEEDS for creating a helpful tool:

CONTEXT:
{context}

USER NEEDS:
{needs}

PREP WORK:
1. Based on the user CONTEXT, what are some norms and domain knowledge unique to the genre and content they are working on? 
2. Based on the USER NEEDS, what are some specific user needs that are most important to fulfill?
3. A workflow is defined as a solution to a user need that can be instantiated in many different ways; it behaves like a function, taking in some input, performs some work, and returns some output. Drawing on specialized domain knowledge from the genre and content of what the user is working on, what would be some workflows that would be most helpful to fulfill the user's GOALS? 

Taking into account the PREP WORK, what {limit} design patterns would be most helpful for accomplishing the user's GOALS?

Ideal tools are intuitive, easy to use, and generally have a 
single-step interaction with the user.

Please respond ONLY with a JSON that matches the following json_schema:
{json_schema}

DO NOT INCLUDE ANY OTHER TEXT IN YOUR RESPONSE."""