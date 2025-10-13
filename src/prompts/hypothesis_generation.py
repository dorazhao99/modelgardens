HYPOTHESIS_EVALUATION_PROMPT = """
You will be provided with a hypothesis about a user's behavior and set of observations. 

Your task is to predict the likelihood of the hypothesis being true based on the observations on a scale from 1-10.
A score of 1 means that there are many observations that strongly CONTRADICT the hypothesis.
A score of 5 means that there are observations that are neutral or do not provide strong evidence for or against the hypothesis.
A score of 10 means that there are observations that strongly DEMONSTRATE or SUPPORT the hypothesis.

If there are any observations that CONTRADICT the hypothesis, the score should be between 1 and 3.
Be conservative in your estimates as these hypotheses are often based on very little evidence or are speculative.

## Input 
Hypothesis:
{hypothesis}

Observations:
{observations}

## Output
Return only the following JSON and nothing else:
{{
    "judgement": "[Likelihood score (1-10)]",
    "reasoning": "[Explanation of the likelihood score]"
    "support_observations": "[Provide the IDs of any observations that DEMONSTRATE / SUPPORT the hypothesis]"
    "contradict_observations": "[Provide the IDs of any observations that CONTRADICT the hypothesis]"
}}
"""

HYPOTHESIS_RANK_PROMPT = """
You will be provided with a observed behavior, a set of hypotheses explaining the behavior, and other observations 

Your task is to predict which of the following hypotheses is most likely to be true based on the other observations.

Be critical in your evaluation and only return the ID of the hypothesis that is most likely to be true.

## Input 
Given the set of observations, assign the likelihood of each of the following hypotheses being true from 0 to 100. 

Observations:
{observations}

Behavior:
{behavior}

Hypotheses:
{hypotheses}

## Output
Return only the following JSON with the likelihood of each hypothesis. 
{{
    likelihoods: [
        {{
            "id": "ID of the hypothesis",
            "likelihood": "[Likelihood score (0-100)]"
            "reasoning": "[Explanation of the likelihood score]"
        }}, ...
    ]
}}
"""

HYPOTHESIS_GENERATION_PROMPT = """
You will be provided with observations of a user's behavior. For this observation, you must generate {limit} distinct hypotheses.

## Instructions for Generating Hypotheses:
1. Do not simply restate the observation. Your goal is to explore the potential cognitive, emotional, social, or pragmatic drivers of the action.
2.For each hypothesis, think deeply about what the user might care about and why they care about it. What are their goals, fears, insecurities, or priorities in this context?
3. Your set of hypotheses for each observation must be varied. They should range from grounded to speculative:
   - A plausible explanation that is directly supported by the details in the observation and common behavioral patterns.
   - An explanation that requires a small inferential leap, connecting a few dots in a non-obvious way.
   - A creative, "outside-the-box" explanation that considers less obvious or even counter-intuitive motivations, perhaps touching on identity, long-term goals, or hidden anxieties.
4. For each observation, list your hypotheses clearly. Each hypothesis should have a concise title and a brief explanation.

## Example
### Input
During a high-stakes project kickoff meeting with senior leadership, a junior team member repeatedly cracked jokes, some of which fell flat. They were the only one exhibiting this behavior.

### Output
{{
    hypotheses: [
        {{
            "text": "Deflecting Anxiety",
            "description": "The user feels overwhelmed and anxious in high-stakes environments. They use humor as a subconscious defense mechanism to deflect their own discomfort and cope with the pressure, even if the jokes aren't successful. They care most about managing their own internal emotional state."
        }},
        {{
            "text": "Fostering Psychological Safety",
            "description": "The user believes that the best ideas emerge from relaxed, psychologically safe environments. They are proactively using humor to break the tension, signal that it's okay to be informal, and encourage more open participation from their peers, even at the risk of appearing goofy to leadership. They care about the team's collective success and creativity."
        }},,
        {{
            "text": "Seeking Validation through Personality",
            "description": "The user is insecure about the value of their technical or business contributions and believes their main 'value-add' is their personality and ability to be the 'funny one.' They are attempting to establish this social role to gain validation and secure their place on the team. Their primary concern is social acceptance."
        }},
        {{
            "text": "Rejecting of Corporate Norms",
            "description": "The user holds a counter-corporate worldview and sees formal meetings as performative and inauthentic. Their jokes are a subtle act of rebellion and a way to signal their identity as someone who doesn't 'play the game.' They care about maintaining their personal authenticity above conforming to professional expectations."
        }}
    ]
}}

## Input
Here are observations about the user:
{observations}

## Output
Return just a JSON of the following format and nothing else
{{
    "hypotheses": [
        {{
            "text": "String summarizing the hypothesis",
            "description": "1-2 sentences explaining the hypothesis"
        }}
    ]
}}
"""