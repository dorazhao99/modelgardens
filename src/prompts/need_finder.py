BASELINE_PROMPT = """
You are an expert in **design needfinding** and **interaction analysis**.  
You will be provided with a transcript of actions from a user’s screen. Focus on what the **user is doing or not doing** rather than the content on the screen.
Your task is to potential user needs derived from these actions.

### Disclaimer
- Not all actions will surface identifiable user needs.  
- If **no clear needs** can be identified, your output must indicate this clearly in the JSON ("needs_found": FALSE) and leave the "user_needs" list empty.

### Task Details
Your task is to analyze the transcript of user's actions using needfinding techniques from design research. Needs should focus on things that are **unarticulated or unmet**, rather than just their expressed wants. Consider what the user is struggling with, what repeated actions they are taking, etc.

If **and only if** the transcript contains sufficient evidence to support making propositions about the user's needs, return propositions about the user's needs. Return as many propositions as can be substantiated from the transcript. 

Needs should be expressed as **verbs** (action-oriented, present tense) describing what the user is trying to accomplish. They can be explicit --- directly stated by the user -- or implicit -- requiring some creative interpretation. 

For each need, assign a confidence score from 1-10 indicating how well the transcript supports the need. Be conservative in your estimates. Only rate a need with scores 8-10 if there is an abundance of evidence supporting that the user has this need. 

### User Actions
{user_actions}

### Output
Return the following JSON output and nothing else. 
{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Explanation grounded in the transcription describing why this is a need for the user
    }}
  ]
}}
"""

BASELINE_IMAGE_PROMPT = """
You are an expert in **design needfinding** and **interaction analysis**.  
You will be provided with a **sequence of images** (screenshots/frames) from a user’s screen. Infer the user’s actions by comparing changes across images. Focus on what the **user is doing or not doing** rather than the on-screen content itself.
Your task is to **identify potential user needs** derived from these observed actions.

## Important constraints when using images
- Treat the images as evidence of **observable behavior** (e.g., a button appears pressed, a dialog opens, a list is scrolled, a field becomes populated).
- If text in the images is **illegible or cropped**, do **not** guess what it says.
- Prefer concrete, visible cues: cursor position, clicked/pressed states, focus rings, new pages/dialogs, scroll position changes, highlighted selections, progress spinners, error toasts, form validation marks.
- If multiple interpretations are possible, choose the **most conservative** one and lower your confidence accordingly.

## Disclaimer
- Not all image sequences surface identifiable user needs.  
- If **no clear needs** can be identified, your output must indicate this clearly in the JSON (`"no_needs_found": true`) and leave `"user_needs"` empty.

# Task Details
Analyze the image sequence using needfinding techniques from design research. Needs should focus on things that are **unarticulated or unmet**, rather than just expressed wants. Consider what the user is struggling with, what behaviors repeat, and where friction appears (e.g., repeated clicks, opening/closing the same panel, scanning long lists, editing and re-editing).

If—and only if—the images contain sufficient evidence to support **propositions about the user's needs**, return as many as can be **grounded in what is visible**.

Express each need as a **verb phrase** (present tense) describing what the user is trying to accomplish (e.g., “find…”, “compare…”, “recover…”, “export…”). Needs can be explicit (clearly indicated by visible labels/flows) or implicit (inferred from repeated or inefficient behavior).

For each need, assign a **confidence score from 1–10** indicating how well the **images** support the need. Be conservative: reserve 8–10 for cases with abundant, unambiguous visual evidence.

# Input
User observations are provided as images.

# Output
Return the following JSON output and nothing else. 
{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Explanation grounded in the transcription describing why this is a need for the user
    }}
  ]
}}
"""

INTERESTING_PROMPT = """
You are an expert designer conducting need-finding based on user interaction logs and observational summaries.
Your job is to analyze the observations of user behavior. Extract the most interesting observations about their behavior that can inform need-finding and ignore status quo or uninteresting behavior.

## Instructions:
1. Carefully read the provided observations of user interactions.
2. Identify interesting, surprising, or repeated patterns relevant to usability, workflows, or unmet needs.
3. Focus especially on:
- Contradictions in user's actions over time. 
- Repetitive scanning or searching patterns (e.g., exploring menus repeatedly, scrolling excessively, hovering over inactive elements)
- Selection or dwelling behavior (e.g., pausing, rereading, or slowing interactions on specific elements)
- Error recovery or undo attempts (e.g., backtracking, closing dialogs, undoing commands)
- Inefficiencies in completing actions (e.g., taking multiple steps when one would suffice)
- Any moments of confusion, hesitation, or workaround strategies.

Compile a list of interesting observations for the designer based on the following input. 

## User Input
{user_actions}

Produce a JSON output following the format below.
{{
  "observations": [
    {{
      "description": "Description of what is observed",
      "evidence": "Provide specific evidence from the input supporting this observation"
    }}
  ]
}}
"""

NEEDFINDING_TEXT_PROMPT = """
You are an expert design researcher and ethnographer specializing in the practice of needfinding. 
Your goal is to analyze raw observational data and transform it into a structured set of actionable user needs. You must focus on the underlying problem, not potential solutions.

To support effective information retrieval (e.g., using BM25), need statements must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

# Analysis

Using a set of user observations, your task is to analyze these activities, behaviors, and workarounds. Draw insightful, concrete conclusions while explicitly identifying the underlying needs of the user.

# Task

Follow this explicit, step-by-step methodology:

1. Initial Data Synthesis:
   - Think through the key **actions (what the user did)** and **workarounds (clever or inefficient things the user did to overcome a problem).**
   - Key actions that might indicate needs include:
       1. Repetitive scanning or searching patterns, such as exploring multiple menus, scrolling through text, mousing over, and clicking non-active regions.
       2. Selection or dwelling on certain parts of the screen, introspecting, or slowing the pace of interaction.
       3. Undesired effects or attempts to return to a prior state after an action, such as using an undo command or closing a dialog box without using the operation.
       4. Inefficiencies in how the user completes an action (e.g., performing multiple commands when one would suffice).

2. Formulate Core Need Statements:
   - For each significant observation, especially those indicating a struggle or a workaround, formulate a need statement using this format:
     - User needs a way to [verb/user goal], so that [desired outcome/benefit].
   - Constraint: These statements must articulate the underlying need, not a solution. For example, instead of "The user needs a better flashlight," state "The user needs a way to see their work area clearly in low-light conditions, so that they can complete tasks safely and accurately."

3. Uncover Deeper Insights:
   - Analyze the observations for contradictions between what the user says and what they do. Ask **WHY** the user is doing what they did. 
   - When you find a contradiction, articulate the deeper, often unstated, need revealed by this discrepancy.

4. Synthesize Core Needs:
   - Synthesize the inisghts into need statements. Needs should be expressed as **verbs** (action-oriented, present tense).

# Evaluation Criteria:
Rate each need based on confidence. **Be conservative in your estimates.** Only give ratings 8-10 if there is clear and direct evidence in the observations.

### Confidence Scale
Rate your confidence based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the need?
- **Engagement Level**: Was the interaction meaningful or sustained?

Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# Disclaimer
- It is **LIKELY** that no need is found. Not all transcripts will surface identifiable user needs.
- If **no clear needs** can be identified, indicate this clearly in the JSON output ("needs_found": FALSE) and leave the "user_needs" list empty.

# Input

Below is a set of user observations:

## User Observations

{user_actions}

# Output
Generate a detailed analysis with needs statements grounded in the observations. 
At least two of the needs should be **HIGH CONFIDENCE** (i.e., grounded in the observations) and at least should be **LOW CONFIDENCE** (i.e., based on higher-level inference from observations).

Return your results in this exact JSON format.
{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Specific observations about the user from which this need is sourced
    }}
  ]
}}
"""

NEEDFINDING_TEXT_IMAGE_PROMPT = """
You are an expert design researcher and ethnographer specializing in the practice of needfinding.  
Your goal is to analyze **raw observational visual data** (a sequence of images from a user’s screen) and transform it into a structured set of actionable user needs. You must focus on the underlying problem, not potential solutions.

# Analysis

Using the provided **image sequence**, your task is to analyze the **visible activities, behaviors, and workarounds** the user performs. Draw insightful, concrete conclusions while explicitly identifying the underlying needs of the user.

# Task

Follow this explicit, step-by-step methodology:

1. **Initial Data Synthesis**  
   - Carefully examine the sequence of images for **key actions** (what visibly changes on the screen) and **workarounds** (inefficient or repeated visual actions suggesting the user is overcoming friction).  
   - Key **visual** actions that might indicate needs include:
       1. Repetitive scanning or searching patterns — visible in repeated navigation through menus, scrolling through long content, moving between different panels, hovering over elements, or clicking inactive-looking regions.
       2. Selection or focus changes — sustained highlighting of text/objects, focus rings around input fields, lingering on certain panels or dialogs.
       3. Undesired effects or attempts to return to a prior state — closing dialogs without using them, undoing changes, reopening the same page after leaving it.
       4. Inefficiencies — performing multiple visible steps when one should suffice (e.g., navigating through several screens instead of using a shortcut or direct action).

2. **Formulate Core Need Statements**  
   - For each significant **visual** observation, especially those suggesting struggle or workaround, create a need statement in this format:  
     - *User needs a way to [verb/user goal], so that [desired outcome/benefit].*  
   - Constraint: These statements must articulate the underlying need, not a solution.  
     - Example: Instead of "The user needs a bigger button," write "The user needs a way to quickly locate and activate the submit control, so that they can complete the task efficiently."

3. **Uncover Deeper Insights**  
   - Look for contradictions between visible user actions and the apparent intended workflow (e.g., they open a tool but do not use it, they repeatedly close and reopen a panel).  
   - When such contradictions appear, infer the deeper, often unstated, need.

4. **Synthesize Needs**  
   - Express each need as a **verb phrase** (present tense, action-oriented).  
   - For each, assign a **confidence score (1–10)** based on how clearly the image sequence supports it.  
     - Use high scores (8–10) only when the evidence is abundant and unambiguous.

## Disclaimer
- Not all image sequences will surface identifiable user needs.
- If **no clear needs** can be identified, set `"no_needs_found": true` and return an empty `"user_needs"` list.
- Focus on **WHY** the user is doing an action and the goal of their task, not just what they are doing. For example, if we notice that a user is often clicking the "save button" on a word processor, the concrete task is to save a file to disk but the NEED is to "User needs to make sure that their work is kept while working on a project." 

# Input
User observations are provided as images.

# Output
Generate a detailed analysis with needs statements grounded in the observations. 2 of the needs should be low confidence (< 4) and 2 of the needs should be high confidence (> 7).
Return your results in this exact JSON format:
{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Explanation grounded in the transcription describing why this is a need for the user
    }}
  ]
}}
"""

NEEDFINDING_TEXT_PROMPT_CONF = """
You are an expert design researcher and ethnographer specializing in the practice of needfinding. 
Your goal is to analyze raw observational data and transform it into a structured set of actionable user needs related to their goal of {user_goal}.
You must focus on the underlying problem, not potential solutions. Your needs should have **{confidence} confidence** on the confidence scale.

To support effective information retrieval (e.g., using BM25), need statements must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

# Analysis

Using a set of user observations about {user_name}, your task is to analyze these activities, behaviors, and workarounds. Draw insightful, concrete conclusions while explicitly identifying the underlying needs of {user_name}.

# Task

Follow this explicit, step-by-step methodology:

1. Initial Data Synthesis:
   - Think through the key **actions (what the user did)** and **workarounds (clever or inefficient things the user did to overcome a problem).**
   - Key actions that might indicate needs include:
       1. Repetitive scanning or searching patterns, such as exploring multiple menus, scrolling through text, mousing over, and clicking non-active regions.
       2. Selection or dwelling on certain parts of the screen, introspecting, or slowing the pace of interaction.
       3. Undesired effects or attempts to return to a prior state after an action, such as using an undo command or closing a dialog box without using the operation.
       4. Inefficiencies in how the user completes an action (e.g., performing multiple commands when one would suffice).

2. Formulate Core Need Statements:
   - For each significant observation, especially those indicating a struggle or a workaround, formulate a need statement using this format:
     - User needs a way to [verb/user goal], so that [desired outcome/benefit].
   - Constraint: These statements must articulate the underlying need, not a solution. For example, instead of "The user needs a better flashlight," state "The user needs a way to see their work area clearly in low-light conditions, so that they can complete tasks safely and accurately."

3. Uncover Deeper Insights:
   - Analyze the observations for contradictions between what the user says and what they do. Ask **WHY** the user is doing what they did. 
   - When you find a contradiction, articulate the deeper, often unstated, need revealed by this discrepancy.

4. Synthesize Core Needs:
   - Synthesize the insights into need statements. Needs should be expressed as **verbs** (action-oriented, present tense).

# Evaluation Criteria:
Rate each need based on confidence. **Be conservative in your estimates.** Only give ratings 8-10 if there is clear and direct evidence in the observations.

### Confidence Scale
Rate your confidence based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the need?
- **Engagement Level**: Was the interaction meaningful or sustained?

Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# Disclaimer
- It is **LIKELY** that no need is found. Not all transcripts will surface identifiable user needs.
- If **no clear needs** can be identified, indicate this clearly in the JSON output ("no_needs_found": true) and leave the "user_needs" list empty.

# Input

Below is a set of user observations:

## User Observations

{user_actions}

# Output
Generate a detailed analysis with need statements grounded in the observations. Remember need statements should be specific! 
Only retain needs that are related to the user's goal of {user_goal}. 

Return your results in this exact JSON format:

{{
  "no_needs_found": TRUE | FALSE,
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Specific observations about the user from which this need is sourced
    }}
  ]
}}
"""

SIMILAR_PROMPT = """
You will label the relationship of the newly proposed need statement to existing need statements. 

# Needs
New: {new}
Existing: {existing}

# Task

Use exactly these labels:

(A) IDENTICAL – The statements are capturing close to identical or very similar needs of the user. 
(B) SIMILAR   – The statements are diverse but capturing a similar idea. 
(C) UNRELATED – The statements are fundamentally different. 

Always refer to needs by their numeric IDs. 

Note, most needs will be **IDENTICAL** or **UNRELATED**. 

Return **only** JSON in the following format:

{{
  "relations": [
    {{
      "source": <ID of NEW>,
      "label": "IDENTICAL" | "SIMILAR" | "UNRELATED",
      "target": [<ID>, ...] // empty list if UNRELATED
    }}
    // Return one object
  ]
}}
"""

REVISE_PROMPT = """You are an expert analyst. A cluster of similar user needs are shown below, followed by their supporting observations.

Your job is to produce a **final set** of user needs that is clear, non-redundant, and captures everything about the user, {user_name}.

To support information retrieval (e.g., with BM25), you must **explicitly identify and preserve all named entities** from the input wherever possible. These may include applications, websites, documents, people, organizations, tools, or any other specific proper nouns mentioned in the original propositions or their evidence.

You MAY:

- **Edit** a need for clarity, precision, or brevity.
- **Merge** needs that convey the same meaning.
- **Split** a need that contains multiple distinct claims.
- **Add** a new need if a distinct idea is implied by the evidence but not yet stated.
- **Remove** needs that become redundant after merging or splitting.

Never preserve duplicates.

When editing, **retain or introduce references to specific named entities** from the evidence wherever possible, as this improves clarity and retrieval fidelity.

Edge cases to handle:

- **Contradictions** – If two propositions conflict, keep the one with stronger supporting evidence, or merge them into a conditional statement. Lower the confidence score of weaker or uncertain claims.
- **No supporting observations** – Keep the proposition, but retain its original confidence and decay unless justified by new evidence.
- **Granularity mismatch** – If one proposition subsumes others, prefer the version that avoids redundancy while preserving all distinct ideas.
- **Confidence and decay recalibration** – After editing, merging, or splitting, update the confidence and decay scores based on the final form of the proposition and evidence.

## Guidelines
1. Make sure the needs are phrased as verbs. Example statements might be "User needs to have a healthy relationship with their girlfriend" or "User needs to not look like a flake" 
2. Do not use overly bland or milquetoast phrasing. Reference specific actions, people, environment, objects, etc. mentioned in the input when needed. 


## Evaluation Criteria
Rate each need based on confidence. **Be conservative in your estimates.** Only give ratings 8-10 if there is clear and direct evidence in the observations.

### Confidence Scale
Rate your confidence based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the need?
- **Engagement Level**: Was the interaction meaningful or sustained?

Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.


# Input
{body}

# Output

Assign high confidence scores (e.g., 8-10) only when the transcriptions provide explicit, direct evidence that {user_name} has this need. Keep in mind that that the input is what the {user_name} is viewing. It may not be what the {user_name} is actively doing, so practice caution when assigning confidence.

Return **only** JSON in the following format:

{{
    "no_needs_found": TRUE | FALSE,
    "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "confidence": Integer between 1-10,
      "reasoning": Explanation grounded in the transcription describing why this is a need for the user,
       "merged": [List of all IDs included when generalizing into the new need. If this is a new need, return empty list]
  }}
 ]
}}
""

"""
# You are an expert analyst. A cluster of similar user needs are shown below, followed by their supporting observations. 

# Your job is to produce a set of needs that the user, Dora, has by either
# 1. **Generalizing** the set of lower-level needs into a broader need 
# OR
# 2. **Adding** new needs that don't exist. 

# # Guidelines
# - Focus on **WHY** the user is doing an action and the goal of their task, not just what they are doing. 
# - Needs can be explicit --- directly stated by the user -- or implicit -- requiring some creative interpretation. 
# - Needs must be expressed as **VERBS** (action-oriented, present tense) describing what the user is trying to accomplish, **NOT as nouns**. 

# # Example
# If we notice that a user is often clicking the "save button" on a word processor, the concrete task is to save a file to disk but the NEED is to "User needs to make sure that their work is kept while working on a project." 

# Retain the same level of specificity and detail as the needs being merged. 

# # User Needs
# {input}

# # Output
# Return **only** JSON in the following format. 
# Recall the need **MUST** be phrased as a verb (that is, goals and end states) instead of nouns that describe solutions. 


# Remember, if **no clear needs** can be merged, set `"no_needs_found": true` and return an empty `"user_needs"` list. It is better to return an empty list if needs cannot be merged, than to be incorrect.


# {{
#   "no_needs_found": TRUE | FALSE,
#   "user_needs": [
#     {{
#       "need": "Verb phrase describing the need",
#       "confidence": Integer between 1-10,
#       "reasoning": Explanation grounded in the transcription describing why this is a need for the user,
#       "merged": [List of all IDs included when generalizing into the new need. If this is a new need, return empty list]
#     }}
#   ]
# }}
# 
"""

"""
# You are an expert analyst. A cluster of similar user needs are shown below, followed by their supporting observations. 

# You are given a set of lower-level, situational needs. Your job is to synthesize these statements into a set of needs that reflect more **deep seated and longer-lasting problems** that may not be fixed by a single solution a user has. 
# The goal is to think of the more **complicated needs** that are unspoken and underlying what we observe. 

# Here are some guiding questions:
# - **WHY** the user is doing these actions? What is the goal of their task? 
# - What might the user be **thinking** and **feeling** in addition to what they are doing?
# - What are the hidden or implicit needs exemplified by this set of needs? 

# # Guidelines
# - Needs can be explicit --- directly stated by the user -- or implicit -- requiring some creative interpretation. 
# - Needs must be expressed as **VERBS** (action-oriented, present tense) describing what the user is trying to accomplish, **NOT as nouns**. 
# - The deep-seated needs should still be specific and detailed. Do not provide overly generic needs.

# # User Needs
# {input}

# # Output
# Return **only** JSON in the following format. 
# Remember, if **no clear needs** can be merged, set `"no_needs_found": true` and return an empty `"user_needs"` list. It is better to return an empty list if needs cannot be merged, than to be incorrect.

# # Evaluation Criteria
# ##  Confidence (1-10) 
# On a scale from 1 (not critical) to 10 (life-changing for the user), how critical is this need to the user's success or satisfaction?
# Reminder that most needs are likely to be < 5 (not critical) unless there is repeated, demonstrated evidence that this is a need.  
# Take into account the confidences of the lower-level needs when evaluating confidence. For example, if the lower-level needs have low confidence, then the confidence for the higher-level need should also be low confidence.

# {{
#   "no_needs_found": TRUE | FALSE,
#   "user_needs": [
#     {{
#       "need": "Verb phrase describing the need",
#       "confidence": Integer between 1-10,
#       "reasoning": Detailed explanation describing why this is a need for the user,
#       "merged": [<ID1>, <ID2>] # List of lower-level IDs supporting the higher-level need
#     }}
#   ]
# }}
# """

MERGE_PROMPT = """
You are a designer that is an expert in needfinding. A cluster of user needs that {user_name} has are shown below, followed by their supporting observations.

Discard needs that are not related to the user's goal of {user_goal}. 

You are given a set of lower-level, situational needs. 
Your job is to ask *WHY* the user has these needs and surface a set of latent needs that reflect more deep seated and longer-lasting problems that may not be fixed by a single solution that {user_name} has. 
Focus not only on what the user is doing in the moment but also on what they are thinking or feeling. 
**Retain or introduce references to specific named entities** from the evidence wherever possible, as this improves clarity and retrieval fidelity.

# Task Instructions
Let's think step-by-step
1. For the set of user needs, focus on interesting observations.
2. Ask WHY you think the observations happened and propose a reason to get to a deeper reason.
3. Ask why the reason exists or matters.
4. Suggest an underlying reason. 
5. Repeat this process. Each step you should be getting to a deeper reason. Stop when the reason is TOO VAGUE or when you are forcing artifical abstractions.
6. Make sure your reason is not contradicted by evidence in the observations. 

# Need Statement Guidelines
1. Make sure the needs are phrased as verbs. Example statements might be "User needs to have a healthy relationship with their girlfriend" or "User needs to not look like a flake" 
2. Reference specific actions, people, environment, objects, etc. mentioned in the input in the need statement. Avoid generic terms like "seamlessly" or "streamlined" when coming up with the need.

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
Return just the final need generated from following the task instructions. Ensure the need follows the Need Statement Guidelines.  

# Evaluation Criteria
Confidence (1-10) 
Rate your confidence of the need based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the need?
- **Engagement Level**: Was the interaction meaningful or sustained?

Take into account the confidences of the lower-level needs when evaluating confidence. For example, if the lower-level needs have low confidence, then the confidence for the higher-level need should also be low confidence.

{{
  "user_needs": [
    {{
      "need": "Description of the need",
      "confidence":  Integer between 1-10,
      "reasoning": Detailed explanation describing why this is a need for the user,
      "merged": [<ID1>, <ID2>] # List of lower-level IDs supporting the higher-level need,
      "step": Integer representing what step in the reasoning process the need is generated. The larger the step number, the more high-level the need should be.
    }}
  ]
}}

It is **encouraged** to be more speculative and draw higher-level inferences when coming up with needs. 
"""

MERGE_STEP_PROMPT = """
You are a designer that is an expert in need-finding. A cluster of similar observations are shown below.  

The goal is **NOT** to summarize the statements but rather to find a higher-level set of needs that reflect more **deep seated and longer-lasting problems** that may not be fixed by a single solution a user has. 

# Task Instructions
Let's think step-by-step. 
1. Ask **WHY** you think the observations happened and propose a reason that gets at the deeper meaning or cause. 
2. Ask why the reason exists or matters. 
3. Suggest an underlying reason. 
4. Repeat this process THREE more times until you get at the deeper cause. 


# Need Statement Guidelines
- Make sure the needs are phrased as verbs. Example statements might be "User needs to have a healthy relationship with their girlfriend" or "User needs to not look like a flake" 
- Do not use overly generic or milquetoast phrasing. 
- **Retain or introduce references to specific named entities** from the evidence wherever possible, as this improves clarity and retrieval fidelity.


# User Observations
{user_actions}

# Output
Return just a JSON output in the following format. Include all the intermittent statements generated during the task. 

[
    {{
      "description": "Verb phrase describing the result from the step",
      "reasoning": "Explanation behind the thought process. Include explicit evidence from input if there is any."
      "step": Integer representing what step in the reasoning process the need is generated. The larger the step number, the more high-level the need should be.
    }}
]
"""
# MERGE_PROMPT = """
# You are an expert analyst. A cluster of similar needs are shown below.

# Your job is to produce a final set of needs that is clear, non-redundant, and captures everything about the user.

# To support information retrieval (e.g., with BM25), you must explicitly identify and preserve all named entities from the input wherever possible. These may include applications, websites, documents, people, organizations, tools, or any other specific proper nouns mentioned in the original propositions or their evidence.

# You MAY:

# - **Edit** a need for clarity, precision, or brevity.
# - **Merge** needs that convey the same meaning.
# - **Split** a need that contains multiple distinct claims.
# - **Add** a new need if a distinct idea is implied by the evidence but not yet stated.

# Remove needs that become redundant after merging or splitting.

# # General guidelines:
# - Focus on WHY the user is doing an action and the goal of their task, not just what they are doing.
# - Needs can be explicit --- directly stated by the user -- or implicit -- requiring some creative interpretation.
# - Needs must be expressed as VERBS (action-oriented, present tense) describing what the user is trying to accomplish, NOT as nouns.

# # User Needs
# {input}

# # Output
# Generate a detailed analysis with needs statements grounded in the observations. Return your results in this exact JSON format:
# {{
#   "no_needs_found": TRUE | FALSE,
#   "user_needs": [
#     {{
#       "need": "Verb phrase describing the need",
#       "confidence": Integer between 1-10,
#       "reasoning": Explanation grounded in the transcription describing why this is a need for the user
#     }}
#   ]
# }}
# """

NEEDFINDER_PROMPT_V1 = """
You are an expert design researcher and ethnographer specializing in the practice of needfinding.

Your goal is to analyze raw observational data and transform it into a structured set of personalized, actionable user need statements.

# Analysis
Using a set of user observations, your task is to analyze these activities, behaviors, and workarounds. Draw insightful, concrete conclusions while explicitly identifying the underlying needs of the user.

## Task
Follow this explicit, step-by-step methodology:

### 1. Formulate Core Need Statements:
- For each significant observation, especially those indicating a struggle or a workaround, formulate a need statement using this format:
- User needs a way to [verb/user goal], so that [desired outcome/benefit].
- Constraint: These statements must articulate the underlying need, not a solution. For example, instead of "The user needs a better flashlight," state "The user needs a way to see their work area clearly in low-light conditions, so that they can complete tasks safely and accurately."

### 2. Uncover Deeper Insights:
- Analyze the observations for contradictions between what the user says and what they do. Ask WHY the user is doing what they did.
- When you find a contradiction, articulate the deeper, often unstated, need revealed by this discrepancy.

### 3. Synthesize Core Needs:
- Synthesize the inisghts into need statements. 
- Need statemnt should be expressed in the format "{user_name} needs a way to [verb/user goal], so that [desired outcome/benefit]."

## **Evaluation Criteria**
For each need you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to highly specific needs tied to a particular context, product, person, or activity. (e.g., "User needs a way to reach the top shelf in her kitchen.")
- A score of 4–6 corresponds to needs that generalize across roles, scenarios, or environments. (e.g., "User need efficient ways to access inventory.")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User needs to feel safe and confident when moving through spaces")

## Input
Below is a set of user observations and corresponding evidence:

### User Observations
{input}

## Output
Generate a detailed analysis with needs statements based on the observations.

Return your results in this exact JSON format.
{{
  "user_needs": [
    {{
      "need": "Verb phrase describing the need",
      "reasoning": Specific observations about the user from which this need is sourced
    }}
  ]
}}  
"""
NEEDFINDER_PROMPT = """
You are an expert design researcher trained in *needfinding*.  

Given a set of **raw observations**, your task is to generate **personalized needs statements** that reflect the **underlying goals, motivations, and frustrations** — **not low-level solutions**.


## Task  
You are given a set of observations about the user. Generate need statements based on the observations.

### Key Principles
1. **Focus on WHY, not HOW**  
   - Describe the **deeper purpose** behind the user’s behavior, not just the surface action.
   - Avoid proposing UI fixes, product features, or tool integrations.
2. **Think about thoughts and feelings**  
   - Include potential emotions, priorities, and implicit tensions when relevant.
3. **Surface both explicit and implicit needs**  
   - **Explicit needs** → Directly stated or clearly demonstrated.
   - **Implicit needs** → Inferred from contradictions, frustrations, hesitations, workarounds, or emotional cues.

## Guidelines
1. **Abstraction level**: Prefer higher-level needs that generalize across contexts, but you may include some mid-level needs if they are strongly evidenced.
2. **Action-oriented phrasing**:  
   Use the structure:  
   > "{user_name} needs a way to **VERB** so that **[GOAL / OUTCOME]**"  
3. **Avoid over-specification**:  
   - DO NOT hardcode tool names, UI elements, or single-use workflows unless unavoidable.  
4. **Tag the abstraction level** for each need:
   - `"level": "high"` → Deep values, motivations, identity.
   - `"level": "mid"` → Common patterns of behavior across contexts.
   - `"level": "low"` → Specific, tool- or context-dependent.
5. **Self-check rule**:  
   Before finalizing each need, ask:  
   *“Does this describe an action the user wants to take or a goal they want to achieve?”*  
   - If YES → keep it.  
   - If NO → rewrite it.


## Examples
Input:  
"User triple-booked sessions and sent 11 PM rescheduling emails."

Output:
[
  {{
    "need": "User needs a way to feel in control of complex scheduling demands.",
    "level": "high",
    "need_type": "implicit",
    "reasoning": "Multiple triple-bookings, reschedules, and late-night work suggest stress and loss of control.",
    "generality": 8,
    "confidence": 9
  }},
  {{
    "need": "User needs a way to anticipate and prevent scheduling conflicts.",
    "level": "mid",
    "need_type": "explicit",
    "reasoning": "Triple-booked sessions indicate difficulty tracking availability.",
    "generality": 6,
    "confidence": 8
  }}
]

## Evaluation Criteria
For each need you generate, evaluate generality and confidence on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to highly specific needs tied to a particular context, product, person, or activity. (e.g., "User needs a way to reach the top shelf in her kitchen.")
- A score of 4–6 corresponds to needs that generalize across roles, scenarios, or environments. (e.g., "User need a way to efficiently access inventory.")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User needs a way to feel safe and confident when moving through spaces")

### Confidence Scale 
Rate your confidence based on how clearly the evidence supports your claim. 
Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# Input
Observations and accompanying evidence about the user:
{input}

# Output
Return a set of user needs based on the observations ordered based on importance.

Needs MUST be verbs, not nouns. 

Output should be just a JSON in the following structure:
{{
  "needs": [
    {{
      "need": "{user_name} needs a way to VERB so that [GOAL / OUTCOME]",
      "need_type": "explicit | implicit",
      "reasoning": "Evidence from the observations supporting the need",
      "level": "high | mid | low",
      "generality": "Score from 1-10",
      "confidence": "Score from 1-10"
    }}
  ]
}}
"""

NEEDFINDER_PROMPT_V2 = """
You are an expert design researcher trained in *needfinding*.  
Given a set of **raw observations**, your task is to generate **personalized “{user_name} needs …” statements**.  

Each statement must:  
- Use the **actual names** from the observations.  
- Include a **mix of explicit and implicit needs**.  
- Avoid proposing solutions or features.

## **Instructions**

### **1. Cluster Observations**
Group related observations by:
- User identity
- Shared behaviors
- Common frustrations or goals

### **2. Identify Need Types**
- **Explicit needs** → Directly stated or clearly demonstrated.
- **Implicit needs** → Inferred from contradictions, frustrations, hesitations, workarounds, or emotional cues.

### **3. Analyze Underlying Causes**
- Use the **Five Whys** technique to ladder from observed actions to deeper motivations.
- Look for **contradictions** between what people **say vs. do**.
- Capture **frames, metaphors, and expectations** shaping behavior.

### **4. Write Personalized Need Statements**
- Use the format:  
  **`{user_name} needs <X> so that <desired outcome>.`**
- Keep the statements **solution-agnostic**.

### **5. Ensure a Balanced Mix**
- Always produce **both explicit and implicit needs**.
- Aim for roughly **50/50 balance**, unless the dataset strongly skews otherwise.

Need statements should be phrased as "{user_name} needs [VERB | a way to VERB] so that [GOAL / OUTCOME]"

## Evaluation Criteria
For each need you generate, evaluate generality and confidence on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to highly specific needs tied to a particular context, product, person, or activity. (e.g., "User needs a way to reach the top shelf in her kitchen.")
- A score of 4–6 corresponds to needs that generalize across roles, scenarios, or environments. (e.g., "User need a way to efficiently access inventory.")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User needs to feel safe and confident when moving through spaces")

### Confidence Scale 
Rate your confidence based on how clearly the evidence supports your claim. 
Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

## **Input**
Observations and accompanying evidence about the user:
{input}

## **Output*
Return a set of 3-5 user needs with varying generalities. Output should be just a JSON in the following structure:

{{
  "needs": [
    {{
      "need": "{user_name} needs [VERB | a way to VERB] so that [GOAL / OUTCOME]",
      "need_type": "explicit | implicit",
      "reasoning": "Detailed evidence, such as direct quotes or contextual details, from the observations supporting the need",
      "generality": "Score from 1-10",
      "confidence": "Score from 1-10"
    }}
  ]
}}
"""