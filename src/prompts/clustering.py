CLUSTERING_PROMPT = """
You are an expert analyst. You are given a set of related higher-level and lower-level user needs are shown below. 

Your job is to synthesize these statements into a set of needs that reflect more **deep seated and longer-lasting problems** that may not be fixed by a single solution a user has. 

The goal is to think of the more **complicated needs** that are unspoken and underlying what we observe. 

Here are some guiding questions:
- **WHY** is the user is doing these actions? What is the goal of their task? 
- What might the user be **thinking** and **feeling** in addition to what they are doing?
- What are the hidden or implicit needs exemplified by this set of needs? 

# Guidelines
- Needs can be explicit --- directly stated by the user -- or implicit -- requiring some creative interpretation. 
- Needs must be expressed as **VERBS** (action-oriented, present tense) describing what the user is trying to accomplish, **NOT as nouns**. 
- Each need statement is phrased as: "User needs a way to ___ so that they can ___." These capture both the requirement (what users need) and the rationale (why it matters).
- The deep-seated needs should still be specific and detailed. Do not provide overly generic needs.

# User Needs
{higher_level}

{lower_level}

# Output
Return **only** JSON in the following format. Return only UNIQUE needs. This may look like returning just 1 summarizing need.

# Evaluation Criteria
##  Confidence (1-10) 
On a scale from 1 (not critical) to 10 (life-changing for the user), how critical is this need to the user's success or satisfaction?
Reminder that most needs are likely to be < 5 (not critical) unless there is repeated, demonstrated evidence that this is a need.  
Take into account the confidences of the lower-level needs when evaluating confidence. For example, if the lower-level needs have low confidence, then the confidence for the higher-level need should also be low confidence.

{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Detailed explanation describing why this is a need for the user,
    }}
  ]
}}
"""