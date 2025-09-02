OBSERVE_PROMPT = """
You will be given a **transcription of Dora's actions** during an interaction with a system.

Your task is to carefully analyze the transcript and extract **specific, concrete observations** about the user, Dora, as well as their actions, interactions, and environment. 

To support effective information retrieval (e.g., using BM25), your analysis must **explicitly identify and refer to specific named entities** mentioned in the transcript. This includes applications, websites, documents, people, organizations, tools, and any other proper nouns. Avoid general summaries—**use exact names** wherever possible, even if only briefly referenced.

# Task

Using a transcription of Dora's activity, provide insightful and concrete conclusions about Dora.

Focus on both **what Dora is doing** and **what Dora is NOT doing**:

When reviewing the transcript, classify evidence into the AEIOU categories:

- **Activities**: What tasks Dora performs (e.g., editing a file, searching a database, adjusting settings).
- **Environments**: The physical, digital, or social contexts where actions occur (e.g., Overleaf, Slack, VS Code).
- **Interactions**: How Dora engages with tools, systems, or people (e.g., commands, undo actions, tagging a collaborator).
- **Objects**: The artifacts Dora uses or produces (e.g., a LaTeX section, JSON schema, Google Doc).
- **Users**: Dora herself, and any other people/entities she references or interacts with.

Then generate observations across the AEIOU categories. 

Pay special attention to the following quesrtions:
### A. Positive Observations (what Dora does)
- Identify unexpected, inefficient, confusing, or purposeful actions.  
- Highlight clever or surprising behaviors.  
- Note inefficiencies, workarounds, or repetitions.  
- Identify points of confusion, hesitation, or frustration.  
- Highlight what Dora ignores or deprioritizes and what that implies.  
- Clarify explicit goals Dora is working toward, grounded in named files, apps, or collaborators.  

### B. Negative Observations (what Dora does not do)
- Identify absences or missed opportunities.  
- Actions Dora could have taken but avoided (e.g., shortcuts, unused features).  
- Expected checks or confirmations that Dora skips.  

Provide detailed evidence supporting each observation. **Support every claim with specific references to named entities in the transcript.**

## **Evaluation Criteria**
For each observation you generate, evaluate its generality on a scale from 1-10. 

### Generality Scale
Rate how general the observation on a scale from 1-10. 
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 correspondds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

# User Actions
{body}

# Output Format

Provide a diverse set of observations grounded in the provided input. Return at least 5 observations.
Focus observations on observations falling between 1-3 on the generality scale.

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
Given a list of observations about Dora, attempt to generalize them into **higher-level insights** **if possible**.  
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
2. Ask: “Why are these observations occuring? What is Dora thinking or feeling>” → propose a plausible internal state.
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
   > “Why might this be happening? What is Dora thinking or feeling?”  
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

# Assign high confidence scores (e.g., 8-10) only when the transcriptions provide explicit, direct evidence that Dora is actively engaging with the content in a meaningful way. Keep in mind that that the input is what the Dora is viewing. It may not be what the Dora is actively doing, so practice caution when assigning confidence.

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
You are an expert analyst. 

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

## Guidelines
- **Look for latent similarities, not just surface wording.** Group observations if they reflect the same *underlying intent, constraint, or effect*, even if the specific tools, times, or phrasing differ.
- An observation can be mapped to multiple clusters
- Not all observations will be used!

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

LLM_CLUSTER_PROMPT_SEED = """
You are an expert analyst. Your job is to group a list of observations into higher-level insights. 


# Task

From the observations,propose a set of candidate clusters. Think about the following when proposing clusters:
- Are there observations with the same mechanistic bridge (e.g., dissimilar items linked by an underlying force)?
- Is there a contradiction in any observations? (e.g., A user is learning about productivity hacks but also spending hours on distracting apps).
- Does one behavior enable or block another? (e.g., A user's late-night social activity consistently precedes them skipping their morning workout).
- Is there a recurring "cause and effect" or "action and reaction" pattern?

Each cluster should be a single, unified theme. It should contain at least 3 observations. 

It is better to have more, well-defined clusters than fewer, less well-defined clusters.

Pay special attention to the following concepts when grouping observations:
{seed}

An observation can be mapped to multiple clusters. Not all observations will be used!

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
                "evidence": "The user bought a book titled 'Atomic Habits' but didn't attend the spin class. They also ordered takeout for dinner 4 times this week. They spent 3 hours on a Saturday deep-cleaning their apartment. They created a detailed, color-coded weekly budget in a spreadsheet.",
                "members": [101, 205, 315],
         }}   
     ]
}}

# Input
Observations:
{observations}

# Output
Return only valid JSON matching this schema:
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
You are an expert synthesis analyst. Given a **cluster of low-level observations** and the reason for grouping them together, your task is to produce a higher-level insight from the observations about the user.

# Task
Consider the following criteria when generating insights:
- Why these specific items belong together.
- The causal forces or mechanisms behind the pattern.
- Potential implications or consequences.

The insights should be:
- Non-obvious: Avoid banal restatements; prefer cross-context synthesis.
- Grounded: Make sure the insights are grounded in the observations.

## Evaluation Criteria
For each cluster, evaluate its generality and cohesion on a scale from 1-10. 

## Generality Scale
- A score of 1–3 corresponds to concrete actions, events, or facts. (e.g., "User clicks the Save button repeatedly.")
- A score of 4–6 correspondds to behavioral insights, patterns, or strategies (e.g., "User double-checks work frequently to avoid mistakes")
- A score of 7–10 correspond to latent insights about deep motivations, values, or systemic needs (e.g., "User has difficulty balancing between work and family.")

## Cohesion Scale
Cohesiveness measures how well the observations in the cluster belong together and describe a single, unified theme. Be conservative in giving high cohesion scores.
- A score of 1–3 corresponds to low cohesion, meaning observations are scattered, inconsistent, or unrelated and hard to summarize in one short sentence.
- A score of 4–6 corresponds to moderate cohesion, meaning observations share a loose connection but lack tight alignment and summary requires multiple clauses to capture differences.
- A score of 7–10 corresponds to high cohesion, meaning observations are strongly related and support a single clear theme and easy to summarize in one short, precise statement.

If a summary has multiple clauses or is not succinct, give a low cohesion score.

## Example
Grouped Observations:
{{ "id": 101, "text": "User bought a book titled 'Atomic Habits'." }},
{{ "id": 205, "text": "User signed up for a 5 AM spin class but didn't attend." }},

Explanation for grouping:
The user bought a book titled 'Atomic Habits' but didn't attend the spin class, showing that they are trying to improve their habits but struggling to follow through.

Output: 
{{
  "observations": [
    {{
      "observation": "User is actively seeking behavior change but struggling with consistency.",
      "reasoning": "Purchasing 'Atomic Habits' suggests an interest in improving routines, yet missing the 5 AM spin class indicates difficulty sustaining new habits. This pattern implies a potential mismatch between aspirations and current energy levels, schedules, or motivation. The evidence suggests that while the user desires structure and self-improvement, lifestyle constraints or competing priorities may be preventing follow-through.",
      "generality": 7,
      "cohesion": 7
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
      "observation": "Concise, synthesized statement capturing a pattern that combines the raw observations.",
      "evidence": "1-2 sentences explaining the observation, citing specific evidence from the observations",
      "generality": "[Generality score (1–10)]",
      "cohesion": "[Cohesion score (1–10)]"
    }}
  ]
}}
"""
