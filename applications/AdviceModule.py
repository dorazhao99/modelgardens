import os
import asyncio
import json
from anthropic import Anthropic
from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils import call_gpt, call_anthropic
from advice import INSIGHT_ADVICE_PROMPTS, ADVICE_PROMPT, SYSTEM_PROMPT, InsightBasedAdvice, Advice, RESPONSE_ADVICE_PROMPT

load_dotenv()


class AdviceSeeker:
    def __init__(self, model: str, fidx: str, user: str, save_file: str, limit: int = 2):
        self.model = model
        self.fidx = fidx
        self.user = user
        self.save_file = save_file
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.insights = json.load(open(f"../data/{self.fidx}/pipeline_outputs/session-meta/insights_prompt_support.json"))["insights"]
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
    
    async def get_advice(self, query: str):
        i_prompt = self.insight_prompt.format(user_name=self.user, insights=self.fmt_insights, query=query, limit=self.limit)
        ni_prompt = ADVICE_PROMPT.format(query=query)
        i_response = await self._guarded_call(self.client, i_prompt, self.model, resp_format=InsightBasedAdvice, systems_message=SYSTEM_PROMPT)
        print(i_response)
        hmw_statement =i_response.hmw_statement
        hmw_candidates = i_response.hmw_candidates

        output = i_response.model_dump()
        baseline_response = call_anthropic(self.anthropic_client, query, self.claude_model)
        output['baseline_response'] = baseline_response
        if len(hmw_candidates) > 0 and hmw_statement.lower() != 'none':
            response_prompt = RESPONSE_ADVICE_PROMPT.format(query=query, hmw_statement=hmw_statement)
            print(response_prompt)
            response = call_anthropic(self.anthropic_client, response_prompt, self.claude_model)
            output['model_response'] = response
        else:
            output['model_response'] = "Same as baseline"
        return output


async def sandbox():
    advice_seeker = AdviceSeeker(model="gpt-4.1", fidx="dora_pilot", user="Dora", save_file="advice.json")
    print(advice_seeker.fmt_insights)
    i_response, ni_response = await advice_seeker.get_advice("I'm planning a Thanksgiving dinner for my family. What should I make?")
    print(i_response)
    print(ni_response)

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
    questions = [
        "I've been really struggling with my productivity lately like I can't get any work done during the day and am stressed and worried about falling behind. How do I get back on track?",
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
    asyncio.run(main())