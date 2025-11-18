from openai import api_key
from needfinder import NeedFinder
from typing import List
from needfinder.llm import LLM
from dotenv import load_dotenv
import pytest
import re, os

load_dotenv()

TEST_INSIGHTS = {
    "insights": [
      {
        "title": "The Deep Focus Dilemma: Craving Immersion While Drowning in Interruptions",
        "tagline": "Dora feels torn between her intellectual strength in sustained, synthesis-driven work and the relentless pull of fragmented, interrupt-driven demands that fragment her attention and drain her energy.",
        "insight": "Dora thrives when she can engage deeply—synthesizing ideas, mapping frameworks, and pursuing conceptual clarity—yet her daily reality forces rapid context-switching among coding, communication, logistics, and administration. This clash between her capacity for deep focus and the interrupt-driven workflow leaves her cognitively fragmented and fatigued. She experiences her greatest sense of meaning and impact during synthesis-heavy work, but much of her day is consumed by procedural tasks that underutilize her strengths.",
        "context": "Most applicable during knowledge work requiring deep focus (coding, research synthesis, academic writing) that is interleaved with communication, scheduling, and administrative tasks. Especially relevant when coordinating studies or collaborations under deadline pressure.",
        "merged": ["1-0", "1-4", "3-3", "5-4", "6-0"],
        "reasoning": "These insights share a common thread: Dora's intellectual strength and preference for sustained, synthesis-oriented work is constantly at odds with fragmented, polychronic demands. Across sessions, she experiences cognitive overload from context-switching between depth and breadth, collaborative coordination and solo deep work, intellectual engagement and logistical survival. The contradiction reveals both what motivates her (synthesis, conceptual clarity) and what drains her (interruption, procedural fragmentation)."
      },
      {
        "title": "Persistent but Inefficient: Learning Through Trial and Pain",
        "tagline": "Dora feels determined to push through technical obstacles on her own, but the emotional and cognitive toll of repeated debugging friction suggests she's absorbing systemic failures as personal responsibility.",
        "insight": "Dora demonstrates remarkable persistence when debugging and troubleshooting, iterating through documentation, trial-and-error, and tool consultation. However, the repetition of similar errors and the intensity of her focus on failure-handling suggest gaps in systematic problem-solving strategies and unaddressed emotional labor. She tends to internalize technical friction as her own shortcoming rather than challenging the tools or systems themselves, which prolongs resolution time and compounds cognitive load.",
        "context": "Most applicable during programming, data analysis, environment setup, and multi-tool technical workflows, especially when debugging errors across R/Python/CLI or integrating external APIs and compliance systems.",
        "merged": ["1-1", "5-1"],
        "reasoning": "Both insights reveal Dora's persistence in the face of recurring technical friction, but also highlight the cost: inefficiency, emotional labor, and a tendency to absorb systemic issues as personal failings. The focus is on how she feels (determined yet burdened) and what drives her (resilience through iteration despite the toll)."
      },
      {
        "title": "The Helpful Overextender: Generosity at the Cost of Self-Preservation",
        "tagline": "Dora feels compelled to support others and remain responsive across channels, but this conscientiousness amplifies her workload and leaves her stretched too thin to protect her own focus and well-being.",
        "insight": "Dora actively mentors, coordinates, and responds to peers while managing a heavy personal workload. Her desire to be a generous, collaborative community member conflicts with her need for sustained focus and self-care. She signals collaborative readiness through open communication channels and quick responses, yet the cognitive and logistical demands of staying helpful compound her time pressure and cognitive fragmentation. The resulting tension threatens both her impact and her energy reserves.",
        "context": "Most applicable when juggling communications (Slack, email, calendar) alongside deep-work tasks like coding, writing, and analysis, especially when supporting peers or coordinating studies while managing her own deadlines.",
        "merged": ["1-2"],
        "reasoning": "This insight stands alone because it uniquely captures Dora's social and relational motivations—her conscientiousness and desire to support others—and the emotional and cognitive cost of that generosity. It reveals what she values (community, helpfulness) and how it conflicts with her capacity."
      },
      {
        "title": "Meticulous to a Fault: Perfectionism as Anxiety Management",
        "tagline": "Dora feels anxious about errors and seeks reassurance through repeated verification, double-checking, and micro-adjustments, but this meticulousness reinforces self-doubt rather than building confidence.",
        "insight": "Dora demonstrates extraordinary attention to detail, consistently verifying emails, schedules, terminology, sources, and outputs with high precision. However, the repetition and oscillation between micro-editing and macro synthesis suggest underlying anxiety, perfectionism, and difficulty settling on 'good enough.' This meticulousness elevates quality but creates bottlenecks, slows decision-making, and may signal a lack of trust in her own judgment. The perfectionism functions as both a driver of rigor and a blocker of progress.",
        "context": "Most applicable during high-stakes communication (emails to recruiters, journalists), academic writing and reviewing, data presentation, slide design, and coding/debugging where accuracy and polish matter, especially under deadlines or external scrutiny.",
        "merged": ["1-3", "4-0", "6-1"],
        "reasoning": "These insights converge on Dora's perfectionist tendencies and the anxiety that fuels them. The focus is on her internal experience—feeling anxious, seeking reassurance, struggling to commit—and how meticulousness serves as both a coping mechanism and a source of cognitive burden."
      }
    ]
}

TEST_PROBLEM = "I need help writing reviews for CHI."

# @pytest.mark.asyncio
# async def test_needfinder_default():
#     n = NeedFinder(user_name="Dora")
#     assert n is not None
#     n.user_insights = TEST_INSIGHTS
#     prompt = await n.reframe_problem(problem_description=TEST_PROBLEM)
#     return prompt

# @pytest.mark.asyncio
# async def test_needfinder_openai():
#     n = NeedFinder(user_name="Dora", reframer_model=LLM(name="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY")))
#     assert n is not None
#     n.user_insights = TEST_INSIGHTS
#     prompt = await n.reframe_problem(problem_description=TEST_PROBLEM)
#     return prompt

# @pytest.mark.asyncio
# async def test_insights_synthesis():
#   def _load_markdown(filepath):
#     with open(filepath, "r", encoding="utf-8") as f:
#         return f.read()
#   def human_sort(s: str) -> List:
#     return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

#   api_key = os.getenv("OPENAI_API_KEY")
#   n = NeedFinder(user_name="Dora", \
#     observer_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
#     insight_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
#     synthesis_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
#     reframer_model=LLM(name="gpt-4.1-mini", api_key=api_key))
#   assert n is not None
#   sessions = ["0", "1"]
#   fpath = "/Users/dorazhao/Documents/modelgardens/data/dora_pilot/processed_data/{0}/session-{1}/"
#   transcripts, summaries, timestamps = [], [], []
#   for session in sessions:
#     session_transcripts, session_summaries = [], []
#     filenames = sorted(os.listdir(fpath.format("transcripts", session)), key=human_sort)
#     for fname in filenames:
#       transcript = _load_markdown(fpath.format("transcripts", session) + fname)
#       summary = _load_markdown(fpath.format("summaries", session) + fname)
#       session_transcripts.append(transcript)
#       session_summaries.append(summary)
#     transcripts.append(session_transcripts)
#     summaries.append(session_summaries)
#   insights = await n.get_insights(transcripts=transcripts, summaries=summaries)
#   return insights

ACTION_INTENTS = {
    0: "Starting my day and working on miscellaneous tasks.", 
    15: "Working on my PhD research project related to automated needfinding and refining my pipeline.", 
    23: "Taking a phone call with my friend Duke from high school who is applying to the P.D. Soros fellowship which I won last year and giving advice on his application.", 
    39: "Attending the HCI Seminar by Alexandra Olteanu where she is talking about rigor in Responsible AI and taking notes on the seminar content", 
    69: "Attending my class PSCYH 251: Experimental Methods” where we are going through a tutorial on how to use Tidyverse in R",
    139: "Attending a talk by Lucy Suchman and Terry Winograd on Generative Frictions and taking notes"
}

@pytest.mark.asyncio
async def test_insights_synthesis_context():
  def _load_markdown(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
  def human_sort(s: str) -> List:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

  api_key = os.getenv("OPENAI_API_KEY")
  n = NeedFinder(user_name="Dora", \
    observer_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
    insight_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
    synthesis_model=LLM(name="gpt-4.1-mini", api_key=api_key), \
    reframer_model=LLM(name="gpt-4.1-mini", api_key=api_key))
  assert n is not None
  sessions = ["0", "1"]
  fpath = "/Users/dorazhao/Documents/modelgardens/data/dora_pilot/processed_data/{0}/session-{1}/"
  transcripts, summaries, context_anns = [], [], []

  
  for session in sessions:
    session_transcripts, session_summaries, session_context_anns = [], [], []
    filenames = sorted(os.listdir(fpath.format("transcripts", session)), key=human_sort)

    action_idx = 0 
    all_action_idxs = list(ACTION_INTENTS.keys())
    current_action_idx = all_action_idxs[action_idx]
    next_action_idx = all_action_idxs[action_idx + 1]

    for idx, fname in enumerate(filenames):
      transcript = _load_markdown(fpath.format("transcripts", session) + fname)
      summary = _load_markdown(fpath.format("summaries", session) + fname)
      session_transcripts.append(transcript)
      session_summaries.append(summary)
      if idx >= next_action_idx:
        if action_idx + 1 < len(all_action_idxs):
          action_idx += 1
          current_action_idx = all_action_idxs[action_idx]
          if action_idx + 1 < len(all_action_idxs):
            next_action_idx = all_action_idxs[action_idx + 1]
      session_context_anns.append(ACTION_INTENTS[current_action_idx])
    transcripts.append(session_transcripts)
    summaries.append(session_summaries)
    context_anns.append(session_context_anns)
  insights = await n.get_insights(transcripts=transcripts, summaries=summaries, context_anns=context_anns)
  return insights