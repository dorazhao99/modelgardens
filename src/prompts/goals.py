INITIAL_GOALS_PROMPT = """Provide goals based on the users' current actions.

Here are their current actions:
{actions}

Now, reflect on the actions and decide holistically what the user's HIGH-LEVEL, overarching goal is. 
First, write a description of the HIGH-LEVEL goal.
Then, write up to 5 unique low-level tasks that the user is immediately working on towards these goals. For each goal, rate the importance of this task to the user from a scale of 1-10. 
Assign high support scores (e.g., 8-10) **only** when the actions provide explicit, direct evidence that the user is actively completing this task.
Finally, include up to 5 bullet points providing specific context about the goal (e.g., what are details about the task, who is involved, when is the task due). 

Please respond **only** with a JSON of the following format:
{{
    "status": "NEW",
    "goal": [Insert name of the high-level goal the task is for],
    "description": [Insert 1-2 sentence description of the goal.  Provide specific references to the user's current actions],
    "tasks": [
        {{
            "task": [Insert name of the task],
            "description": [Insert 1-2 sentence description of the task], 
            "importance": [Insert rating 1-10 about how important the task is]
        }}
    ],
    "context": [<DETAIL>, <DETAIL>, <DETAIL>]
}}
"""

CONTINUING_GOALS_PROMPT = """Identify whether the user's goals have changed based on their actions. 

# Goals and Actions
Past goal:
{past_goal}

Past tasks:
{past_tasks}

Past context:
{past_context}

Here are their current actions:
{actions}

# Task
1. Reflect on the actions and decide holistically whether the user's HIGH-LEVEL, overarching goal has changed or stayed the same. Use these exact labels:
(A) SIMILAR – The high-level goals are similar
(B) NEW  – The user now has a completely different goal they are working towards

2. Include past tasks that are **still relevant** and any new unique low-level tasks that the user is immediately working on towards these goals. For each goal, rate the importance of this task to the user for completing the goal from a scale of 1-10. 
3. Include past context that is still relevant and any **new** context learned about the goal (e.g., what are details about the task, who is involved, when is the task due). 

Please respond **only** with a JSON of the following format:
{{
    "status": "SIMILAR" | "NEW",
    "goal": [Insert name of the high-level goal the task is for]",
    "description": [Insert 1-2 sentence description of the goal.  Provide specific references to the user's current actions],
    "existing_tasks": [
        {{
            "task": [Insert name of the task],
            "description": [Insert 1-2 sentence description of the task], 
            "importance": [Insert rating 1-10 about how important the task is]
        }}
        // List of past tasks that are still relevant
    ],
    "new_tasks": [
        {{
            "task": [Insert name of the task],
            "description": [Insert 1-2 sentence description of the task], 
            "importance": [Insert rating 1-10 about how important the task is]
        }}
        // List of new tasks or empty array if no new tasks identified
    ],
    "context": [<DETAIL>, <DETAIL>, <DETAIL>]
}}
"""

NEW_TOOLS_PROMPT = """
You are a helpful assistant tasked with generating agents to support a user's tasks.

# Generate Agents

Using a summary of the user's current workflow and their task, generate agents that would help the user complete the task. Provide concrete and concise descriptions of agents.
Agents should be standalone web applications or prompts. They should have a **highly specific** and scoped purpose.
Examples of agents for creative writing might include a scenery generator, a simulated audience member, and a copywriter. 

Consider these points when coming up with agents:
- What specific tasks is the user working on?
- What are parts of their workflows that could be aided by agents?

## Implementation
For each agent, provide detailed instructions to a software engineer about how it can be implemented.

## Evaluation Criteria
For each agent you generate, evaluate its strength using two scales:

### 1. Utility Scale

Rate how useful the user would find the agent for their task.
Consider:

- **Demonstrated need**: Has the user demonstrated that they are struggling with this task?
- **Likelihood of using**: Will the user repeatedly interact with the agent?

Score: **1 (no explicit demonstrated need, one-off use)** to **10 (explicit demonstrated need, repeated use)**. Only provide high score (8-10) if there is **direct and specific evidence** the user would find the agent useful. Cite the specific examples in the purpose.

### 2. Feasibility Scale

Rate how likely it is that an LLM could implement this agent in one-shot without errors. Agents that require access to external APIs / services OR require extensive user input should be considered infeasible.
Consider: 
- **Complexity**: How complex is the agent that is proposed? How difficult would it be to implement the tool? 
- **Integrations**: Does the agent require integration with external APIs or services?
- **Ease of Use**: How much input does it require from the user? 
- **Learnability** How easy is it for a user to learn how to use the agent if they were presented with it? 

Score: **1 (difficult implemented)** to **10 (extremely trivial implementation)**.

# Input

Below is a set of transcribed actions and interactions that the user has performed:

## User Activity
The user is completing the following tasks: 
{tasks}

Additional Task Context:
{task_context}

# Task

Generate **5 distinct, well-supported agents** that can support the user to complete their task. Vary the confidence levels.
At least 1-2 agent that would aid with **repeated tasks or manual processes** the user is doing, and at least 1-2 agents that would **expand the capabilities** of what the user can do. 
Each agent must be different in purpose from each other.  


Return your results in this exact JSON format:

{{
  "agents": [
    {{
        "name": [Insert the name of the tool], 
        "id": [Unique identified],
        "purpose": "[Insert a 1-2 sentence description of the tool]",
        "implementation": [Write 3-4 sentences of instruction to how the tool could be implemented]",
        "utility": "[Utility score (1–10)]",
        "feasibility": "[Feasibility score (1–10)]",
    }},
    ...
  ]
}}
"""

CONTINUING_TOOLS_PROMPT = """
You are a helpful assistant tasked with generating agents to support a user's tasks.

# Agents
{current_tools}

# User Activity
### Goal
{goal}

### Tasks
{tasks}

### Task Context
{task_context}

# Task
## Assess Existing Agents
First, using a summary of the user's current workflow and their task, assess the utility of each existing agent. 
Raise the utility score if there is more evidence that the agent would be more helpful for the user. Lower the utility score if it would be less helpful or is no longe relevant. 

## Suggest New Agents
Then, based on the current activity, provide suggestions for new agents that would help the user with the task. If the current tools are sufficient, do not return any new agents.
Provide concrete and concise descriptions of agents. Agents should be standalone web applications or prompts. They should have a **highly specific** and scoped purpose.
Examples of agents for creative writing might include a scenery generator, a simulated audience member, and a copywriter. 

Consider these points when coming up with agents:
- What specific tasks is the user working on?
- What are parts of their workflows that could be aided by agents?

### Implementation
For each agent, provide detailed instructions to a software engineer about how it can be implemented.

### Evaluation Criteria
For each agent you generate, evaluate its strength using two scales:

#### 1. Utility Scale

Rate how useful the user would find the agent for their task. Consider:

- **Demonstrated need**: Is user currently struggling with this task in their workflow?
- **Likelihood of using**: Will the user repeatedly interact with the agent?

Score: **1 (not that useful)** to **10 (extremely useful, will drastically improve workflow)**. Only provide high score (8-10) if there is **direct and specific evidence** the user would find the agent useful. Cite the specific examples in the purpose.

#### 2. Feasibility Scales
Rate how likely it is this agent can be provided in a simple and minimal interface. Implementations that require access to external APIs / services OR require extensive user input should be considered infeasible.
Consider: 
- **Complexity**: How complex is the agent that is proposed? How difficult would it be to implement the tool? 
- **Integrations**: Does the agent require integration with external APIs or services?
- **Ease of Use**: How much input does it require from the user? 
- **Learnability** How easy is it for a user to learn how to use the agent if they were presented with it? 

Score: **1 (infeasible)** to **10 (extremely feasible)**.

Return your results in this exact JSON format:

{{
    "agents": [
        {{
            "name": [Insert the name of the agent], 
            "id": [Unique identifier of the existing tool or new identifier],
            "purpose": "[Insert a 1-2 sentence description of the agent]",
            "implementation": [Write 3-4 sentences of instruction to how the agent could be implemented]",
            "utility": "[Utility score (1–10)]",
            "feasibility": "[Feasibility score (1–10)]",
        }},
        ...
        // Return for all agents (old and new). Return empty list if no agents are needed for the task.
    ]
}}
"""

ALTERNATIVE_TOOLS_PROMPT="""
You are both a Senior PM and a Software Architect working together to ideate and scope lightweight agents to help a user with:
# Context
## Tasks
{tasks}

## Context & pain-points
# {task_context}

#
**Phase 1: Ideation**
First start with 8–10 bold, creative agent concepts with a diverse range of automation, capability expansion, or delight. Provide concrete and concise descriptions of agents. Agents should be standalone web applications or prompts. They should have a **highly specific** and scoped purpose. Do not report on these ideas. 

**Phase 2: Selection**
Choose the top 5 (2 automation, 2 expansion, 1 wildcard), justifying each choice by referencing exact user needs from {task_context}.

** Phase 3: Idea Refinement**
For the 5 best ideas, make them even more creative and useful. 

**Phase 4: Evaluation**
For each of the 5 ideas, evaluate its feasiblity:

Rate whether this idea is feasible to implement as a single-page web application. Implementations that require access to external APIs / services (e.g., Google Drive API) OR require extensive user input should be considered infeasible. 
Consider: 
- **Complexity**: How complex is the agent that is proposed? How difficult would it be to implement the tool? 
- **Integrations**: Does the agent require integration with external APIs or services?
- **Ease of Use**: How much input does it require from the user? 
- **Accuracy** How accurate would the information from the tool be?

Score: 0 (infeasible) or 1 (feasible)

# Output
Return your results for ONLY the 5 selected agents in this exact JSON format:
{{
    "agents": [
        {{
            "name": [Insert the name of the agent], 
            "id": [Unique identifier of the existing tool or new identifier],
            "purpose": "[Insert a 1-2 sentence description of the agent]",
            "implementation": [Write 3-4 sentences of instruction on how the agent could be implemented if it is feasible OR justification as to why the tool is not feasible]",
            "feasibility": "[Feasibility judgement (0/1)]",
        }},
        ...
    ]
}}
"""

CONTINUING_ALTERNATIVE_TOOLS_PROMPT="""
You are both a Senior PM and a Software Architect working together to decide whether there are new lightweight tools to help the user with their task:

# Context
## User Tasks
{tasks}

## Context & pain-points
{task_context}
## Existing Ideas
{tasks}

# Task
## Phase 1: Ideate on new tools
Brainstorm 8-10 bold, creative agent concepts that are different from the existing ideas. They should have a highly specific and scoped purpose. Agents should be standalone web applications or prompts. Do not report these ideas.

## Phase 2: Select the best 3 ideas
Choose the top 3 (1 automation, 1 expansion, 1 wildcard), justifying each choice by referencing exact user needs from the user's context. 

## Phase 3:
For the 3 best ideas, make them even more creative and useful. 

## Phase 4: Evaluate new tools
For each of the ideas, evaluate its feasibility:

### Feasibility Scales
Rate whether this idea is feasible to implement as a single-page web application. Implementations that require access to external APIs / services (e.g., Google Drive API) OR require extensive user input should be considered infeasible. 
Consider: 
- **Complexity**: How complex is the agent that is proposed? How difficult would it be to implement the tool? 
- **Integrations**: Does the agent require integration with external APIs or services?
- **Ease of Use**: How much input does it require from the user? 
- **Accuracy** How accurate would the information from the tool be?

Score: 0 (infeasible) or 1 (feasible)

# Output
Return your results in this exact JSON format:
{{
"agents": [
{{
"name": [Insert the name of the agent],
"id": [Unique identifier of the existing tool or new identifier],
"purpose": "[Insert a 1-2 sentence description of the agent]",
"feasibility": "[Feasibility judgement (0/1)]",
"implementation": [Write 3-4 sentences of instruction on how the agent could be implemented if it is feasible OR justification as to why the tool is not feasible]",
}},
...
// Return the top 3 agents. Return empty list if no agents are needed for the task.
]
}}
"""

# CONTINUING_ALTERNATIVE_TOOLS_PROMPT="""
# You are both a Senior PM and a Software Architect working together to decide whether there are new lightweight agents you should build to help users with:
# - Tasks: {tasks}
# - Context & pain-points: {task_context}

# **These are the existing ideas**:
# {current_tools}

# **Phase 1: Evaluate the utility of the existing tools**
# For each existing tool, reflect on how useful the user would find the agent given their updated task. Note whether the agent is no longer relevant for the task.

# **Phase 2: Ideate**
# Brainstorm up to 5 bold, creative agent concepts with a diverse range of automation, capability expansion, or delight that are **NOT** already covered by existing ideas. 
# Provide concrete and concise descriptions of agents. Agents should be standalone web applications or prompts. They should have a **highly specific** and scoped purpose. Do not report on these ideas. 

# **Phase 3: Evaluation**
# For each of the ideas, evaluate its strength using two scales:

# 1. Utility Scale

# Rate your confidence based on how useful the user would find the agent for their task. Consider:

# - **Demonstrated need**: Is user currently struggling with this task in their workflow?
# - **Likelihood of using**: Will the user repeatedly interact with the agent?

# Score: **1 (not that useful)** to **10 (extremely useful, will drastically improve workflow)**. Only provide high score (8-10) if there is **direct and specific evidence** the user would find the agent useful. Recall that most tools will only score a *5* on this scale.

# 2. Feasibility Scales
# Rate how likely it is this agent can be provided in a simple and minimal interface. Implementations that require access to external APIs / services OR require extensive user input should be considered infeasible.
# Consider: 
# - **Complexity**: How complex is the agent that is proposed? How difficult would it be to implement the tool? 
# - **Integrations**: Does the agent require integration with external APIs or services?
# - **Ease of Use**: How much input does it require from the user? 
# - **Accuracy** How accurate would the information from the tool be?

# Score: **1 (infeasible)** to **10 (extremely feasible)**.

# Return your results in this exact JSON format:
# {{
#     "agents": [
#         {{
#             "name": [Insert the name of the agent], 
#             "id": [Unique identifier of the existing tool or new identifier],
#             "purpose": "[Insert a 1-2 sentence description of the agent]",
#             "implementation": [Write 3-4 sentences of instruction to how the agent could be implemented]",
#             "utility": "[Utility score (1–10)]",
#             "feasibility": "[Feasibility score (1–10)]",
#         }},
#         ...
#         // Return for all agents (old and new). Return empty list if no agents are needed for the task.
#     ]
# }}
# """