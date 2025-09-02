INTENT_PROMPT = """
What is the underlying user intent expressed by this need:
{body}

Write the intent in ~1 sentence in a format that will be good for clustering using HDBSCAN.
"""

COMPARE_PROMPT = """
You are an expert design researcher and need-finding analyst. Your task is to synthesize and refine a set of user needs into a single, high-quality list. You must ensure clarity, precision, and completeness while avoiding redundancy.

# Instructions
You are given a set of user needs about Dora. Your task is to produce a final list of needs. You MAY: 

1. Edit — Improve clarity, precision, and brevity of needs without changing meaning.
2. Combine — Combine two or more needs if they convey the same underlying idea.
3. Split — Separate a need into multiple distinct needs if it contains more than one claim.
4. Add — Introduce a new need if an implied but missing idea is revealed by the evidence.
5. Remove — Delete redundant needs after merging or splitting.

# Methodology
1. Compare Sets
Examine needs for overlaps, conflicts, and unique statements. 

Identify:
- Exact duplicates → remove.
- Similar needs → merge.
- Contradictions → retain both but clarify distinctions.
- Gaps → add missing needs.

2. Consolidate Needs
Use simple, clear, action-oriented phrasing. Focus on the underlying user problem, not potential solutions. Preserve important nuances.

3. Output Format
Produce a JSON array where each need has:
Return **only** JSON in the following format:

# Evaluation Criteria:
Rate each need based on confidence. **Be conservative in your estimates.** Only give ratings 8-10 if there is clear and direct evidence in the observations.

### Confidence Scale
Rate your confidence based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the need?
- **Engagement Level**: Was the interaction meaningful or sustained?

Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# Input
{set_a}
{set_b}

{{
    "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": 1-2 sentence explanation grounded in the transcription describing why this is a need for the user,
      "merged": [List of all IDs included when generalizing into the new need. If this is a new need, return empty list]
  }}
 ]
}}
"""

# COMPARE_PROMPT = """
# You are an expert design researcher and need-finding analyst. Your task is to synthesize and refine a sets of user needs into a single, high-quality list. You must ensure clarity, precision, and completeness while avoiding redundancy.

# # Instructions
# You are given two sets of user needs: Set A and Set B. Your task is to produce a final, unified list of needs by following these rules:

# ## Available Actions
# 1. Edit — Improve clarity, precision, and brevity without changing meaning.
# 2. Combine — Combine two or more needs if they convey the same underlying idea.
# 3. Split — Separate a need into multiple distinct needs if it contains more than one claim.
# 4. Add — Introduce a new need if an implied but missing idea is revealed by the evidence.
# 5. Remove — Delete redundant needs after merging or splitting.

# # Methodology
# 1. Compare Sets
# Examine Set A and Set B for overlaps, conflicts, and unique needs.

# Identify:
# - Exact duplicates → remove.
# - Similar needs → merge.
# - Contradictions → retain both but clarify distinctions.
# - Gaps → add missing needs.

# 2. Consolidate Needs
# Use simple, clear, action-oriented phrasing. Focus on the underlying user problem, not potential solutions. Preserve any important nuances from both sets during merging.

# 3. Output Format

# Produce a JSON array where each need has:
# Return **only** JSON in the following format:

# # Evaluation Criteria:
# Rate each need based on confidence. **Be conservative in your estimates.** Only give ratings 8-10 if there is clear and direct evidence in the observations.

# ### Confidence Scale
# Rate your confidence based on how clearly the evidence supports your claim. Consider:
# - **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
# - **Relevance**: Is the evidence clearly tied to the need?
# - **Engagement Level**: Was the interaction meaningful or sustained?

# Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# # Input
# Set A: 
# {set_a}

# Set B:
# {set_b}

# {{
#     "user_needs": [
#     {{
#       "need": "Verb phrase describing the need",
#       "confidence": Integer between 1-10,
#       "reasoning": "Revised reasoning including any named entities where applicable",
#       "merged": [List of all IDs included when generalizing into the new need. If this is a new need, return empty list]
#   }}
#  ]
# }}
# """

MERGE_PROMPT = """
You are a designer that is an expert in needfinding. A cluster of similar observations about a user are shown below.

You are given a set of observations. Your job is to synthesize these observations into a set of needs that reflect more deep seated and longer-lasting problems that may not be fixed by a single solution a user has.
The goal is to think of the more complicated needs that are unspoken and underlying what we observe.

# Task Instructions
Follow these steps
1. For the set of user observations, select ONLY the observations that are interesting.
2. Ask WHY you think the observations happened and propose a reason.
3. Ask why the reason exists or matters.
4. Suggest an underlying reason. Remember this reason. 
5. Repeat this process THREE more times. Each step you should be getting to a deeper reason. 

# Need Statement Guidelines
1. Make sure the needs are phrased as verbs. Example statements might be "User needs to have a healthy relationship with their girlfriend" or "User needs to not look like a flake" 
2. Do not use overly bland or milquetoast phrasing. Reference specific actions, people, environment, objects, etc. mentioned in the input when needed. 

# Example Reasoning Trace
1. Observe users hold hands when they walk into the furniture store.
2. WHY? They want to feel closer to their partner.
3. WHY? Because they are about to buy furniture together.
4. WHY? Because furniture is an expensive purchase you make together.
5. WHY? Because buying a sofa is a statement of your commitment to each other.
6. WHY? Because how you feel walking in affects the likelihood of whether you walk out with a new sofa. 

# Input
{input}

# Output
Return all of the intermittent need statements generated during the task. 

# Evaluation Criteria

For each need you generate, evaluate its confidence using the following scale. 

### Confidence Scale
Rate how important this need is for the user. 
On a scale from 1 (not critical) to 10 (life-changing for the user), how critical is this need to the user's success or satisfaction?

Reminder that most needs are likely to be < 5 (not critical) unless there is repeated, demonstrated evidence that this is a need.  



Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

{{
  "user_needs": [
    {{
      "need": "Description of the need",
      "confidence":  Integer between 1-10,
      "reasoning": Detailed explanation describing why this is a need for the user,
      "step": Integer representing what step in the reasoning process the need is generated. The larger the step number, the more high-level the need should be.
    }}
  ]
}}

It is **encouraged** to be more speculative and draw higher-level inferences when coming up with needs. Be creative.
"""