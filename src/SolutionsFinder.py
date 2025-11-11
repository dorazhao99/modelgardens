from prompts import solutions
from utils import call_gpt
from response_formats import SolutionResponse
import os 
import json
import argparse
import pandas as pd
import asyncio
from dotenv import load_dotenv 
from openai import AsyncOpenAI 
from utils import load_markdown 

class SolutionFinder:
    def __init__(self, model):
        load_dotenv()
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_solutions(self, needs, observations, tt_scale=0):
        tasks = []
        for need, observation in zip(needs, observations): 
            input_prompt = solutions.COT_PROMPT.format(user_need = need, observations=observation)
            if tt_scale > 0:
                for i in range(tt_scale):
                    tasks.append(call_gpt(self.client, input_prompt, self.model, resp_format=SolutionResponse))
            else:
                tasks.append(call_gpt(self.client, input_prompt, self.model, resp_format=SolutionResponse))
        resp = await asyncio.gather(*tasks, return_exceptions=True)
        return resp 

async def main(args):
    if args.need_source == 'gt':
        df = pd.read_csv('infact_dataset/benchmark.csv')
        df = df.dropna()
        needs = list(df['need'].values)
        if args.tt_scale:
            idxs = [i for i in list(df['id'].values) for _ in range(args.tt_scale)]
            new_needs = [i for i in needs for _ in range(args.tt_scale)]
            needs = new_needs
        else:
            idxs = list(df['id'].values)
    else:
        print("not implemented")

    observations = []
    if args.observation_source == 'point':
        print('not implemented')
    elif args.observation_source == 'summarized':
        for fid in idxs:
            overview = load_markdown(f"infact_dataset/overview/{fid}.md")
            observations.append(overview)
    else:
        observations = [''] * len(needs)

    sol_finder = SolutionFinder(args.model)
    solutions = await sol_finder.generate_solutions(needs, observations)

    res_dir = os.path.join(args.output_dir)
    os.makedirs(res_dir, exist_ok=True)

    for idx, solution in enumerate(solutions): 
        save_file = idxs[idx]
        out_path = os.path.join(res_dir, f"{save_file}.json")
        print(out_path, needs)
        new_output = solution.dict()
        new_output['need'] = needs[idx]
        if os.path.exists(out_path):
            # Load, update, and overwrite
            with open(out_path, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}
            existing_data['solutions'].extend(new_output['solutions'])
            print(existing_data)
            with open(out_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
        else:
            # Write a brand new file
            with open(out_path, 'w') as f:
                json.dump(new_output, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run SolutionFinders on needs.")
    parser.add_argument("--need_source", type=str, required=True)
    parser.add_argument("--observation_source", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--tt_scale", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(main(args))
