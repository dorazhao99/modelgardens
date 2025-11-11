import json 
import orjson
import asyncio
import os
import argparse
from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils import call_gpt
from prompts.hypothesis_generation import HYPOTHESIS_GENERATION_PROMPT
from response_formats import HypothesisResponse

load_dotenv()

class HypothesisGenerator:
    def __init__(self, model: str, fidx: str, num_sessions: int, limit: int = 5):
        self.model = model
        self.fidx = fidx
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.num_sessions = num_sessions
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.limit = limit
    
    def format_observation(self, observation: dict):
        if 'observations' in observation:
            evidence = [i['description'] for i in observation['observations']]
            evidence = " ".join(evidence)
        else:
            evidence = " ".join(observation['evidence'])
        return f"Observation: {observation['description']}\nEvidence: {evidence}"
    
    def get_observations(self, observations):
        obs = []
        # only get observations that are clustered
        for k, v in observations.items():
            if 'theme' in v:
                obs.append(v)
        return obs

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)

    async def generate_all_hypotheses(self):
        for session_idx in range(self.num_sessions):
            tasks = []
            print(f"Generating hypotheses for session {session_idx}")
            observations = json.load(open(f'../data/{self.fidx}/pipeline_outputs/session-{session_idx}/cluster_o4-mini.json'))
            observations = self.get_observations(observations)
            for obs in observations:
                fmt_observations = self.format_observation(obs)
                prompt = HYPOTHESIS_GENERATION_PROMPT.format(observations=fmt_observations, limit=self.limit)
                tasks.append(self._guarded_call(self.client, prompt, self.model, resp_format=HypothesisResponse))
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            output = []
            for obs, resp in zip(observations, resps):
                if 'observations' in obs:
                    supporting_observations = obs['observations']
                else:
                    supporting_observations = []
                try:
                    output.append({
                        'observation': obs['description'],
                        'evidence': obs['evidence'],
                        'hypotheses': [h.model_dump() for h in resp.hypotheses],
                        'supporting_observations': supporting_observations
                    })
                except Exception as e:
                    print(f"Error generating hypotheses for session {session_idx}: {e}\n resp: {resp}")
                    continue
            if self.limit == 5:
                save_file = f'../data/{self.fidx}/pipeline_outputs/session-{session_idx}/all_hypotheses.json'
                with open(save_file, "wb") as f:
                    f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
            else:
                save_file = f'../data/{self.fidx}/pipeline_outputs/session-{session_idx}/all_hypotheses_limit{self.limit}.json'
            with open(save_file, "wb") as f:
                f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
            await asyncio.sleep(10)
        # return resp
    
async def main(args):
    hypothesis_generator = HypothesisGenerator(model="gpt-5", fidx=args.fidx, num_sessions=args.num_sessions, limit=args.limit)
    await hypothesis_generator.generate_all_hypotheses()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HypothesisGenerator on transcripts.")
    parser.add_argument("--model", type=str, default="gpt-5", help="OpenAI model name.")
    parser.add_argument("--fidx", type=str, default="dora_pilot", help="Dataset index.")
    parser.add_argument("--num_sessions", type=int, default=6, help="Number of sessions.")
    parser.add_argument("--limit", type=int, default=5, help="Number of hypotheses to generate.")
    args = parser.parse_args()
    asyncio.run(main(args))


