import os
import asyncio
import json
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from typing import List
from dotenv import load_dotenv
from openai.types.responses import response_status
from utils import call_gpt, call_anthropic
from advice import INSIGHT_ADVICE_PROMPTS
from longterm_prompts import BASELINE_LONGTERM_PROMPT, LONGTERM_SOLUTION_PROMPT

load_dotenv()


class LongtermSolution:
    def __init__(self, model: str, fidx: str, user: str, save_file: str, limit: int = 2):
        self.model = model
        self.fidx = fidx
        self.user = user
        self.save_file = save_file
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.insights = json.load(open(f"../data/{self.fidx}/pipeline_outputs/session-meta/insights_prompt.json"))["insights"]
        self.fmt_insights = self._format_insights()
        self.insight_prompt = INSIGHT_ADVICE_PROMPTS["v3"]
        self.limit = limit
        self.claude_model = "claude-sonnet-4-5-20250929"

    def _format_insights(self):
        insights = []
        for i, insight in enumerate(self.insights):
            fmt_insight = f"ID {i} | {insight['title']}: {insight['tagline']}\n{insight['insight']}\nContext Insight Applies: {insight['context']}"
            insights.append(fmt_insight)
        return "\n\n".join(insights)

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)
    

    async def get_baseline_solutions(self, query:str, solution_limit:int = 3):
        baseline_prompt = BASELINE_LONGTERM_PROMPT.format(scenario=query, limit=solution_limit, user_name=self.user)
        print(baseline_prompt)
        baseline_response = await call_anthropic(self.anthropic_client, baseline_prompt, self.claude_model)
        return baseline_response

    async def get_insight_solutions(self, query:str, hmws: List[str], insights: str):
        tasks = []
        for hmw in hmws:
            baseline_prompt = LONGTERM_SOLUTION_PROMPT.format(scenario=query, hmw=hmw, limit=self.limit, user_name=self.user, insights=insights)
            print(baseline_prompt)
            tasks.append(call_anthropic(self.anthropic_client, baseline_prompt, self.claude_model))
        responses = await asyncio.gather(*tasks)
        for hmw, response in zip(hmws, responses):
            print(f"HMW: {hmw}")
            print(response)
            print("-"*100)
        return responses


async def sandbox():
    advice_seeker = LongtermSolution(model="gpt-4.1", fidx="dora_pilot", user="Dora", save_file="advice.json", limit=3)
    resp = await advice_seeker.get_baseline_solutions("Need assistance when writing CHI reviews")
    print(resp)
    hmws = [
        "Amp up the good: HMW leverage Dora's rigorous critique skills to build her confidence in her own reviewing authority?",
        "Question the assumption: HMW reframe external validation as a complement rather than a prerequisite to Dora's expertise?",
        "Remove the bad: HMW reduce Dora's uncertainty spiral when evaluating CHI submissions so she trusts her analytical judgments?"
    ]
    insights = """The Imposter Among Experts: Seeking Validation While Validating Others: Dora feels uncertain of her authority despite clear analytical strength, persistently seeking external benchmarks and community standards to authorize her decisions while rigorously critiquing others' work. Nuance vs. Clarity: The Ethical Tension in Simplification: Dora feels committed to representing multiple perspectives accurately and sensitively, but the pressure to craft clear, impactful narratives for audiences forces difficult tradeoffs between honoring complexity and achieving engagement."""
    resps = await advice_seeker.get_insight_solutions("Need assistance when writing CHI reviews", hmws, insights)
    print(response_status)

async def main():
    # questions = [
    #     "I have a big presentation coming up for the end of my grant. How should I prep my slides?", 
    #     "I have to balance three different projects at work. How should I prioritize them?",
    #     "I want to tell my advisor that I want to quit one of my projects, but I'm afraid they'll be angry. What should I do?",
    #     "I need to develop a mobile app for my new project, but I've literally never done this before and I'm afraid I'll mess it up. What should I do?",
    #     "I need to  potential collaborator who I've never met before about setting up a meeting to chat about a new project. What should I say?",
    #     "I'm going to meet my partner's parents for the first time... what are some tips for making a good impression?",
    #     "I've been really struggling with my productivity lately like I can't get any work done during the day and am stressed and worried about falling behind. How do I get back on track?",
    #     "I'm working on a project with some collaborators but they're literally not doing anything and expecting me to do everything. What do I do?",
    #     "I got asked to be a panelist for a conference and I have no idea what to say. What should I do?",
    # ]
    # questions = [
    #     "I've been really struggling with my productivity lately like I can't get any work done during the day and am stressed and worried about falling behind. How do I get back on track?",
    # ]
    questions = [
        "Build a personalized calendar manager that helps me manage my time and schedule my tasks.",
    ]
    advice_seeker = AdviceSeeker(model="gpt-4.1", fidx="dora_pilot", user="Dora", save_file="advice.json")

    tasks = []
    for q in questions:
        tasks.append(advice_seeker.get_advice(q))
        
    results = await asyncio.gather(*tasks)
    for r, q in zip(results, questions):
        i_response = r
        print(q)
        print("Model Response:")
        print(i_response['model_response'])
        print("\n")
        print("Baseline Response:")
        print(i_response['baseline_response'])
        # print(ni_response)
        print("-"*100)

if __name__ == "__main__":
    asyncio.run(sandbox())
    # asyncio.run(main())