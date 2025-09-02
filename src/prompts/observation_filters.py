INTERESTING_SCORE = """
You are an expert design researcher analyzing a user observations and evidence supporting the observation from a needfinding study.  
Your task is to **score each observation** on a scale from **1** to **10** based on **how interesting or surprising the behavior being described is**.

## Scoring Guidelines
- **1–3 (Low Interest / Low Perplexity)**  
  - The behavior is very common, predictable, or obvious.  
  - Likely to be something you already expect or is broadly known.
- **4–6 (Moderate Interest / Moderate Perplexity)**  
  - The behavior has some novel aspect or unexpected twist.  
  - It raises mild curiosity or indicates a potentially noteworthy pattern.
- **7–8 (High Interest / High Perplexity)**  
  - The behavior is clearly unusual, counterintuitive, or surprising.  
  - It provides strong insight into user motivations or unexpected workflows.
- **9–10 (Very High Interest / Very High Perplexity)**  
  - The behavior is rare, highly unexpected, or deeply revealing.  
  - It challenges assumptions or reveals a previously hidden pain point, strategy, or need.

## Input
{body}

## Output Format
Return **only** JSON in the following format:

{{
  "score": <1-10>,
  "reasoning": "<brief 1-2 sentence explanation for why the observation received this score>"
}}
"""

SELECTION_PROMPT = """
You are an expert design researcher analyzing a user observations and evidence supporting the observation from a needfinding study.  

You are provided a selected interesting observation. Your task is to select additional observations that are related to the selected observation.

## Input
Selected observation:
{selected}

All observations:
{body}

## Output Format
Return **only** JSON in the following format. Report just the IDs of the selected observations.

{{
  "observations": [<ID1>, <ID2>, <ID3>, ...] // IDs of the selected observations
}}
"""