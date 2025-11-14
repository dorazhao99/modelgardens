LONGTERM_SOLUTION_PROMPT = """
You are an expert in design-thinking, specialized in the IDEATE and PROTOTYPE stage. 
You are given a DESIGN SCENARIO, USER INSIGHT, and HOW MIGHT WE question that reframes the design scenario. 
Your task is to proposed a long-running solution can take to proactively address the DESIGN SCENARIO and HOW MIGHT WE questions.

# Guidelines
1. Review the problem reframing and ideate a wide range of potential solutions based on the HOW MIGHT WE question. 
2. For each action, evaluate how beneficial they would be to {user_name} given the USER INSIGHTS. Rank the solutions by how much they would benefit her.
3. Next, for each solution, evaluate its implementability given the IMPLEMENTATION CONSTRAINTS. For each solution, decide whether it can implemented under these constraints. If it can be implemented, reflect on how beneficial it would be to {user_name}. Update the ranking of solutions after accounting for implementation. 
4. Refine a solution that will be beneficial to {user_name}. This might involve combining parts of multiple solutions to create a more comprehensive solution.

# Input
DESIGN SCENARIO:
{scenario}

USER INSIGHT:
{insights}

HOW MIGHT WE:
{hmw}

IMPLEMENTATION CONSTRAINTS:
The proposed solutions must be implementable as software. They cannot execute physical-world actions or be physically embodied.  


## Output
Return just the top solution and a short description (2-3 sentences) of how it works
"""

BASELINE_LONGTERM_PROMPT = """
You are given a user-centered DESIGN PROBLEM PROBLEM. 
Your task is to proposed a long-running solution can take to proactively address the DESIGN PROBLEM.

# Guidelines
1. Review the DESIGN PROBLEM and ideate a wide range of potential solutions to address the DESIGN PROBLEM.
2. For each solution, evaluate how beneficial they would be to {user_name}. Rank the actions by how much they would benefit {user_name}.
3. Next, for each action, evaluate its implementability given the IMPLEMENTATION CONSTRAINTS. For each action, decide whether it can implemented under these constraints. If it can be implemented, reflect on how beneficial it would be to {user_name}. Update the ranking of solutions after accounting for implementation. 
4. Select the top solutions that are implementable and beneficial to {user_name}. 

# Input
DESIGN PROBLEM:
{scenario}

IMPLEMENTATION CONSTRAINTS:
The proposed solutions must be implementable as software. They cannot execute physical-world actions or be physically embodied.  

## Output
Return just the top {limit} solutions and a short description (2-3 sentences) of how it works
"""