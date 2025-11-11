import argparse
from response_formats import (
    NeedRubricResponse,
    RelevanceResponse,
    ImportanceResponse
)
from prompts import tool_spec, rubrics
from utils import call_gpt, format_needs, format_goals
from openai import AsyncOpenAI
import os, json, time
import asyncio
import orjson
from dotenv import load_dotenv
from typing import List
import pdb
import numpy as np
import traceback
load_dotenv()


class NeedGrader:
    def __init__(self, model: str, fidx: str, filename: str):
        self.need_judge = rubrics.NEED_JUDGE_RUBRIC 
        self.task_judge = rubrics.TASK_RELEVANCE_RUBRIC
        self.needs = json.load(open(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}.json", "r"))
        if os.path.exists(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}_graded.json"):
            self.needs = json.load(open(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}_graded.json", "r"))
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.need_support = self.get_evidence()
        self.graded_needs = []
        self.save_file = f"../data/{fidx}/pipeline_outputs/session-meta/{filename}_graded.json"
    
    def get_evidence(self):
        all_evidence = []
        for need in self.needs:
            evidence = []
            for item in need['cluster_items']:
                evidence.extend(item['observation']['evidence'])
            all_evidence.append(evidence)
        assert len(all_evidence) == len(self.needs)
        return all_evidence

    
    async def grade_needs(self):
        tasks = []
        for need, support in zip(self.needs, self.need_support):
            fmt_support = " ".join(support)
            prompt = self.need_judge.format(need_statement=need['need'], observations=fmt_support)
            print(prompt)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=NeedRubricResponse))
            # tasks.append(self.client.chat.completions.create(
            #     model=self.model,
            #     messages=[{"role": "user", "content": prompt}],
            # ))
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        self.graded_needs = resps
        return resps
    
    async def grade_task_relevance(self, goals: List[str]):
        fmt_goals = "\n".join([f"- {goal['goal']}: {goal['description']}" for goal in goals['goals']])
        tasks = []
        for need in self.needs:
            prompt = self.task_judge.format(need_statement=need['need'], goals=fmt_goals)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=RelevanceResponse))
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for i, resp in enumerate(resps):
            print(self.needs[i]['need'])
            scores = [self.needs[i]['total_score'], resp.relevance]
            print(scores, np.mean(scores))

        return resps
    
    async def grade_importance(self):
        tasks = []
        for need in self.needs:
            seen_ids = set([])
            observations = []
            for item in need['cluster_items']:
                for obs in item['observation']['supporting_observations']:
                    oid = obs['id']
                    if oid not in seen_ids:
                        seen_ids.add(oid)
                        observations.extend(obs['evidence'])
            fmt_obs = "\n".join(observations)
            fmt_need = f"Need: {need['need']}\nDescription: {need['need']}"
            prompt = rubrics.IMPORTANCE_RUBRIC.format(need=fmt_need, observations=fmt_obs)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=ImportanceResponse))
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for i, resp in enumerate(resps):
            self.needs[i]['graded_need']['importance'] = resp.model_dump()
        with open(self.save_file, "wb") as f:
            assert self.needs[0]['graded_need']['importance'] is not None
            f.write(orjson.dumps(self.needs, option=orjson.OPT_INDENT_2))

        
        
    def save_graded_needs(self):
        for i, need in enumerate(self.needs):
            need['graded_need'] = self.graded_needs[i].model_dump()
            need['total_score'] = float(np.mean([self.graded_needs[i].support, self.graded_needs[i].non_obviousness, \
                self.graded_needs[i].clarity, self.graded_needs[i].actionability]))
        with open(self.save_file, "wb") as f:
            f.write(orjson.dumps(self.needs, option=orjson.OPT_INDENT_2))

    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("--model", type=str, required=True)
    # parser.add_argument("--fidx", type=str, required=True)
    # parser.add_argument("--filename", type=str, required=True)
    args = parser.parse_args()
    need_grader = NeedGrader("gpt-5", "dora_pilot", "cluster_motivation_o4-mini_hypothesis2")
    # asyncio.run(need_grader.grade_needs())
    # need_grader.save_graded_needs()
    goals = json.load(open("../data/dora_pilot/tool_eval/chi_review/goals.json", "r"))
    # asyncio.run(need_grader.grade_task_relevance(goals=goals))
    asyncio.run(need_grader.grade_importance())