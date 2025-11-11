import json 
import orjson
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils import call_gpt
from prompts.need_finder import ARMCHAIR_NEEDFINDER_PROMPT
import os 


load_dotenv()

summaries = {
    "interview":
    """
    Dora is a PhD student organizing think-aloud studies for a research project. She is using a Google Form to recruit participants.
    She is coordinating with her collaborators to schedule who is the interviewer. After assigning the interviewer, she creates 
    a Zoom meeting for the interview and sends a calendar invite plus email to both the interviewer and the participant.
    """
}
class ArmchairDesigner():
    def __init__(self, model, filename):
        self.model = model
        self.user = "Dora"
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.observations = json.load(open(filename))
        self.summary = summaries["interview"]

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)


    async def summarize_observations(self):
        input_prompt = f"Provide a 1 paragraph summary of what the user is doing based on the following observations: {self.observations}"
        resp = await self._guarded_call(self.client, input_prompt, self.model)
        self.summary = resp
        return resp

    async def generate_needs(self):
        prompt = ARMCHAIR_NEEDFINDER_PROMPT.format(user_name=self.user, input=self.summary)
        print(prompt)
        resp = await self._guarded_call(self.client, prompt, self.model)
        return resp

async def main():
    model = "gpt-5"
    filename = "/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/0_interview_gpt-5_20250918.json"
    armchair = ArmchairDesigner(model, filename)
    needs = await armchair.generate_needs()
    print(needs)
    save_file = "results/armchair/interview_armchair.json"
    with open(save_file, "wb") as f:
        f.write(orjson.dumps(needs, option=orjson.OPT_INDENT_2))
    return needs 

if __name__ == "__main__":
    asyncio.run(main())
    