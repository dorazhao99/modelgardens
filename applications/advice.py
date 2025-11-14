from pydantic import BaseModel
from typing import List

SYSTEM_PROMPT = "You are a helpful assistant." 

INSIGHT_ADVICE_PROMPT_V1 = """
You are approaching this task through a design-thinking mindset.
Your goal is to understand the human behind the query and use empathy, context, and creative reasoning to generate a response that aligns with their deeper needs or goals.

Use the following insights about {user_name} to empathize and reframe the query if relevant.
If the insights are not relevant, answer normally.
Input

INSIGHTS:
{insights}

QUERY:
{query}

Output

Generate your response to the query. In addition, provide reflective metadata in the following JSON format:

{{
  "response": "Your response to the query, informed by empathy and insight-driven reasoning.",
  "insights": ["List of IDs. Return an empty list if no insights were applied."],
  "reframing": "How you interpreted or reframed the user's query from a human-centered perspective.",
  "reasoning": "1–2 sentences explaining why specific insights were (or were not) used and how they shaped your framing."
}}
"""

INSIGHT_ADVICE_PROMPT_V2 = """
You are approaching this task through a design-thinking mindset.
Your goal is to understand the human behind the query and use empathy, context, and creative reasoning to generate a response that aligns with their deeper needs or goals.

Use the following insights about {user_name} to empathize and reframe the query if relevant.
If the insights are not relevant, answer normally.

Follow this explicit, step-by-step methodology:
1. Read the query and the insights. Look at the context that the insights are related to and see if they are relevant to the query. For example, insights about knowledge work or productivity may not be relevant to queries about {user_name}'s personal life.
Err on the side of caution and assume that the insights are not relevant unless they are strongly likely to be relevant.
2. If the insights are NOT relevant, proceed to answer the query normally.
3. If there are any insights that are relevant, select the insight MOST relevant. 
4. With the selected insight, use it to empathize and reframe the query provided. Think about how the insight might shape the response the user needs. 

#Input
INSIGHTS:
{insights}

QUERY:
{query}

# Output

Generate your response to the query. In addition, provide reflective metadata in the following JSON format:

{{
  "response": "Your response to the query, informed by empathy and insight-driven reasoning.",
  "insights": "ID of the selected insight.",
  "reframing": "How you interpreted or reframed the user's query from a human-centered perspective.",
  "reasoning": "1–2 sentences explaining why specific insights were (or were not) used and how they shaped your framing."
}}
"""

INSIGHT_ADVICE_PROMPT_V3 = """
You are an expert in design-thinking, specializing in the EMPATHIZE and DEFINE steps, combining **empathic insight analysis** with the **“How Might We” (HMW)** framework for creative problem reframing and solution generation.  
Your goal is to understand the human behind the query and use empathy, context, and creative reasoning to generate advice that aligns with their deeper needs or goals.

## Step-by-Step Methodology

### 1.Evaluate insight relevance
Read the **query** and the **insights** about {user_name}.  
Determine whether any insights are relevant to the user’s query context.  
If no insights are clearly relevant, answer the query normally.  
If one or more are relevant, select the **AT MOST {limit} most relevant insights**.
Err on the side of caution and assume that the insights are not relevant unless they are strongly likely to be relevant.


### 2. Reframe the problem using the HMW framework
If an insight is relevant:
- Treat the query as the **problem scenario**.  
- Reframe the query into a **“How Might We” statement**. A "How Might We" statement is a small actionable questions that retain your unique and specific perspective. Generate at least 3 candidate HMW statements.

Strategies to generate HMW question include the following:
1. Amp up the good: Focus on what’s working well and make it even better.
2. Remove the bad: Identify pain points and find ways to eliminate them.
3. Explore the opposite: Flip the problem to see it from a radically different angle.
4. Question the assumption: Challenge what’s being taken for granted.
5. ID unexpected resources: Find overlooked assets or people that could help.
6. Create an analogy from need or context: Use parallels from other domains for inspiration.
7. Change a status quo: Challenge and rethink existing norms or processes.

### 3. Select the most compelling HMW statement
- Select the HMW statement that would lead to the biggest change in advice compared to the original query.
- If there are multiple HMW statements that would lead to the same change in advice, select the one that is most creative and innovative.

## Examples
Query: Need to increase customers at ice cream store
User Insight: Licking someone else’s ice cream cone is more tender than a hug.

1. HMW Statement: "Amp up the good: HMW make the “tandem” of ice cream cones?"
2. HMW Statement: "Explore the opposite: HMW make solitary-confinement ice cream?"
3. HMW Statement: "Create an analogy from need or context: HMW make ice cream like a therapy session?"


Question: Redesign the ground experience at a local international airport
User Insight: Parents need to entertain their children is a large part of the burden so that they are not a nuisance to other passengers

1. HMW Statement: "Remove the bad: HMW separate the kids from fellow passengers?"
2. HMW Statement: "ID unexpected resources: HMW leverage free time of fellow passengers to share the load?"
3. HMW Statement: "Change a status quo: HMW make playful, loud kids less annoying?"
4. HMW Statement: "Play against the challenge: HMW make the airport a place that kids want to go?"


## Input
INSIGHTS:
{insights}

QUERY: 
{query}

## Output
Provide your output in the following JSON format:

{{
    "insights": [List of IDs of the selected insight (if any).],
    "hmw_candidates": [List of candidate HMW statements. None if no insights were selected.],
    "hmw_selected": "Selected HMW statement in the format of 'Strategy: HMW statement'. None if no insights were selected.",
    "reasoning": "1–2 sentences explaining how and why specific insights shaped (or did not shape) the reframing and advice."
}}
"""

ADVICE_PROMPT = """
Generate a response to the user's query.

# Input

QUERY:
{query} 

# Output
Return the response in a JSON format.

{{
    "response": "Response to the user's query"
}}
"""

RESPONSE_ADVICE_PROMPT = """
You have the following query from the user and suggested problem reframings. Generate a response to the query based on the potential reframings.

QUERY: {query}

REFRAMING: {hmw_statement}
"""

INSIGHT_ADVICE_PROMPTS = {
    "v1": INSIGHT_ADVICE_PROMPT_V1,
    "v2": INSIGHT_ADVICE_PROMPT_V2,
    "v3": INSIGHT_ADVICE_PROMPT_V3,
}


class InsightBasedAdvice(BaseModel):
    insights: List[str]
    reasoning: str
    hmw_candidates: List[str]
    hmw_statement: str

class Advice(BaseModel):
    response: str
