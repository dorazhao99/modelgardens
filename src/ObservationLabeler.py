import json 
from prompts import observation_filters
from response_formats import FilterResponse
from utils import call_gpt 
import os 
import orjson
import asyncio 
from openai import AsyncOpenAI
from dotenv import load_dotenv
from collections import deque
from typing import List, Dict
from itertools import combinations 
load_dotenv()

class Labeler(): 
    def __init__(self, filter_name:str, model:str, idx:str): 
        filename = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/text_summary_gpt-4o_gum_reflect/{idx}_observe_o3.json"
        self.data = json.load(open(filename))
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        prompts = {
            "interesting": observation_filters.INTERESTING_SCORE
        }
        self.filter_prompt = prompts[filter_name]
        self.save_file = f"{filter_name}_{idx}.json"
    
    def _save_file(self, output):
        with open(self.save_file, "wb") as f:
            f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)
        
    async def apply_prompt(self, verbose=True) -> Dict:
        tasks = []
        oids = list(self.data.keys())
        for obs in self.data:
            observation = f"Observation: {self.data[obs]['description']}\nEvidence: {'\n'.join(self.data[obs]['evidence'])}"
            prompt = self.filter_prompt.format(body=observation)
            if int(obs) < 2 and verbose:
                print(prompt)
            tasks.append(self._guarded_call(self.client, prompt, self.model, resp_format=FilterResponse))
        
        scored_output = {}
        output = await asyncio.gather(*tasks, return_exceptions=True)
        for oid, o in zip(oids, output):
            info = o.model_dump()
            info['observation'] = self.data[oid]
            scored_output[oid] = info
        self._save_file(scored_output)
        return scored_output
    
    
def main(filter_name, model, idx):
    labeler = Labeler(filter_name, model, idx)
    asyncio.run(labeler.apply_prompt())

if __name__ == "__main__":
    
    filter_name = "interesting"
    model = "gpt-4o"
    idx = "41"
    main(filter_name, model, idx)
