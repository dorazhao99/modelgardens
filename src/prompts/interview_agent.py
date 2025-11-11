QUESTION_GENERATOR_PROMPT = """
You have behavioral observations and hypotheses about what motivates a user, but you're missing key context that would determine what kind of need this actually represents.
Your task is to generate {limit} strategic follow-up questions that would provide the most valuable context for converting
behavioral hypotheses into accurate, actionable need statements.

## You'll receive:
1. **Hypotheses**: Interpretations of what motivates the user's behavior
2. **Evidence**: Specific observed behaviors that support these hypotheses

## What You Need to Discover
Good need statements require understanding:
1. **Stance (amplify vs. minimize)**: Does the user want to lean into this behavior or find relief from it?
2. **Intentional vs. symptomatic**: Is this a deliberate strategy or a symptom of an unmet need?
3. **Stakes**: What happens if this need isn't met? What are they protecting or pursuing?
4. **Generalizability**: Does this pattern extend beyond the immediate context to reveal something fundamental about the user?

## Question Selection Strategy
Choose questions that:
- **Fill the biggest gaps**: What's most ambiguous or uncertain in the hypotheses?
- **Distinguish between interpretations**: What would confirm or disconfirm the current hypothesis?
- **Maximize information gain**: What single question would most change your understanding?
- **Address multiple reasoning steps**: Can one question inform both stance AND stakes?

Avoid:
- Questions that confirm what you already know
- Yes/no questions that don't reveal nuance
- Leading questions that bias the response
- Purely factual questions that don't uncover motivation

Finalize the {limit} most important questions. Make sure these questions are distinct and have minimal overlap.

## Input 
{input}

## Output
Please respond ONLY with a JSON that matches the following json schema, including your reasoning and the questions along with their relative weight (1–10). 
The weight is the estimated *importance* of the question to uncovering needs, where (1 = not important, 5 = moderately important, 10 = very important).

{{
    "questions": [
        {{
            "question": "Question",
            "weight": "[1-10] rating on the importance of the question to uncovering needs",
            "reasoning": "Reasoning for why this question is relevant"
        }}
    ]
}}
"""

QUESTION_SELECTOR_PROMPT = """
You are given an initial need statement about a user and answers from a user interview. Your task is to refine the need statement based on the answers.

If the interview is unrevealing, return the original need statement.

Consider the following:
1. Read through the need statement and the answers from the user interview. 
2. Identify any contradictions between the need statement and the answers.
3. Identify any gaps in the need statement that are not addressed by the answers.
4. Identify any new information that is not addressed by the need statement.
5. Refine the need statement based on the answers.
6. Return the refined need statement.

# Guidance Examples
Here are examples of bad and good need statements:
- Bad (too low-level): "User needs better tools for document formatting." 
- Good (addresses higher-level need): "User needs to align her information environments with her particular cognitive patterns, rather than generic organizational formats."

- Bad (states what they do): "User needs to externalize tasks across multiple systems."
- Good (identifies the burden): "User needs to offload task sequencing and context without the constant anxiety of checking whether critical details have slipped through the cracks between systems."

- Bad (descriptive): "User needs to coordinate across multiple tools for research workflow."
- Good (aspirational): "User needs her distributed tool ecosystem to feel like a unified cognitive workspace, reducing the mental overhead of translating context between disconnected platforms."

# Input
Initial Need Statement: 
{initial_need_statement}

Interview:
{interview}

# Output  
Return only a JSON object in this format. Use language that would be accessible to a lay person. Avoid over-generalizations. 

{{
  "name": "2-6 word title summarizing the need (e.g., Managing context-switches, Supporting emotional labor).,
  "need": "1-2 sentences articulating the user need statement.",
  "reasoning": "Show the step-by-step reasoning process. Make sure to explain the stance (to amplify or minimize behaviors).",
  "motivation": "Why does this need exist? What's at stake if this need isn't met?",
  "behaviors": [
    "list of 3–6 concrete behavioral patterns from the cluster that demonstrate the need",
    "each should be written as an active present-tense clause"
  ],
  "implications": [
    "2–4 non-obvious design implications",
    "Focus on what would be *missed* by conventional tools/processes"
  ]
}}
""" 