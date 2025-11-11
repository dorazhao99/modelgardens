import json 
from prompts import tool_spec, eval
from response_formats import ScenarioResponse, ToolResponse, Tool, JudgeResponse, PatternInductionResponse
from utils import call_gpt
import os 
import re
import numpy as np
import orjson
import asyncio 
from openai import AsyncOpenAI
from dotenv import load_dotenv
from collections import deque
from typing import List, Dict, Tuple
from itertools import combinations 
from sentence_transformers import SentenceTransformer
load_dotenv()

class EndToEnd(): 
    def __init__(self, idx, ilename, user, model, scenario, outfile): 
        self.idx = idx
        self.data = json.load(open(filename))
        self.needs = []
        for oid in self.data:
            for need in self.data[oid]:
                self.needs.append(need)
        self.needs = self.dedupe_instances()
        self.user = user
        self.model = model
        self.scenario = scenario
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.outfile = outfile
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))

    @staticmethod 
    def _normalize_text(s: str) -> str:
        s = (s or "").strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s

    def dedupe_instances(self, threshold= 0.8) -> List[dict]:
        em_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Normalize text and embed
        proposed_needs = [EndToEnd._normalize_text(p['need']) for p in self.needs]
        embeddings = em_model.encode(proposed_needs, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype=np.float32)  # (N, D)

        kept_indices = []
        kept_embs = None  # (K, D)

        for i, emb in enumerate(embeddings):
            if kept_embs is None:
                kept_indices.append(i)
                kept_embs = emb[np.newaxis, :]
                continue

            # Cosine similarities with all previously kept proposals
            sims = kept_embs @ emb  # (K,)
            if np.any(sims >= threshold):
                # Too similar to something we've already kept — drop it
                continue

            # Otherwise, keep it
            kept_indices.append(i)
            kept_embs = np.vstack([kept_embs, emb])

        # Produce final list, sorted by confidence desc (if present)
        deduped = [self.needs[i] for i in kept_indices]
        deduped.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return deduped

    def filter_needs(self, min_thresh=None, max_thresh=None) -> List[dict]:
        filtered_needs = self.needs
        if min_thresh is not None:
            filtered_needs = [need for need in filtered_needs if need['generality'] >= min_thresh]
        if max_thresh is not None:
            filtered_needs = [need for need in filtered_needs if need['generality'] <= max_thresh]
        return filtered_needs
    
    @staticmethod
    def format_needs(needs) -> str:
        formatted_needs = []
        for need in needs:
            formatted_needs.append(f"Need: {need['need']}\nReasoning: {need['reasoning']}")
        return '\n'.join(formatted_needs)

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)
        
    async def generate_scenarios(self, selected_needs: str) -> Tuple[List[dict], List[int]]: 
        baseline_prompt = tool_spec.PATTERN_INDUCTION_PROMPT
        baseline_prompt = baseline_prompt.format(context=self.scenario, limit=5, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
        needs_prompt = tool_spec.PATTERN_INDUCTION_PROMPT_NEEDS
        needs_prompt = needs_prompt.format(context=self.scenario, needs=selected_needs, limit=5, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
        baseline_resps = await self._guarded_call(self.client, baseline_prompt, self.model, resp_format=PatternInductionResponse)
        needs_resps = await self._guarded_call(self.client, needs_prompt, self.model, resp_format=PatternInductionResponse)
        return [i.model_dump() for i in baseline_resps.patterns], [i.model_dump() for i in needs_resps.patterns]
        # randomize 
        # for br, nr in zip(baseline_resps.tools, needs_resps.tools):
        #     is_first = np.random.randint(0, 2)
        #     if is_first == 0: 
        #         output = [br.model_dump(), nr.model_dump()]
        #         order = ["baseline", "need_augmented"]
        #     else: 
        #         output = [nr.model_dump(), br.model_dump()]
        #         order = ["need_augmented", "baseline"]
        #     outputs.append(output)
        #     answers.append(order)
        # return [tool.model_dump() for tool in baseline_resps.tools], [tool.model_dump() for tool in needs_resps.tools]  
    
    async def modulate_tool(self, selected_needs:str) -> Tuple[List[dict], List[int]]:
        baseline_prompt = tool_spec.PATTERN_INDUCTION_PROMPT
        baseline_prompt = baseline_prompt.format(context=self.scenario, limit=5, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)

        baseline_tool = await self._guarded_call(self.client, baseline_prompt, self.model, resp_format=PatternInductionResponse)
        # print(baseline_tool)
        needs_prompt = tool_spec.TOOL_UPDATE_PROMPT
        output = []
        for tool in baseline_tool:
            fmt_needs_prompt = needs_prompt.format(tool=tool, needs=selected_needs, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
            tool_update = await self._guarded_call(self.client, fmt_needs_prompt, self.model, resp_format=PatternInductionResponse)
            output.append(tool_update.model_dump())
        return output
    
    async def evaluate_needs(self) -> dict:
        gt_needs = json.load(open(f"results/needs/{self.idx}/ground_truth.json"))
        print(gt_needs)
        prompt = eval.NEEDS_JUDGE

        formatted_needs = []

        covered_ids = set([])
        expected_needs = {}
        for i, gt_need in enumerate(gt_needs):
            tasks = []
            expected_needs[str(i)] = []
            for n in self.needs:
                fmt_prompt = prompt.format(gt=gt_need, proposed=n)
                tasks.append(self._guarded_call(self.client, fmt_prompt, "gpt-4o"))
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            for j, resp in enumerate(resps):
                if int(resp) == 1:
                    covered_ids.add(j)
                    expected_needs[str(i)].append(self.needs[j])
        unexpected_needs = []
        for i in range(len(self.needs)):
            if i not in covered_ids:
                unexpected_needs.append(self.needs[i])

        print("Expected and covered needs: ", expected_needs)
        print("Unexpected needs: ", unexpected_needs)
        output = {
            "expected_needs": expected_needs,
            "unexpected_needs": unexpected_needs,
        }
        with open(f"results/needs/{self.idx}/{self.outfile}_judge.json", "wb") as f:
            f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
        return output


async def main(idx:str, filename:str, scenario:str):
    save_file = filename.split("/")[-1].split(".")[0]
    e2e = EndToEnd(idx, filename, "Dora", "gpt-4o", scenario)
    filtered_needs_high = e2e.filter_needs(min_thresh=7)
    filtered_needs_high = e2e.format_needs(filtered_needs_high)
    # baseline_tools, need_augmented_tools = await e2e.generate_scenarios(filtered_needs_high)
    outputs= await e2e.modulate_tool(filtered_needs_high)
    print(outputs)
    # high_outputs = await asyncio.gather(*high_tasks)
    # for output, order in high_outputs:
    #     outputs.append(output)
    #     answers.append(order)
    
    # with open(f"results/scenarios/41_general_o3_2_baseline_tools.json", "wb") as f:
    #     f.write(orjson.dumps(baseline_tools, option=orjson.OPT_INDENT_2))
    # with open(f"results/scenarios/41_general_o3_2_need_augmented_tools.json", "wb") as f:
    #     f.write(orjson.dumps(need_augmented_tools, option=orjson.OPT_INDENT_2))
    # with open(f"results/scenarios/41_general_o3_2_modulated_tools.json", "wb") as f:
    #     f.write(orjson.dumps(outputs, option=orjson.OPT_INDENT_2))
        
    # outputs, answers = [], []
    # low_tasks = []
    # filtered_needs_low = e2e.filter_needs(min_thresh=3, max_thresh=6)
    # filtered_needs_low = e2e.format_needs(filtered_needs_low)
    # baseline_tools, need_augmented_tools = await e2e.generate_scenarios(filtered_needs_low)
    # for _ in range(3):
    #     low_tasks.append(e2e.generate_scenarios(filtered_needs_low))
    # low_outputs = await asyncio.gather(*low_tasks) 
    # for output, order in low_outputs:
    #     outputs.append(output)s
    #     answers.append(order)


    # with open(f"results/scenarios/{save_file}_low.json", "wb") as f:
    #     f.write(orjson.dumps(outputs, option=orjson.OPT_INDENT_2))
    # with open(f"results/scenarios/41_general_o3_2_need_augmented_tools_low.json", "wb") as f:
    #     f.write(orjson.dumps(need_augmented_tools, option=orjson.OPT_INDENT_2))

async def run_judge(idx, filename, scenario, outfile):

    e2e = EndToEnd(idx, filename, "Dora", "gpt-4o", scenario, outfile)
    # for i in e2e.needs:
    #     print(i['confidence'])
    await e2e.evaluate_needs()

if __name__ == "__main__":
    idx = "synthetic_small"
    outfile = f"all_o4-mini_1"
    filename = f"results/needs/{idx}/{outfile}.json"
    scenario = """
    Dora's goal is to coordinate think-aloud sessions with participants for a research study. She needs to select participants, schedule the sessions, and assign interviewers.
    For each session, she needs to send out an email to the participants to confirm their availability, schedule the session on Zoom, and assign a member of her team as the interviewer.
    """  

    # asyncio.run(main(idx, filename, scenario))
    asyncio.run(run_judge(idx, filename, scenario, outfile))

