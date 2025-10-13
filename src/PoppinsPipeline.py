import argparse
from response_formats import GoalResponse, PatternInductionResponse, PatternJudgeResponse
from prompts import tool_spec
from utils import call_gpt
from openai import AsyncOpenAI
import os, json, time
import asyncio
import orjson
from dotenv import load_dotenv
from typing import List

load_dotenv()

class PoppinsPipeline:
    def __init__(self, model, params, user, context):
        self.model = model
        self.params = params
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.context = context
        self.fmt_goals = ""
        self.user = user

    def format_goals(self, goals):
        self.fmt_goals = '\n'.join([f"{i.goal}: {i.description}" for i in goals])
    async def generate_goals(self):
        prompt = tool_spec.GOAL_INDUCTION_PROMPT.format(context=self.context, limit=3)
        resp = await call_gpt(self.client, prompt, self.model, resp_format=GoalResponse)

        return resp

    async def generate_tools(self):
        prompt = tool_spec.PATTERN_INDUCTION_PROMPT.format(context=self.context, \
            goals=self.fmt_goals, limit=10, user=self.user, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
        resp = await call_gpt(self.client, prompt, self.model, resp_format=PatternInductionResponse)
        return resp

    async def generate_tools_needs(self, needs):
        prompt = tool_spec.PATTERN_INDUCTION_PROMPT_NEEDS.format(context=self.context, goals=self.fmt_goals, needs=needs, \
            limit=10, user=self.user, json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
        resp = await call_gpt(self.client, prompt, self.model, resp_format=PatternInductionResponse)
        return resp

    async def judge_tools(self, tool, needs):
        prompt = tool_spec.PATTERN_JUDGE.format(design_pattern=tool, user_need=needs)
        resp = await call_gpt(self.client, prompt, self.model, resp_format=PatternJudgeResponse)
        return resp


async def evaluate(filename: str, model: str, fidx: str, timestep: str, is_annotated: int):
    eval_file = json.load(open(filename, 'r'))

    timestamp = time.strftime("%Y%m%d")
    file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{fidx}/{timestep}.md'
    with open(file, 'r') as f:
        transcription = [i for i in f.readlines()]
    context = '\n'.join(transcription)
    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)

    for dk in ['tools', 'tools_needs']:
        tools = eval_file[dk]
        needs = eval_file['needs'] 

        if is_annotated == 1:
            fmt_needs = '\n'.join([f"Need: {i['need']} | Reasoning: {i['reasoning']}" for i in needs if i['real'] == 1])
        else:   
            fmt_needs = '\n'.join([f"Need: {i['need']} | Reasoning: {i['reasoning']}" for i in needs])
        print(fmt_needs)
        tasks = []
        for tool in tools['patterns']:
            tasks.append(pipeline.judge_tools(tool=tool, needs=fmt_needs))
        resp = await asyncio.gather(*tasks)

        for idx, r in enumerate(resp):
            tools['patterns'][idx]['judge'] = r.response
            tools['patterns'][idx]['judge_reasoning'] = r.reasoning
        eval_file[dk] = tools
    with open(filename, 'wb') as f:
        f.write(orjson.dumps(eval_file, option=orjson.OPT_INDENT_2))

async def main(model: str, fidx: str, timestep: str, is_annotated: int):
    timestamp = time.strftime("%Y%m%d")

    file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{fidx}/{timestep}.md'
    with open(file, 'r') as f:
        transcription = [i for i in f.readlines()]
    file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/{fidx}/{timestep}.md'
    with open(file, 'r') as f:
        summaries = [i for i in f.readlines()]

    context = ''

    for s, t in zip(summaries, transcription):
        context += f'\n\nSummary: {s}\n\nTranscription: {t}'

    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)
    resp = await pipeline.generate_goals()
    goal_output = resp.model_dump()
    goals = resp.goals 

    # tools without needs
    resp = await pipeline.generate_tools()
    tools = resp.patterns
    tools_output = resp.model_dump()
    print(tools)

    # needs 
    needs = json.load(open(f'/Users/dorazhao/Documents/modelgardens/src/results/needs/{fidx}_o4-mini_20251007_tooleval_o4-mini.json', 'r'))
    if is_annotated == 1:
        fmt_needs = '\n'.join([f"Need: {i['need']} | Reasoning: {i['reasoning']} | Importance: {i['importance']}" for i in needs if i['real'] == 1])

    else:
        fmt_needs = '\n'.join([f"Need: {i['need']} | Reasoning: {i['reasoning']} | Importance: {i['importance']}" for i in needs])
    print(fmt_needs)
    # tools with needs 
    resp = await pipeline.generate_tools_needs(needs=fmt_needs)
    tools_needs = resp.patterns
    tools_needs_output = resp.model_dump()
    print(tools_needs)

    output = {
        "goals": goal_output,
        "tools": tools_output,
        "tools_needs": tools_needs_output,
        "needs": needs
    }

    print(output)
    with open(f'results/tool_eval/{fidx}_tools_{model}_{timestamp}_{is_annotated}.json', 'wb') as f:
        f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--arg_type", type=str, required=True)
    parser.add_argument("--fidx", type=str, required=True)
    parser.add_argument("--timestep", type=str, required=True)
    parser.add_argument("--is_annotated", type=int, required=True)
    args = parser.parse_args()
    model = args.model
    is_annotated = args.is_annotated
    if args.arg_type == "main":
        asyncio.run(main(model, args.fidx, args.timestep, is_annotated))
    elif args.arg_type == "evaluate":
        filename = f'/Users/dorazhao/Documents/modelgardens/src/results/tool_eval/{args.fidx}_tools_gpt-5_20251007_{args.is_annotated}.json'
        asyncio.run(evaluate(filename, model, args.fidx, args.timestep, is_annotated))
    else:
        raise ValueError(f"Invalid argument type: {args.arg_type}")
