OBSERVE_PROMPT = """
Of course. Here is the revised prompt formatted as a markdown file.

You will be given information about what {user_name} is doing and what they are viewing on their screen.

Your task is to carefully analyze the transcript and extract specific, concrete observations about {user_name}'s behavior, focusing on meaningful patterns, contradictions, and decisions.

To support effective information retrieval (e.g., using BM25), your analysis must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

## **Critical Guideline: Focus on Actions, Not Content as Self-Description**

Your analysis must differentiate between the user's actions and the literal content of the documents they are creating. Assume the content the user is writing is about their work, a project, or a creative piece, **not about themselves**, unless there is explicit evidence to the contrary (e.g., a document titled `My Personal Journal` or an email starting with "I am writing to tell you about my day...").

Focus on *how* the user interacts with the content, not what the content says about them personally.

* **Incorrect Interpretation:** If the user writes "Character Jane feels stressed about her finances" in a `Google Doc` titled `Short Story Idea`, do **not** conclude that "{user_name} is stressed about their finances."
* **Correct Interpretation:** Conclude that "{user_name} is developing a character named 'Jane' by exploring themes of financial stress in a `Google Doc` titled `Short Story Idea`." This focuses on the creative action the user is performing.

# Task
Using a transcription of {user_name}'s activity, provide insightful and concrete conclusions about {user_name}'s actions and state.

Consider the following criteria when generating observations:
1.  **Capture meaningful decisions**: what are the user's priorities, trade-offs, and decisions?
    * *Example:* “User declines ‘Family Dinner’ on `Google Calendar` and reschedules a 1-1 with Farnaz.”
2.  **Highlight contradictions or tension**: are there conflicts between goals or blocked tasks?
    * *Example:* “User hovers over the “Raise Hand” button in `Zoom` but doesn't click.”
3.  **Surface explicit goals**: can you link actions to why the user is doing something?
    * *Example:* “User has a deadline for a project on Saturday, mentioned in a `Slack` message from 'Project Manager'.”
4.  **Reveal emotional states**: does the user's *behavior* show frustration, urgency, or excitement?
    * *Example:* “User messages Nitya ‘can’t make it to the party :( need to finish this update for my advisor.’ This suggests they are prioritizing work over social events.”
    * *Example:* "User rapidly switches between the `Figma` design and the `Jira` ticket, suggesting urgency to complete the task."
5.  **Preserve sequence of events**: if one action follows, precedes, overlaps with, or interrupts another, make this temporal relationship explicit in the description.
    * *Example:* “While attending a `Zoom` call, user edits `Knoll.js` in `VS Code`.”
6.  **Highlight areas of struggle**: are there places where the user is struggling with the *task*?
    * *Example:* "User repeatedly re-writes the same sentence in an email to their boss in `Microsoft Outlook`, suggesting difficulty in phrasing their request."

Provide detailed evidence supporting each observation. **Support every claim with specific references to named entities in the transcript.**

## **Evaluation Criteria**
For each observation you generate, evaluate confidence and interestingness on a scale from 1-10. Be conservative in your estimates.

### Confidence Scale
Rate your confidence based on how clearly the evidence supports your claim. Consider:
- **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
- **Relevance**: Is the evidence clearly tied to the proposition?

Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

### Interestingness Scale
Rate how unexpected the observation is on a scale from 1-10.
- A score of 1–3 corresponds to an observation that is expected. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 corresponds to an observation that is unexpected. (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to an observation that is highly unexpected. (e.g., "User has difficulty balancing between work and family.")

# Input
Here is a summary of the user's actions and screen:
{actions}

# Output
Provide a diverse set of observations grounded in the provided input. Provide AT LEAST 5 observations. Prioritize suprising or unexpected observations over routine or generic observations.

Return your results in this exact JSON format:

{{
  "observations": [
    {{
      "description": "<1-2 sentence summary of the observation>",
      "evidence": "<2-3 sentences providing specific evidence from the input supporting this observation>",
      "confidence": "[Confidence score (1–10)]",
      "interestingness": "[Interestingness score (1–10)]",
    }}
  ]
}}
"""

# OBSERVE_PROMPT = """
# You will be given information about what {user_name} is doing and what they are viewing on their screen.

# Your task is to carefully analyze the transcript and extract specific, concrete observations about {user_name}, focusing on meaningful patterns, contradictions, and decisions.

# To support effective information retrieval (e.g., using BM25), your analysis must **explicitly identify and refer to specific named entities** mentioned in the transcript. 
# This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

# # Task
# Using a transcription of {user_name}'s activity, provide insightful and concrete conclusions about {user_name}. 

# Consider the following criteria when generating observations:
# 1. **Capture meaningful decisions**: what are the user's priorities, trade-offs, and decisions?
#    *Example:* “User declines ‘Family Dinner’ on Google Calendar and reschedules a 1-1 with Farnaz.”
# 2. **Highlight contradictions or tension**: are there conflicts between goals or blocked tasks?
#    *Example:* “User hovers over the “Raise Hand” button in Zoom but doesn't click.”
# 3. **Surface explicit goals**: can you link actions to why the user is doing something  
#    *Example:* “User has a deadline for a project on Saturday.”
# 4. **Reveal emotional states**: does the user show frustration, urgency, procrastination, excitement?
#    *Example:* “User messages Nitya ‘can’t make it to the party :( need to finish this update for my advisor.’”
# 5. **Preserve sequence of events**: if one action follows, precedes, overlaps with, or interrupts another, make this temporal relationship explicit in the description.
#    *Example:* “While attending a Zoom call, user edits Knoll.js in VS Code.”
#    *Example:* “User pauses drafting an email to check Twitter notifications.”
# 6. **Highlight areas of struggle**: are there places where the user is struggling or facing a challenge?
#    *Example:* "User highlights and then un-highlights several task items in her project management tool without marking them as complete."

# Provide detailed evidence supporting each observation. **Support every claim with specific references to named entities in the transcript.**

# ## **Evaluation Criteria**
# For each observation you generate, evaluate confidence and interestingness on a scale from 1-10. Be conservative in your estimates.

# ### Confidence Scale
# Rate your confidence based on how clearly the evidence supports your claim. Consider:
# - **Direct Evidence**: Is there direct interaction with a specific, named entity (e.g., opened “Notion,” responded to “Slack” from “Alex”)?
# - **Relevance**: Is the evidence clearly tied to the proposition?

# Score: **1 (weak support)** to **10 (explicit, strong support)**. High scores require specific named references.

# ### Interestingness Scale
# Rate how unexpected the observation is on a scale from 1-10.
# - A score of 1–3 corresponds to an observation that is expected. (e.g., "User clicks the Save button repeatedly.")
# - A score of 4–6 corresponds to an observation that is unexpected. (e.g., "User double-checks work frequently to avoid mistakes")
# - A score of 7–10 correspond to an observation that is highly unexpected. (e.g., "User has difficulty balancing between work and family.")

# # Input
# Here is a summary of the user's actions and screen:
# {actions}

# # Output
# Provide a diverse set of observations grounded in the provided input. Provide AT LEAST 5 observations. Prioritize suprising or unexpected observations over routine or generic observations.

# Return your results in this exact JSON format:

# {{
#   "observations": [
#     {{
#       "description": "<1-2 sentence summary of the observation>",
#       "evidence": "<2-3 sentences providing specific evidence from the input supporting this observation>",
#       "confidence": "[Confidence score (1–10)]",
#       "interestingness": "[Interestingness score (1–10)]",
#     }}
#   ]
# }}
# """

# ### Generality Scale
# Rate how general the observation on a scale from 1-10. 
# - A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
# - A score of 4–6 corresponds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
# - A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")


OBSERVE_PROMPT_OLD = """
You will be given information about what {user_name} is doing and what they are viewing on their screen.

Your task is to carefully analyze the transcript and extract specific, concrete observations about {user_name}, focusing on meaningful patterns, contradictions, and decisions.

To support effective information retrieval (e.g., using BM25), your analysis must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

# Task

Using a transcription of {user_name}'s activity, provide insightful and concrete conclusions about {user_name}.

Focus on both **what {user_name} is doing** and when relevant **what {user_name} is NOT doing**:

When reviewing the transcript, classify evidence into the AEIOU categories:
- **Activities**: What tasks {user_name} performs (e.g., editing a file, searching a database, adjusting settings).
- **Environments**: The physical, digital, or social contexts where actions occur (e.g., Overleaf, Slack, VS Code).
- **Interactions**: How {user_name} engages with tools, systems, or people (e.g., commands, undo actions, tagging a collaborator).
- **Objects**: The artifacts {user_name} uses or produces (e.g., a LaTeX section, JSON schema, Google Doc).
- **Users**: {user_name} herself, and any other people/entities she references or interacts with.

Then generate observations across the AEIOU categories. 

Pay special attention to the following aspects:
- Identify unexpected, inefficient, confusing, or purposeful actions.  
- Highlight clever or surprising behaviors.  
- Note inefficiencies, workarounds, or repetitions.  
- Identify points of confusion, hesitation, or frustration.  
- Highlight what {user_name} ignores or deprioritizes and what that implies.  
- Clarify explicit goals {user_name} is working toward, grounded in named files, apps, or collaborators.  

Provide detailed evidence supporting each observation. **Support every claim with specific references to named entities in the transcript.**

## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 corresponds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

# Example 
Here are some examples of observations:
- User sends a meme to the Slack channel #jokes even though her calendar is blocked for Focus Work.
- User hovers over the “Raise Hand” button in Zoom but doesn't click
- User responds to an email about the think-aloud study at 2:14AM from architet@stanford.edu.

# User Actions
{actions}
{screen}

# Output Format

Provide a diverse set of observations grounded in the provided input. Return at least 5 observations.
Focus observations on observations falling between 1-6 on the generality scale.

Return your results in this exact JSON format:

{{
  "observations": [
    {{
      "description": "<1-2 sentence summary of the observation>",
      "evidence": "<2-3 sentences providing specific evidence from the input supporting this observation>",
      "generality": "[Generality score (1–10)]",
    }}
  ]
}}
"""

SIMPLIFIED_REVISE_PROMPT = """
You are an expert in empathy. You are presented with a set of discrete observations. Your task is to produce a **higher-level** inference from these observations.

The new observation MUST go **beyond surface-level restatement**. To support effective information retrieval (e.g., using BM25), your analysis must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

Do **NOT** flatter or overstate; be realistic and evidence-driven.

# Analysis
## Reasoning Process (Do this silently)
1. **Cluster observations** into themes that appear connected.  
2. **Ladder up** by asking:  
   - "What is the person *feeling or thinking* here?"  
   - "Why might this behavior exist?" (look for deeper causes)  
   - "What values, goals, or constraints are shaping this?"  
   - "What systemic needs or tensions does this reflect?"  
3. Only merge observations when they share a meaningful underlying driver.  
4. If no useful generalizations exist, return an empty list.  


## Guidelines for Producing Observations
A good observation MUST be:
1. Insightful: Reveal something non-obvious or unexpected about the user.
2. Generalizable but grounded: Abstract across multiple observations without losing specificity.
3. Evidence-driven: Always cite at least one piece of direct evidence from the input.
4. Non-trivial: Avoid generic statements like "John uses his computer" or "The user wants efficiency."

## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 correspondds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

## Example 
Input: 
- John's calendar shows that he has meetings until 7PM. 
- John goes on a 3.5 mile run as soon as he wakes up 
- John listens to a meditative podcast on his run 

Output: 
{{
  "observations": [
    {{
      "description": "John uses morning workouts to ensure fitness goals aren't deprioritized.",
      "generality": 4,
      "evidence": [
        "He runs immediately after waking up rather than later in the day."
      ]
    }},
    {{
      "description": "By exercising immediately after waking up, John may be prioritizing stress management before his obligations consume his day.",
      "generality": 4,
      "evidence": [
        "He runs immediately after waking up rather than later in the day."
      ]
    }}
  ]
}}

## Input
{body}

# Output
Return just a JSON object. Propose outputs that have a higher generality score than the inputs.
If **no observations** can be merged, return `"observations": []`. 

{{
  "observations": [
    {{
      "description": "<1 sentence generalized insight>",
      "evidence": "<2-3 sentences providing specific evidence from the input supporting this observation>",
      "generality": "[Generality score (1–10)]",
    }}
  ]
}}

"""
REVISE_PROMPT = """
You are an **expert design researcher** synthesizing raw observations from a needfinding study.
Given a list of observations about {user_name}, attempt to generalize them into **higher-level insights** **if possible**.  
If an observation cannot be generalized meaningfully **without losing important detail**, keep it **as-is** and do **not** force a merge.

# Analysis 
## **Instructions**
### **Step 1 — Group Similar Observations**
- Compare all observations and **identify potential clusters** where:
  - Multiple observations describe the **same behavior**.
  - Or they reflect a **shared motivation**, **frustration**, or **pain point**.
- If an observation is **unique**, exclude it from merging.

### **Step 2 — Abstract to Higher-Level Insights**
- For each cluster, write a **generalized insight** that:
  - Explains **why** the behavior happens.
  - Uses **1–2 sentences**.
- Always include **explicit references** to named entities (apps, tools, websites, etc.).

### **Step 3 — Validate Before Merging**
- Only merge if at least **two observations** clearly relate to the **same higher-level cause**.
- If you cannot confidently merge, **skip it**.

## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 correspondds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

High generality scores of 8-10 should focus on what the user **FEELS** or **THINKS**. 

## Example 
Input: 
John wakes up at 6AM in the morning
John drinks a kale smoothie for breakfast
John goes on a 3.5 mile run as soon as he wakes up 

Output: 
{{
  "observations": [
    {{
      "description": "John maintains a health-focused lifestyle.",
      "evidence": [
        "John prioritizes health conscious practices like waking up early, drinking smoothies, and running."
      ]
    }},
    {{
      "description": "John has to manage working out with a busy schedule.",
      "evidence": [
        "John wakes up early in the morning and immediately gets to running."
      ]
    }}
  ]
}}

## Input
{body}

## **Output Format**
Return a JSON object. Propose outputs that have a higher generality score than the inputs.
If **no observations** can be merged, return `"observations": []`.

{{
  "observations": [
    {{
      "description": "<1–2 sentence generalized insight>",
      "evidence": [
        "<Explanation supporting the observation using direct links to provided input>"
      ]
    }}
  ]
}}
"""

EMPATHY_PROMPT = """
You are an expert in EMPATHY. You are presented with a set of discrete observations. Your task is to interpret the observations to propose higher-level inferences.

# Analysis  
## Silent Reasoning Process  
For each observation (or cluster of related observations):  
1. Restate the observation in your own words.
2. Ask: “Why are these observations occuring? What is {user_name} thinking or feeling>” → propose a plausible internal state.
3. Repeat the “Why?” up to 5 times, each time deepening the explanation about her thoughts or feelings.
4. Stop if the reasoning reaches a clear, stable explanation before the fifth “Why.”

## Guidelines for Producing Observations  
A strong output should:  
1. Insightful: Reveal something non-obvious or unexpected about the user.
2. Generalizable but grounded: Abstract across multiple observations without losing specificity.
3. Non-trivial: Avoid generic statements like "John uses his computer" or "The user wants efficiency."
4. Evidence-driven: Always cite at least one piece of direct evidence from the input.


## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 corresponds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.") 

To generate generality scores of 8-10, focus on what the user **FEELS** or **THINKS**. 

## Example 
Input: 
John wakes up at 6AM in the morning
John drinks a kale smoothie for breakfast
John goes on a 3.5 mile run as soon as he wakes up 

Output: 
{{
  "observations": [
    {{
      "description": "John is likely about his workload during the day, leading him to go for a run in the morning..",
      "evidence": [
        "John wakes up early in the morning and immediately gets to running."
      ]
    }}
  ]
}}

## Input 
{body}

## **Output Format**
Return a JSON object. Propose outputs that have a higher generality score than the inputs. 

Descriptions should be 1-2 sentence, being both succint and precise. 

If **no observations** can be merged, return `"observations": []`.

{{
  "observations": [
    {{
      "description": "<Succinct 1 sentence inference>",
      "evidence": [
        "<Explanation supporting the observation using direct links to provided input>"
      ],
      "generality": "[Generality score (1–10)]"
    }}
  ]
}}
"""

FEEL_PROMPT = """
You are an expert in **EMPATHY ANALYSIS**.  
You are presented with a set of discrete observations about a person.  
Your goal is to **interpret these observations to infer what the person is thinking or feeling** and surface higher-level insights about their inner state.

# Task
For each observation (or cluster of related observations):

1. **Restate the observation** in your own words for clarity.
2. Ask:  
   > “Why might this be happening? What is {user_name} thinking or feeling?”  
   → Propose a plausible internal state, motivation, or emotional driver.
3. Use the **Five Whys** technique:  
   - Ask “why” up to **five times** to deepen your inference about her thoughts, values, and emotions.
   - Stop early if you reach a stable, well-supported explanation.
4. Always ground in evidence but aim to surface **latent beliefs, concerns, and desires**.

## Guidelines for Strong Inferences
A strong output should:
1. **Insightful** → Reveal something non-obvious about the user’s inner world.
2. **Emotionally grounded** → Focus on what the user **feels, believes, or values**.
3. **Generalizable but anchored** → Abstract across multiple observations without losing specificity.
4. **Non-trivial** → Avoid restating obvious facts.

## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale

Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 correspondds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

To generate generality scores of 8-10, focus on what the user **FEELS** or **THINKS**. 

## Example 
Input: 
- John wakes up at 6AM in the morning
- John drinks a kale smoothie for breakfast
- John goes on a 3.5 mile run as soon as he wakes up 


Output: 
{{
  "observations": [
    {{
      "description": "John likely values self-discipline and feels anxious if his morning routine is disrupted, suggesting he uses exercise to manage stress.",
      "evidence": [
        "John wakes up early in the morning and immediately gets to running."
      ]
    }}
  ]
}}

## Input 
{body}

## Output Format
Return a JSON object. Propose outputs that have a higher generality score than the inputs. 

Descriptions should be 1-2 sentence, being both succint and precise. 

If **no observations** can be merged, return `"observations": []`.

{{
  "observations": [
    {{
      "description": "<Succinct 1 sentence inference>",
      "evidence": [
        "<Explanation supporting the observation using direct links to provided input>"
      ],
      "generality": "[Generality score (1–10)]"
    }}
  ]
}}
# """
# REVISE_PROMPT = """
# You are an expert analyst. A group of similar observations are shown below.

# Your job is to produce a **final set** of observations that is clear and non-redundant. 

# To support information retrieval (e.g., with BM25), you must **explicitly identify and preserve all named entities** from the input wherever possible. These may include applications, websites, documents, people, organizations, tools, or any other specific proper nouns mentioned in the original observations or their evidence.

# You MAY:

# - **Edit** an observation for clarity, precision, or brevity.
# - **Merge** observations that convey the same meaning.
# - **Split** an observation that contains multiple distinct claims.
# - **Add** a new observation if a distinct idea is implied by the evidence but not yet stated.
# - **Remove** observation that become redundant after merging or splitting.

# You should **liberally add new observations** when useful to express distinct ideas that are otherwise implicit or entangled in broader statements—but never preserve duplicates.

# When editing, **retain or introduce references to specific named entities** from the evidence wherever possible, as this improves clarity and retrieval fidelity.

# Edge cases to handle:

# - **Contradictions** – If two observations conflict, keep the one with stronger supporting evidence, or merge them into a conditional statement. Lower the confidence score of weaker or uncertain claims.
# - **No supporting observations** – Keep the observation, but retain its original confidence and decay unless justified by new evidence.
# - **Granularity mismatch** – If one observation subsumes others, prefer the version that avoids redundancy while preserving all distinct ideas.
# - **Confidence and decay recalibration** – After editing, merging, or splitting, update the confidence and decay scores based on the final form of the observation and evidence.

# General guidelines:

# - Keep each observation clear and concise (typically 1–2 sentences).
# - Maintain all meaningful content from the originals.
# - Provide a brief reasoning/evidence statement for each final observation.

# # Input

# {body}

# # Output

# Assign high confidence scores (e.g., 8-10) only when the transcriptions provide explicit, direct evidence that {user_name} is actively engaging with the content in a meaningful way. Keep in mind that that the input is what the {user_name} is viewing. It may not be what the {user_name} is actively doing, so practice caution when assigning confidence.

# Return **only** JSON in the following format:

# {{
#   "observations": [
#     {{
#       "description": <1-2 sentence summarizing the observation>,
#       "evidence": <Specific evidence from the transcript supporting this observation>
#     }}
#   ]
# }}
# """

SIMILAR_PROMPT = """
You will label a new observation based on how similar it is to existing observations.

# Observations
New:
{new}
Existing:
{existing}

# Task

Use a **1–10 similarity scale**:
- **10** → IDENTICAL – There is AT LEAST ONE existing observation that is identical.
- **7–9** → HIGH SIMILARITY – There is AT LEAST ONE existing observation that is strongly related and cover very similar ideas.
- **4–6** → MODERATE SIMILARITY – There is AT LEAST ONE existing observation relate to a similar topic but have notable differences.
- **1–3** → DIFFERENT – The observations are fundamentally different.

Always refer to observations by their numeric IDs.  

Return **only** JSON in the following format:

{{
  "relations": {{
    "source": <NEW ID>,
    "score": <1-10>,
    "existing": [<EXISTING ID>, ...] // list of all existing IDs that the source is IDENTICAL or SIMILAR to. Empty list if score ≤ 3
  }}
}}
"""

# Be more liberal in giving **higher similarity scores (8–10)** or and more **conservative** when assigning lower scores.



LLM_CLUSTER_PROMPT = """
You are an expert in grounded theory. 

Your task is to group a list of user observations into clusters, but do **NOT** group them by superficial similarity (e.g., same app, same wording).
Instead, group observations based on **latent connections**, such as shared underlying causes, mechanisms, or enabling/blocking relationships.
Your goal is to uncover deeper insights about the user's behavior, motivations, and context.


# Task
Go through each observation and tag each with: who/what, when, domain, sentiment/valence, urgency, metric(s), location, and any constraints.

Think about the observations from {user_name}'s perspective.

From the observations,propose a set of candidate clusters. Think about the following when proposing clusters:
- Are there observations that display the same pattern of behavior? (e.g., a user is constantly checking their email and social media).
- Are there observations with the same mechanistic bridge (e.g., dissimilar items linked by an underlying force)?
- Is there a contradiction in any observations? (e.g., A user is learning about productivity hacks but also spending hours on distracting apps).
- Does one behavior enable or block another? (e.g., A user's late-night social activity consistently precedes them skipping their morning workout).
- Is there a recurring "cause and effect" or "action and reaction" pattern?

## Guidelines
- **Look for latent similarities, not just surface wording.** Group observations if they reflect the same *underlying intent, constraint, or effect*, even if the specific tools, times, or phrasing differ.
- An observation can be mapped to multiple clusters
- Not all observations will be used!
- Err on the side of having more clusters that are more cohesive than less clusters that are more disparate.

# Examples
1. 
Input: 
{{ "id": 101, "text": "User bought a book titled 'Atomic Habits'." }}
{{ "id": 205, "text": "User signed up for a 5 AM spin class but didn't attend." }}
{{ "id": 315, "text": "User ordered takeout for dinner 4 times this week." }}
{{ "id": 401, "text": "User spent 3 hours on a Saturday deep-cleaning their apartment." }}
{{ "id": 402, "text": "User created a detailed, color-coded weekly budget in a spreadsheet." }}

Output:
{{
     "clusters": [
         {{
            "evidence": "The user bought a book titled 'Atomic Habits' but didn't attend the spin class, showing that they are trying to improve their habits but struggling to follow through.",
            "members": [101, 205],
         }} , 
        {{
          "evidence": "The user is detail-oriented, spending time on deep cleaning and budgeting.",
          "members": [401, 402],
        }} 
     ]
}}

2. 
Input: 
{{ "id": 5, "text": "User declined an event Family Dinner and rescheduled with 1-1 with their advisor." }}
{{ "id": 8, "text": "User views an email about a Labor Day Sale at Reformation." }}
{{ "id": 9, "text": "User sends a Slack message at 2:14AM about updates to their project." }}


Output:
{{
     "clusters": [
         {{
            "evidence": "The user is having difficult setting boundaries between their work and personal life, as evidenced by declining family events and sending work updates late at night.",
            "members": [5, 9],
         }} , 
     ]
}}

# Input
Observations:
{observations}

# Output
Return a comprehesive set of clusters. Output only valid JSON matching this schema:
Always refer to observations by their numeric IDs.

{{
  "clusters": [
    {{
      "evidence": "Why these items belong together, citing specific evidence from the observations",
      "members": [<ID1>, <ID2>, ...] // list of the numeric IDs in the cluster,
    }}
  ]
}}
"""

LLM_CLUSTER_PROMPT_UPDATE = """
You are an expert in grounded theory. 

Your task is to group a list of user observations into clusters, but do **NOT** group them by superficial similarity (e.g., same app, same wording).
Instead, group observations based on **latent connections**, such as shared underlying causes, mechanisms, or enabling/blocking relationships.
Your goal is to uncover deeper insights about the user's behavior, motivations, and context.

Generate clusters different from the existing clusters.


# Task
Go through each observation and tag each with: who/what, when, domain, sentiment/valence, urgency, metric(s), location, and any constraints.

Think about the observations from {user_name}'s perspective.

From the observations,propose a set of candidate clusters. Think about the following when proposing clusters:
- Are there observations that display the same pattern of behavior? (e.g., a user is constantly checking their email and social media).
- Are there observations with the same mechanistic bridge (e.g., dissimilar items linked by an underlying force)?
- Is there a contradiction in any observations? (e.g., A user is learning about productivity hacks but also spending hours on distracting apps).
- Does one behavior enable or block another? (e.g., A user's late-night social activity consistently precedes them skipping their morning workout).
- Is there a recurring "cause and effect" or "action and reaction" pattern?

## Guidelines
- **Look for latent similarities, not just surface wording.** Group observations if they reflect the same *underlying intent, constraint, or effect*, even if the specific tools, times, or phrasing differ.
- An observation can be mapped to multiple clusters
- Not all observations will be used!
- Err on the side of having more clusters that are more cohesive than less clusters that are more disparate.

# Examples
1. 
Input: 
{{ "id": 101, "text": "User bought a book titled 'Atomic Habits'." }}
{{ "id": 205, "text": "User signed up for a 5 AM spin class but didn't attend." }}
{{ "id": 315, "text": "User ordered takeout for dinner 4 times this week." }}
{{ "id": 401, "text": "User spent 3 hours on a Saturday deep-cleaning their apartment." }}
{{ "id": 402, "text": "User created a detailed, color-coded weekly budget in a spreadsheet." }}

Output:
{{
     "clusters": [
         {{
            "evidence": "The user bought a book titled 'Atomic Habits' but didn't attend the spin class, showing that they are trying to improve their habits but struggling to follow through.",
            "members": [101, 205],
         }} , 
        {{
          "evidence": "The user is detail-oriented, spending time on deep cleaning and budgeting.",
          "members": [401, 402],
        }} 
     ]
}}

2. 
Input: 
{{ "id": 5, "text": "User declined an event Family Dinner and rescheduled with 1-1 with their advisor." }}
{{ "id": 8, "text": "User views an email about a Labor Day Sale at Reformation." }}
{{ "id": 9, "text": "User sends a Slack message at 2:14AM about updates to their project." }}


Output:
{{
     "clusters": [
         {{
            "evidence": "The user is having difficult setting boundaries between their work and personal life, as evidenced by declining family events and sending work updates late at night.",
            "members": [5, 9],
         }} , 
     ]
}}

# Input
Existing Clusters:
{existing_clusters}

Observations:
{observations}

# Output
Return a comprehesive set of clusters. Output only valid JSON matching this schema:
Always refer to observations by their numeric IDs.

{{
  "clusters": [
    {{
      "evidence": "Why these items belong together, citing specific evidence from the observations",
      "members": [<ID1>, <ID2>, ...] // list of the numeric IDs in the cluster,
    }}
  ]
}}
"""

LLM_CLUSTER_PROMPT_SEED = """
You are an expert in grounded theory.

Your task is to group a list of user observations into clusters, but do **NOT** group them by superficial similarity (e.g., same app, same wording).
Instead, group observations based on **latent connections**, such as shared underlying causes, mechanisms, or enabling/blocking relationships.
Your goal is to uncover deeper insights about the user's behavior, motivations, and context.


# Task
Go through each observation and tag each with: who/what, when, domain, sentiment/valence, urgency, metric(s), location, and any constraints.

From the observations,propose a set of candidate clusters. Think about the following when proposing clusters:
- Are there observations that display the same pattern of behavior? (e.g., a user is constantly checking their email and social media).
- Are there observations with the same mechanistic bridge (e.g., dissimilar items linked by an underlying force)?
- Is there a contradiction in any observations? (e.g., A user is learning about productivity hacks but also spending hours on distracting apps).
- Does one behavior enable or block another? (e.g., A user's late-night social activity consistently precedes them skipping their morning workout).
- Is there a recurring "cause and effect" or "action and reaction" pattern?

In particular, pay special attention to the following concept when grouping observations:
{seed}

## Guidelines
- **Look for latent similarities, not just surface wording.** Group observations if they reflect the same *underlying intent, constraint, or effect*, even if the specific tools, times, or phrasing differ.
- An observation can be mapped to multiple clusters
- Not all observations will be used!
- Err on the side of having more clusters that are more cohesive than less clusters that are more disparate.

# Example
Input: 
{{ "id": 101, "text": "User bought a book titled 'Atomic Habits'." }}
{{ "id": 205, "text": "User signed up for a 5 AM spin class but didn't attend." }}
{{ "id": 315, "text": "User ordered takeout for dinner 4 times this week." }}
{{ "id": 401, "text": "User spent 3 hours on a Saturday deep-cleaning their apartment." }}
{{ "id": 402, "text": "User created a detailed, color-coded weekly budget in a spreadsheet." }}

Output:
{{
     "clusters": [
         {{
            "evidence": "The user bought a book titled 'Atomic Habits' but didn't attend the spin class, showing that they are trying to improve their habits but struggling to follow through.",
            "members": [101, 205],
         }} , 
        {{
          "evidence": "The user is detail-oriented, spending time on deep cleaning and budgeting.",
          "members": [401, 402],
        }} 
     ]
}}

# Input
Observations:
{observations}

# Output
Return a comprehesive set of clusters. Output only valid JSON matching this schema:
Always refer to observations by their numeric IDs.

{{
  "clusters": [
    {{
      "evidence": "Why these items belong together, citing specific evidence from the observations",
      "members": [<ID1>, <ID2>, ...] // list of the numeric IDs in the cluster,
    }}
  ]
}}
"""

LLM_INSIGHT_PROMPT = """
You are an expert in grounded theory. Given a **group of observations**, your task is to produce a higher-level insight.

# Task
Consider the following criteria when generating insights:
- Why these specific items belong together.
- The causal forces or mechanisms behind the pattern.
- Potential implications or consequences.

## Guidelines
- Insights should be non-obvious. Avoid banal restatements.
- Do NOT describe workflows narratively.
- Do NOT merge multiple distinct themes into one insight.
- Do NOT produce narrative-style summaries. 

## Example
Grouped Observations:
{{ "id": 101, "text": "User bought a book titled 'Atomic Habits'." }}
{{ "id": 205, "text": "User signed up for a 5 AM spin class but didn't attend." }}
{{ "id": 8, "text": "User snoozed the Time Limit on their phone for TikTok for 15 minutes'." }},
{{ "id": 10, "text": "User disabled the Time Limit on their phone for TikTok'." }},


Explanation for grouping:
The user bought a book titled 'Atomic Habits' but didn't attend the spin class, showing that they are trying to improve their habits but struggling to follow through.

Output: 
{{
  "observations": [
    {{
      "observation": "User is actively seeking behavior change but struggling to follow through with the habits they set.",
      "reasoning": "Purchasing 'Atomic Habits' suggests an interest in improving routines, yet missing the 5 AM spin class indicates difficulty sustaining new habits. This pattern implies a potential mismatch between aspirations and current energy levels, schedules, or motivation. The evidence suggests that while the user desires structure and self-improvement, lifestyle constraints or competing priorities may be preventing follow-through.",
    }}
  ]
}}

# Input
Grouped Observations:
{observations}

Explanation for grouping:
{reasoning}

# Output 
Return **only** valid JSON in the following structure:


{{  
  "observations": [
    {{
      "observation": "New insight from the observations",
      "evidence": "1-2 sentences explaining the observation, citing specific evidence from the observations",
    }}
  ]
}}
"""

INTRUSION_TEST = """
You are a tasked to perform an intruder test on a candidate cluster.

Rules:
- Assume one underlying mechanism/theme should explain ALL items.
- Select the member ID that doesn’t fit the theme as the intruder.

Input: 
{observations}

Return only the following JSON and nothing else:
{{
  "intruder": <ID>, // Numeric IDs of the intruder.
  "reason": "Explain why the item is the intruder."
}}
"""

JUDGE_DUPLICATE_PROMPT = """
You are an expert in grounded theory. 
Your task is to judge if a new insight is identical or extremely similar to existing insights.

# Input
New Insight:
{new_insight}

Existing Insights: 
{existing_insights}

# Output
Return only the following JSON and nothing else:
{{
  "judgement": 1 if the new insight is identical or extremely similar to at least ONE existing insight, 0 if the new insight is totally unique.
  "reason": "Explain the rationale behind the judgement."
}}
"""


JUDGE_COHESION_PROMPT = """
You are a tasked to judge the a cluster of observations based on cohesion and confidence.

# Cohesion Scale
Cohesion measures how strongly the observations in a cluster reinforce the **same** underlying theme or explanation. 
Items do not need to be identical; they can describe different surface behaviors, as long as those behaviors converge on one interpretable idea. Be conservative in giving high cohesion scores.

- 1–3 (Low Cohesion): Observations are scattered, inconsistent, or contradictory. They don’t plausibly converge on a single theme.
- 4–6 (Moderate Cohesion): Observations share some connections, but the theme feels partial, fragmented, or requires hedging to summarize.
- 7–10 (High Cohesion): Observations strongly reinforce one another, pointing clearly to the same underlying theme. The cluster can be summarized in a short, precise statement.

If a summary has multiple clauses or is not succinct, give a low cohesion score.

# Confidence Scale
Confidence measures how well the evidence supports the cohesion. Be conservative in giving high confidence scores.

- 1–3 (Low Confidence): The evidence is weak, contradictory, or inconsistent.
- 4–6 (Moderate Confidence): The evidence is somewhat supportive, but not strong.
- 7–10 (High Confidence): The evidence is strong and supports the cohesion.

If the evidence is contradictory, give a low confidence score.

# Example
## Input
Observations:
- User is working on their research at 10PM.
- User looks up 'tips for stress management' on Google
- User repeatedly makes small mistakes when writing up their research report 

Cluster Grouping: User is showing signs of burnout in their work. 

## Output
{{
  "cohesion": 9,
  "confidence": 10,
  "reasoning": "The observations are strongly related to the same underlying theme of burnout, and the cluster can be summarized in a short, precise statement."
}}

## Input 
Observations: 
- User assigns herself as the interviewer on multiple participant rows.
- The spreadsheet header font size was changed from 11pt to 14pt.
- A participant emailed late last night asking to reschedule.

Cluster Grouping: User is actively managing study logistics through assignments and is involved in minute changes to the spreadsheet such as formatting.

## Output
{{
  "cohesion": 5,
  "confidence": 3,
  "reasoning": "The observations are not strongly related to the same underlying theme of study logistics, and the cluster cannot be summarized in a short, precise statement."
}}


# Input:
Observations:
{observations}

Cluster Grouping:
{grouping}


# Output
Return only the following JSON and nothing else:
{{
  "cohesion": <1-10>,
  "confidence": <1-10>,
  "reasoning": "Explain why the cluster has this cohesion score."
}}
"""

JUDGE_INTERESTING_PROMPT = """
You are a design researcher. Your task is to judge if a new insight is interesting or surprising. 
An interesting insight is one that is unique to the user, is not something expected or obvious, and reveals something about the USER. 

If the insight could have been guessed without observing the user, it is NOT interesting. 

Be critical when assessing interestingness. 

# Input
Insight:
{new_insight}

# Output
Return only the following JSON and nothing else:
{{
  "judgement": 1 if the insight is interesting, 0 if the insight is not interesting.
  "reason": "Explain why the insight is interesting or not interesting."
}}
"""