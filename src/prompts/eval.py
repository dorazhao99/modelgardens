NEEDS_JUDGE = """
You are a careful judge of *user needs*.
Given two needs, classify whether they are similar or not. 

Return 1 if YES they are meaningfully similar or 0 if NO. 

Need 1: {gt}
Need 2: {proposed}

Return only 1 or 0 and nothing else. 
"""

SOLUTIONS_JUDGE = """
You are a an expert in design-thinking and are asked to be a judge of proposed *solutions*.
Given a ground-truth and proposed solution, decide whether the proposed solution is meaningfully similar to the ground-truth solution. Return 1 if YES they are meaningfully similar or 0 if NO. 

Ground Truth Solution: {gt}
Proposed Solution: {proposed}

Return only 1 or 0 and nothing else. 
"""

SOLUTIONS_RERANK = """
You are a an expert in design-thinking and are asked to rank a set of proposed *solutions*.

Given a list of solutions, re-rank them based on how well they meet a user's need. 

User's Need:
{need}
Solutions: 
{solutions}

Return a JSON in the following format with the re-ranked solutions. The first in the list should be the best solution and so forth.
{{
  "solutions": [
    {{
      "solution": "Brief overview of solution",
      "description": "Brief description of the solution",
      "reasoning": Explanation grounded in the observatioins describing why this is a solution to the user's need
    }}
  ]
}}
"""

NEEDS_TYPE = """
You are an expert in needfinding and human-centered design. Your task is to classify a given user prompt into exactly one of the following four need types: Context Need, Common Need, Qualifier Need, or Activity Need.

Use the following definitions to guide your classification:

1. **Common Need** (common): A fundamental, universal, and enduring human need present for most people over time (e.g., socializing, safety). Often met indirectly and may be taken for granted.
2. **Context Need** (context): A need shaped by the situation, environment, or background in which people live, work, or operate (e.g., industry, region, culture). Often goal-oriented (e.g., having a pleasant experience) and not always consciously recognized because it is pervasive.
3. **Activity Need** (activity): A need tied to specific activities someone performs or wants to perform, typically shared by people doing the same task.
4: **Qualifier Need** (qualifier): An immediate need arising from problems with existing solutions, often expressed in terms of desired changes or qualities in a product or service.

# Example
User Need: I want to be able to quickly switch between document tabs without losing my place.
Output:
{{
  "need_type": "qualifier",
  "rationale": "The request reflects a desire to improve an existing solution by preserving context when switching between tabs, which is a specific feature-related improvement."
}}

# Input
User Need: {user_need}

# Output
Return the output as JSON with the following format: 
{{
    "need_type": "common" | "context" | "activity" | "qualifier",
    "rationale": "Explanation for why the need type was selected"
}}
"""

ARMCHAIR_JUDGE = """
You are a careful judge of *user needs*.
Given a candidate statement and a set of existing statements, classify whether the candidate statement is similar to any of the existing statements. 

Return 1 if the existing statements cover the candidate statement or 0 if NO. 

Candidate: {gt}
Existing Statements:
{armchair}

Return only 1 or 0 and nothing else. 
"""

