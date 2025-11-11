from pydantic import BaseModel
from typing import List, Dict, Literal

class ClassifierMerge(BaseModel):
    label: Literal["IDENTICAL", "SIMILAR", "UNRELATED"]
    target: List[int]

class Insight(BaseModel):
    title: str
    insight: str
    context: str

class Insights(BaseModel):
    insights: List[Insight]

class Evidence(BaseModel):
    supporting: List[str]
    contradicting: List[str]

class FinalInsight(BaseModel):
    title: str
    tagline: str
    insight: str
    context: str
    merged: List[str]
    reasoning: str


class FinalInsights(BaseModel):
    insights: List[FinalInsight]

class InsightSupportResponse(BaseModel):
    evidence: List[str]
    confidence: int
    reasoning: str
    context: str

class RefinedInsightResponse(BaseModel):
    insight: Insight 
    support: InsightSupportResponse

class SimilarInsightsResponse(BaseModel): 
    insights: List[RefinedInsightResponse]

INSIGHT_FORMAT = """
{{
    "insights": [
        {{
            "title": "Thematic title of the insight",
            "insight": "Insight in 3-4 sentences",
            "context": "[1-2 sentences when this insight might apply (e.g., when writing text, in social settings)]",
        }}, 
        {{
            "title": "Thematic title of the insight",
            "insight": "Insight in 3-4 sentences",
            "context": "[1-2 sentences when this insight might apply (e.g., when writing text, in social settings)]",
        }}
        ...
    ]
}}
"""

INSIGHT_PROMPT_INTERVIEW = """
You are an expert in design-thinking, especially in the Empathize and Define stages. Your task is to produce a set of insights given an empathy map about a user. 

An "Insight" is a remarkable realization that you could leverage to better respond to a design challenge. 
Insights often grow from contradictions between two user attributes (either within a quadrant or from diﬀerent quadrants) or from asking yourself “Why?” when you notice strange behavior. One way to identify the seeds of insights is to capture “tensions” and “contradictions” as you work.

Given this input, produce around {limit} insights about {user_name}. Focus only on the insights, not on potential solutions for the design challenge.

# Input
You are provided these traits from direct observation about what {user_name} is doing, feeling / thinking, and saying:

WHAT {user_name} DID:
{actions}

WHAT {user_name} FELT / THOUGHT:
{feelings}

WHAT {user_name} SAID:
{what_i_say}
"""

INSIGHT_PROMPT = """
You are an expert in design-thinking, especially in the Empathize and Define stages. Your task is to produce a set of insights given an empathy map about a user. 

An "Insight" is a remarkable realization that you could leverage to better respond to a design challenge. 
Insights often grow from contradictions between two user attributes (either within a quadrant or from two diﬀerent quadrants) or from asking yourself “Why?” when you notice strange behavior. One way to identify the seeds of insights is to capture “tensions” and “contradictions” as you work.

Given this input, produce around {limit} insights about {user_name}. Focus only on the insights, not on potential solutions for the design challenge.

# Input
You are provided these traits from direct observation about what {user_name} is doing and feeling:

WHAT {user_name} DID:
{actions}

WHAT {user_name} FELT:
{feelings}

"""

INSIGHT_JSON_FORMATTING_PROMPT = """
You are an expert in formatting insights into a JSON format. Your task is to format a list of insights provided in prose into a JSON format.

# Input
You are provided with a list of insights in prose format.
{insights}

# Output
Return your results in this exact JSON format:
{format}
"""

INSIGHT_SUPPORT_PROMPT = """
You are an expert in design-thinking. Your task is to evaluate an insight against a set of observations about the user 

Follow this explicit, step-by-step methodology:
1. Read the insight and the set of observations. Check if any of the observations directly contradict the insight. If so, set the confidence score to 0 and return the evidence that contradicts the insight.
2. If there are no contradictions, go through the observations and select those that strongly support the insight if any exist. Use this to form a confidence score about how well-supported the insight is. 
3. Read through the observations again, and evaluate insight holistically. Use this to update the confidence score about how well-supported the insight is. Any contradictions should lower confidence scores.
4. Look at the confidence scores of the observations and update the confidence score of the insight accordingly. For example, if the confidence score of the observations are all low, the confidence score of the insight should be low. However, having high confidence scores for the observations does NOT mean the confidence score of the insight should be high.

# Criteria
Confidence Score:
- 0: The insight is contradicted by the observations.
- 1-3: The insight is supported by the observations, but not strongly.
- 4-6: The insight is supported by the observations.
- 7-10: The insight is strongly and explicitly supported by the observations.

When scoring, recall the following:
1. If there is evidence that supports the insight but not explicitly or extremely obvious way, the confidence is likely to be 4-6. 
2. To reach a confidence score of 7-10, this requires **overwhelming evidence** from the observations or the user explicitly stating the insight. 
3. Feelings are inferred, so if the insight is only supported by feelings, the confidence score is likely to be low. 

# Input 
You are provided with an insight about the user and an accompanying set of observations about how the user thinks and feels. 

INSIGHT
{insight}

WHAT {user_name} DID: 
{actions}

HOW {user_name} FELT:
{feelings}

# Output
Return your results in this exact JSON format:
{{
    "evidence": [List of observations supporting or contradicting the insight],
    "confidence": "[Confidence score (0-10)]",
    "reasoning": "[1-2 sentences explaining the reasoning behind the confidence score]",
}}
"""


FIND_SIMILAR_INSIGHTS_PROMPT = """
You are an expert in design-thinking. You will label a source insight against a list of target insights based on how similar they are to each other.

# Insight
Source Insight:
{source_insight}

Target Insights:
{target_insights}

# Task

Use exactly these labels:

(A) IDENTICAL – One or more of the target insights say practically the same thing as the source insight AND in the same context.
(B) SIMILAR   – One or more of the target insights relate to a similar idea or topic as the source insight.
(C) UNRELATED – The source insight is fundamentally different from the target insights.

If SIMILAR, select AT MOST the 3 most similar insights. If there are less than 3 similar insights, return all of them.
If IDENTICAL, return ALL IDENTICAL insights.
If UNRELATED, return an empty list.

Always refer to insights by their numeric IDs.

Return **only** JSON in the following format:

{{
    "label": "IDENTICAL" | "SIMILAR" | "UNRELATED",
    "target": [<ID>, ...] // empty list if UNRELATED
}}
"""

HANDLE_IDENTICAL_PROMPT = """
You are an expert in design-thinking. You will handle an identical insight by combining the source insight with the target insights.

Your task is to combine the source insight with the target insights into a single insight. 

Use the following criteria to update the insight:
1. Consider the source insight and target insights. Does the insight or the title change by merging these togeether?
2. Next, look at the supporting evidence provided for each of the insights. Does the confidence that the insight is supported by the observations increase, decrease, or stay the same?
3. Finally, think about the contexts in which the insight might apply. Are the insights about the same contexts or different contexts? Update the context if needed.

# Criteria
Use the following criteria to evaluate the confidence score. 

Confidence Score:
- 0: The insight is contradicted by the observations.
- 1-3: The insight is supported by the observations, but not strongly.
- 4-6: The insight is supported by the observations.
- 7-10: The insight is strongly and explicitly supported by the observations.

When judging, recall the following:
1. To reach a confidence score of 7-10, this requires **overwhelming evidence** from the observations or the user explicitly stating the insight. 
2. Feelings are inferred, so if the insight is only supported by feelings, the confidence score is likely to be low. 

# Input
You are provided with a source insight and a list of target insights that say practically the same thing as the source insight.

SOURCE INSIGHT
{source_insight}

TARGET INSIGHTS
{target_insights}

# Output
Return the following JSON format:
{{
    "insight": {{
        "title": "Thematic title of the insight",
        "insight": "Insight in 3-4 sentences",
    }},
    "support": {{
        "evidence": [List of observations supporting the insight],
        "confidence": "[Confidence score (0-10)]",
        "context": "[1-2 sentences when this insight might apply (e.g., when writing text, in social settings)]",
    }}
}}
""" 

HANDLE_SIMILAR_PROMPT = """
You are an expert in design-thinking. You will create a refined insight by considering a set of similar insights.

Recall an "Insight" is a remarkable realization that you could leverage to better respond to a design challenge. 
Insights often come from contradictions between two user attributes or from asking yourself “Why?” when you notice strange behavior.
One way to identify the seeds of insights is to capture “tensions” and “contradictions” as you work.

Given the input insights, you can take any of the following actions:
- **Edit** an insight for clarity, precision, or brevity.
- **Merge** insights that convey the same meaning.
- **Add** a new insight if a new contradiction or motivation is revealed.
- **Remove** insights that become redundant after merging or splitting.

# Evaluation Criteria
For each insight you revise, evaluate the confidence score using the following criteria:

Confidence Score:
- 0: The insight is contradicted by the observations.
- 1-3: The insight is supported by the observations, but not strongly.
- 4-6: The insight is supported by the observations.
- 7-10: The insight is strongly and explicitly supported by the observations.

When judging, recall the following:
1. To reach a confidence score of 7-10, this requires **overwhelming evidence** from the observations or the user explicitly stating the insight. 
2. Feelings are inferred, so if the insight is only supported by feelings, the confidence score is likely to be low. 

# Input
You are provided with a source insight and a list of target insights that are similar to the source insight.
SOURCE INSIGHT
{source_insight}

TARGET INSIGHTS
{target_insights}

# Output
Return a list of refined insights in the following JSON format:

{{
    "insights": [
        {{
            "insight": {{
                "title": "Thematic title of the insight",
                "insight": "Insight in 3-4 sentences",
            }},
            "support": {{
                "evidence": [List of observations supporting the insight],
                "confidence": "[Confidence score (0-10)]",
                "context": "[1-2 sentences when this insight might apply (e.g., when writing text, in social settings)]",
            }}
        }}, ...
    ]
}}
"""

INSIGHT_SYNTHESIZER_PROMPT = """
You are an expert design-thinker, especially in the EMPATHIZE and DEFINE stages. 
I have insights across multiple sessions of observing {user_name} along with the context in which the insight emerges. 
Your task is to help synthesize across the insights and produce a final set of insights about {user_name}.

Across the insights, consider the following when combining them: 
1. Which insights appear across most of them as a recurring theme or pattern?
2. Which appear only in specific situations or for specific people?
3. Which insights contradict each other — and what might that reveal about unique tensions?

# Input
These are the insight generated across {session_num} sessions of observation.

{input}

# Output
Return the final list of insights in a JSON format.  When writing the insight and tagline, emphasize language about what Michelle is feeling or what is motivating her. 

{{
    "insights": [
        {{
            "title": "Thematic title of the insight",
            "tagline": "Provide the insight in a succinct statement (1-2 sentences).", 
            "insight": "Insight in 3-4 sentences",
            "context": "1-2 sentences when this insight might apply (e.g., when writing text, in social settings)",
            "merged": [List of insight IDs (Session #-ID) that are merged], // Return a list with a single ID if the insight is not merged
            "reasoning": "Explain the reasoning behind the insight"
        }},
    ...
    ]
}}
"""

INSIGHT_INTERVIEW_PROMPT = """
You are an expert in design-thinking in the EMPATHIZE and DEFINE stage. You are given an empathy map about {user_name} and a set of initial user insights. 
You have the opportunity to interview {user_name} to help refine the insights. Your task is to come up with {limit} survey questions to ask {user_name} that will improve user insights. The survey questions should include fixed responses (e.g., multiple choice, true / false) rather than open-ended questions. To answer the questions, you can use known measures such as Likert scales, feeling thermometers, etc. 

Use the following reasoning process:
1. Consider the provided empathy map and insights. What critical assumptions are being made here that need to be clarified? Use this to draft an initial set of ten questions. Each question should be short and understandable. 
2. Then, think about any important unknown motivations, contradictions, or tensions that are identified. Are there any confusing things she did or felt? Update the set of questions as needed. 
3. Imagine the responses that {user_name} would give to each of these questions and how these might change the insights that are created. Rank the questions by those that would provide maximal amount of information. 
4. Finally, return the top three best questions to ask to {user_name}.

# Input
We provide the empathy map generated about {user_name}. 

{empathy_map}

{insights}

# Output
Return the top {limit} survey questions in a JSON format.

{{
    "questions": [
        {{
            "question": "Survey question",
            "options": "Response options",
        }}
    ]
}}
"""