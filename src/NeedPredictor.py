import json
import stat 
from prompts import need_finder, observation_filters
from response_formats import NeedResponse, ObservationIDResponse, ScoredNeedResponse
from utils import call_gpt, call_gpt_logprobs
import os 
import random
import numpy as np
import orjson
import asyncio 
from openai import AsyncOpenAI
from dotenv import load_dotenv
from collections import deque
from typing import List, Dict
from itertools import combinations 

load_dotenv()

class NeedPredictor(): 
    def __init__(self, filename, user, model): 
        self.data = json.load(open(filename))
        if isinstance(self.data, List):
            self.data = {i['id']: i for i in self.data}
        self.user = user
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
    @staticmethod
    def format_observation(observation: Dict) -> str:
        return f"Observation ID {observation['id']}: {observation['description']}\nEvidence: {observation['evidence']}"
    
    def bfs(self, start_id: str) -> List[str]: 
        visited = set()
        queue = deque([start_id])
        order = []
        output = []
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            
            visited.add(node_id)
            order.append(node_id)
            output.append(NeedPredictor.format_observation(self.data[node_id]))
            # Get neighbors from "merged" if they exist
            node = self.data.get(node_id, {})
            neighbors = node.get("merged", [])
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append(neighbor)
        return output
    
    async def select_observations(self, selected_observation: str) -> List[str]:
        selected = ""
        all_observations = []
        for nid in self.data:
            if nid == selected_observation:
                selected = f"ID {nid}: {self.data[nid]['description']}\nEvidence: {self.data[nid]['evidence']}"
            else:
                all_observations.append(f"ID {nid}: {self.data[nid]['description']}\nEvidence: {self.data[nid]['evidence']}")
        input_prompt = observation_filters.SELECTION_PROMPT.format(selected=selected, body='\n'.join(all_observations))
        resp = await self._guarded_call(self.client, input_prompt, "gpt-4o", resp_format=ObservationIDResponse)
        return resp.observations


    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)
        
    async def generate_needs(self, observations): 
        if isinstance(observations, str):
            formatted_obs = observations
        else:
            formatted_obs = '\n'.join(observations)
        input_prompt = need_finder.NEEDFINDER_PROMPT.format(user_name=self.user, input=formatted_obs)
        resp = await self._guarded_call(self.client, input_prompt, "o4-mini", resp_format=NeedResponse)
        return resp 
    
    async def recognize_needs(self, observations, options):
        if isinstance(observations, str):
            formatted_obs = observations
        else:
            formatted_obs = '\n'.join(observations)
        input_prompt = need_finder.NEED_RECOG_PROMPT.format(user_name=self.user, input=formatted_obs, statements=options)
        resp = await call_gpt_logprobs(self.client, input_prompt, "gpt-4o")
        return resp 
    
    def apply_filter(self, nodes: List[str]) -> Dict:
        input = []
        num_obs = 1
        for node in nodes:
            retrieved = self.bfs(node)
            input.extend(retrieved)
        observations = "\n".join(input)
        return observations

    async def score_needs(self, needs: List[Dict]):
        tasks = []
        for need in needs['needs']:
            related_observations = need['related_observations']
            support = []
            for o in related_observations:
                support.append(f"{self.data[str(o)]['description']}\nEvidence: {self.data[str(o)]['evidence']}")

            # Randomly sample other observations from self.data that are not in related_observations
            all_obs_ids = set(self.data.keys())
            related_obs_ids = set(str(o) for o in related_observations)
            other_obs_ids = list(all_obs_ids - related_obs_ids)
            # Sample up to 3 other observations (or fewer if not enough)
            num_samples = min(10, len(other_obs_ids))
            sampled_other_obs = random.sample(other_obs_ids, num_samples) if num_samples > 0 else []
            for o in sampled_other_obs:
                support.append(f"{self.data[o]['description']}\nEvidence: {self.data[o]['evidence']}")
            random.shuffle(support)

            fmt_support = "\n".join(support)
            input_prompt = need_finder.SCORE_NEEDS_PROMPT.format(need=need['need'], observations=fmt_support)
            print(input_prompt)
            tasks.append(self._guarded_call(self.client, input_prompt, "gpt-4o", resp_format=ScoredNeedResponse))
        resps = await asyncio.gather(*tasks, return_exceptions=True) 
        scored_needs = []

        for r, need in zip(resps, needs['needs']):
            output = need
            output['importance'] = r.importance
            output['surprise'] = r.surprise
            output['score_rationale'] = r.reasoning
            scored_needs.append(output)
        return scored_needs

# Selection filters
def most_general(graph: Dict): 
    all_nodes = set(graph.keys())
    referenced_nodes = set()
    for node in graph.values():
        referenced_nodes.update(node.get("merged", []))
    root_candidates = all_nodes - referenced_nodes
    roots_with_children = [
        node_id for node_id in root_candidates
        if graph.get(node_id, {}).get("merged")
    ]

    return roots_with_children

def get_all_with_merged(graph: Dict):
    """
    Returns a list of node IDs that have a non-empty 'merged' field.
    """
    return [nid for nid, node in graph.items() if node.get("merged")]

def get_all_nodes(graph: Dict):
    """
    Returns a list of all node IDs
    """
    return list(graph.keys())


def get_orphans(graph: Dict): 
    # Get nodes with no parents and no children
    all_nodes = set(graph.keys())
    referenced_nodes = set()
    for node in graph.values():
        referenced_nodes.update(node.get("merged", []))
    # Nodes with no parents
    no_parents = all_nodes - referenced_nodes
    # Nodes with no children
    no_children = {nid for nid, node in graph.items() if not node.get("merged", [])}
    # Nodes with no parents and no children
    orphans = no_parents & no_children
    return orphans

def random_sample(graph: Dict): 
    all_nodes = set(graph.keys()) 
    max_length = len(all_nodes)
    node_names = []
    np.random.seed(0)
    for i in range(10):
        number_nodes = 0 # generate number of nodes
        selected_nodes = [] # randomly select that number of nodes 
        node_names.append(selected_nodes)
    return node_names

def apply_filter(filter_name: str, idx: str, thresh: int) -> List:
    filter_responses = json.load(open(f"{filter_name}_{idx}.json"))
    filtered_options = []
    for oid in filter_responses:
        resp = filter_responses[oid]
        if resp['score'] >= thresh: 
            filtered_options.append(oid)
    print(filtered_options)
    return filtered_options




async def main(filter_name:str, method:str, stem:str, model:str, aggregation:int, strategy: str, user:str):
    # filename = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/text_summary_gpt-4o_gum_reflect/{idx}_observe_o3.json"
    filename = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/{method}/{stem}.json"
    # filename = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/perturbations/7_shuffled.json"
    need_p = NeedPredictor(filename, user, model)
    # observation = need_p.bfs("42", count=1)
    if filter_name == "general":
        nodes = most_general(need_p.data)
    elif filter_name == "interesting":
        nodes = apply_filter(filter_name, idx, 8)
    elif filter_name == "orphan":
        nodes = get_orphans(need_p.data)
    elif filter_name == "merged":
        nodes = get_all_with_merged(need_p.data)
    elif filter_name == "all":
        nodes = get_all_nodes(need_p.data)


    tasks = []
    print(nodes)
    if strategy == "llm-select":
        for node in nodes:
            tasks.append(need_p.select_observations(node))
        resps = await asyncio.gather(*tasks, return_exceptions=True)

        need_tasks = []
        for node, resp in zip(nodes, resps):
            observations = []
            observations.append(need_p.format_observation(need_p.data[node]))
            for oid in resp:
                oid = str(oid)
                observations.append(need_p.format_observation(need_p.data[oid]))
            need_tasks.append(need_p.generate_needs(observations))
        output = {}
        resps = await asyncio.gather(*need_tasks, return_exceptions=True)
        for node, resp in zip(nodes, resps):
            output[node] = []
            for need in resp.needs:
                output[node].append(need.model_dump())
        # with open(f"results/needs/{idx}_{filter_name}_{model}_{aggregation}_{strategy}.json", "wb") as f:
        #     f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
    elif strategy == "bfs":
        if aggregation > 1: 
            combo_names = []
            for a, b in combinations(nodes, r=aggregation):
                observations = need_p.apply_filter([a, b])
                tasks.append(need_p.generate_needs(observations))
                combo_names.append(f"{a}-{b}")
            output = {}
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            for resp, combo in zip(resps, combo_names):
                output[combo] = []
                try:
                    for need in resp.needs: 
                        output[combo].append(need.model_dump())
                except Exception as e:
                    print(e)
        else:
            observations = []
            for n in nodes:
                observation = need_p.apply_filter([n])
                observations.append(observation)
            tasks.append(need_p.generate_needs(observations))
            output = {}
            print('Awaiting tasks',len(tasks))
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            for resp, n in zip(resps, nodes):
                output[n] = []
                try:
                    for need in resp.needs: 
                        output[n].append(need.model_dump())
                except Exception as e:
                    print(e)
    else:
        observations = []
        for node in nodes:
            observations.append(need_p.format_observation(need_p.data[node]))
        print(observations)
    #     output = await need_p.generate_needs(observations)
    #     output = output.model_dump()
    # print(output)
    # updated_output = await need_p.score_needs(output)
    # out_path = f'results/needs/{stem}_{method}_{model}.json'
    # with open(out_path, "wb") as f:
    #     f.write(orjson.dumps(updated_output, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    random.seed(0)
    filter_name = "merged"
    method = "tooleval"
    model = "o3"
    user="Dora"
    aggregation = 1
    strategy = ""
    for i in ['41']:
        # if i == "_interview_o4-mini_20250918.json":
        # stem = i.split(".")[0]
        # stem = f"{i}_interview_o4-mini_20250918"
        stem = f"{i}_o4-mini_20251007"
        print(stem)
        asyncio.run(main(filter_name, method, stem, model, aggregation, strategy, user))
    # stem = "0_interview_o4-mini_20250917_120305"
    # asyncio.run(main(filter_name, method, stem, model, aggregation, strategy, user))