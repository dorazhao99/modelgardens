
from prompts import insights
from utils import call_anthropic, parse_model_json
import os
import json
import orjson
import asyncio
from anthropic import AsyncAnthropic
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

## GLOBAL VARIABLES
anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_KEY"))
claude_model = "claude-sonnet-4-5-20250929"
fidx = "dora_pilot"

async def per_session_insights(actions, feelings, session_id: str, limit: int = 3, user_name: str = "Dora", is_save: bool = False) -> List[Dict]:
    prompt = insights.INSIGHT_PROMPT.format(actions=actions, feelings=feelings, limit=limit, user_name=user_name)
    print(prompt)
    resp = await call_anthropic(anthropic_client, claude_model, prompt)
    insight_prompt = insights.INSIGHT_JSON_FORMATTING_PROMPT.format(insights=resp, format=insights.INSIGHT_FORMAT)
    insight_resp = await call_anthropic(anthropic_client, claude_model, insight_prompt)
    structured_insights = parse_model_json(insight_resp)
    if is_save:
        with open(f"../data/{fidx}/pipeline_outputs/session-{session_id}/insights.json", "wb") as f:
            f.write(orjson.dumps(structured_insights, option=orjson.OPT_INDENT_2))
    return structured_insights

async def merge_insights(sessions: List[str], user_name: str = "Dora", is_save: bool = False) -> List[Dict]:
    all_insights = []
    output = {}
    for session_id in sessions:
        data = json.load(open(f"../data/{fidx}/pipeline_outputs/session-{session_id}/insights.json"))
        for idx, insight in enumerate(data['insights']):
            sid = f"{session_id}-{idx}"
            fmt_insight = f"ID {sid} | {insight['title']}: {insight['insight']}\nContext Insight Applies: {insight['context']}"
            all_insights.append(fmt_insight)
            output[sid] = insight
    fmt_all = "\n".join(all_insights)
    print(fmt_all)
    merge_prompt = insights.INSIGHT_SYNTHESIZER_PROMPT.format(input=fmt_all, user_name=user_name, session_num=len(sessions))
    print(merge_prompt)
    resp = await call_anthropic(anthropic_client, claude_model, merge_prompt)
    structured_resp = parse_model_json(resp)
    if is_save:
        with open(f"../data/{fidx}/pipeline_outputs/session-meta/insights.json", "wb") as f:
            f.write(orjson.dumps(structured_resp, option=orjson.OPT_INDENT_2))
    return structured_resp
    
async def main():
    for session_id in ["0", "2"]:
        data = json.load(open(f"../data/{fidx}/pipeline_outputs/session-{session_id}/observations_feelings_gpt-4.1_conservative.json"))
        actions, feelings = [], []
        for d in data:
            actions.append(data[d]['evidence'][0])
            feelings.append(data[d]['description'])
        actions = "\n".join(actions)
        feelings = "\n".join(feelings)
        await per_session_insights(actions, feelings, session_id=session_id, is_save=True)

async def merge_all():
    sessions = ["0", "2"]
    await merge_insights(sessions)

if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(merge_all())