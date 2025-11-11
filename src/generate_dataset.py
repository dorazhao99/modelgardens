from utils import call_gpt
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from prompts import dataset_generation
from response_formats import DatasetGenerationResponse
import asyncio
load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_dataset(needs):
    tasks = []
    for need in needs:
        prompt = dataset_generation.OBSERVATION_GENERATOR_PROMPT.format(need=need)
        tasks.append(call_gpt(client, prompt, "gpt-4o", resp_format=DatasetGenerationResponse))
    resp = await asyncio.gather(*tasks)
    for need, resp in zip(needs, resp):
        print(need)
        for observation in resp.observations:
            print(observation)
    return resp


if __name__ == "__main__":
    needs = [
        "User needs better work-life division",
        "User needs to feel confident standing up for their opinion",
        "User needs to stay focused on their task instead of getting distracted.",
        "User needs a way to manage their anxiety in high-stakes situations",
        "User needs help prioritizing their schedule to reduce procrastination",
        "User needs to quickly and confidently compare options without leaving her comfort zone",
        "User needs to get validation from others when making an important decision",
        "User needs safe spaces to share vulnerable feelings.",
        "User needs clarity about what truly matters when faced with competing demands.",
        "User needs confidence when stepping into leadership roles.",
        "User needs to experience a sense of progress even when results are not immediate.",
        "User needs to express creativity without fear of judgment.",
        "User needs to maintain joy and playfulness in daily routines.",
        "User needs to stay grounded when external pressures feel overwhelming.",
        "User needs to feel respected when setting personal boundaries.",
        "User needs to let go of perfectionism in their work."
    ]
    
    asyncio.run(generate_dataset(needs))