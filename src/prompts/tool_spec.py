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
        },
        "reasoning": {
            "type": "str",
            "description": "Reasoning as to how this solution meets the user's needs",
        }
    },
    "required": ["patterns", "reasoning"],
}


GOAL_INDUCTION_PROMPT = """
I have the following CONTEXT that a current user is working on:

CONTEXT:
{context}

Now, employ the following reasoning framework when inferring the goals.

0. If there is an attached screenshot, use context clues to infer what application the user is viewing and what they might be doing in that application. Are they the direct author of the text, or are they viewing it as a reader? Are they actively editing the text, providing feedback, or synthesizing the content?

1. Identify the genre of what the user is working on and their stage of completion. Map the content's genre and completion stage to common goals users of these genres and stages may have, and form an initial hypothesis of what the user's goals may be.

2. Infer who the intended audience of the content is. Based on how you think the user wants their audience to receive their content, update your goal hypothesis.

3. Think about what an ideal version of the user's current content would look like and identify what is missing. Then, use this to update your goal hypothesis.

4. Simulate what the user's reaction would be to possible tools generated (e.g., grammar checker, style reviser, high-level structure advisor, new content generator, etc.). Use the user's responses to update your goal hypothesis.

For each step in your reasoning, briefly write out your thought process, your current hypothesis of the goals as a numbered list, and what the updated list would be after your reasoning.

After you are done, finalize the {limit} most important goals. Make sure these goals are distinct and have minimal overlap.

Please respond ONLY with a JSON that matches the following json schema, including your reasoning and the new goals along with their relative weight (1–10). The weight is the estimated *importance* of the goal to the user, based on the provided context (1 = not important, 5 = moderately important, 10 = very important).

{{
    "goals": [
        {{
            "goal": [Insert the name of the goal],
            "description": [Insert a 1-2 sentence description of the goal],
            "weight": [Insert the weight of the goal (1-10)],
            "reasoning": [Insert a 1-2 sentence reasoning for the goal],
        }}
    ]
}}
""" 

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

Generate **{limit} distinct, well-supported tools** that can support {user} in their task. 

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


PATTERN_INDUCTION_PROMPT = """
I have the following CONTEXT and GOALS for creating a helpful tool :

CONTEXT:
{context}

GOALS:
{goals}

What {limit} design patterns would be most helpful for accomplishing {user}'s GOALS?

Ideal tools are intuitive, easy to use, and generally have a single-step interaction with the user.

Please respond ONLY with a JSON that matches the following json_schema:
{json_schema}
"""

PATTERN_INDUCTION_PROMPT_NEEDS = """
I have the following CONTEXT, GOALS, and NEEDS for creating a helpful tool :

CONTEXT:
{context}

GOALS:
{goals}

Based on the user need-finding you have conducted, you find that {user} has the following long-term needs:
{needs}

What {limit} design patterns would be most helpful for accomplishing the user's GOALS while adhering to the user's long-term needs?

Ideal tools are intuitive, easy to use, and generally have a single-step interaction with the user.

Please respond ONLY with a JSON that matches the following json_schema:
{json_schema}
"""

PATTERN_JUDGE = """
You are given a design pattern and a user's need. Decide whether the design pattern is a good fit for the user's need.

Be careful to not over-generalize the design pattern to the user's needs.

Design Pattern:
{design_pattern}

User Need:
{user_need}

Label the pattern either as -1, 0, or 1. 
-1: The design pattern CONTRADICTS ONE or MORE of the needs.
0: The design pattern is UNRELATED to the user's needs.
1: The design pattern MEETS user's needs.

Return the following JSON:
{{
    "response": [-1, 0, 1],
    "reasoning": 1-2 sentence rationale explaining the judgement,
}}
"""