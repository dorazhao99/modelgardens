import argparse
from response_formats import (
    GoalResponse,
    PatternInductionResponse,
    PatternJudgeResponse,
    MotivationResponse,
    RubricResponse,
    EvaluationResponse,
)
from prompts import tool_spec, rubrics
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
        self.fmt_needs = ""
        self.fmt_rubric = ""
        self.user = user

    async def refine_tool(self, tool, scores, criteria):
        # prompt = tool_spec.PATTERN_REFINEMENT_PROMPT.format(
        #     design_pattern=tool,
        #     user_needs=self.fmt_needs,
        #     scores=scores,
        #     json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA,
        # )
        prompt = tool_spec.PATTERN_REFINEMENT_PROMPT_CRITERIA.format(
            design_pattern=tool,
            user_needs=self.fmt_needs,
            goals=self.fmt_goals,
            criteria=criteria,
            json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA,
        )
        print(prompt)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=PatternInductionResponse
        )
        return resp

    async def evaluate_spec(self, spec: str):
        prompt = rubrics.EVALUATION_PROMPT.format(
            evaluationMetrics=self.fmt_rubric, specification=spec
        )
        print(prompt)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=EvaluationResponse
        )
        return resp

    def format_goals(self, goals):
        try:
            self.fmt_goals = "\n".join([f"{i.goal}: {i.description}" for i in goals])
        except:
            self.fmt_goals = "\n".join(
                [f"{i['goal']}: {i['description']})\n" for i in goals]
            )

    def format_rubric(self, rubric):
        print(rubric)
        try:
            self.fmt_rubric = "\n".join(
                [
                    f"{i.name}: {i.description}\nCriteria:\n{'\n'.join([f"- {c}" for c in i.criteria])}"
                    for i in rubric
                ]
            )
        except:
            self.fmt_rubric = "\n".join(
                [
                    f"{i['name']}: {i['description']}\nCriteria:\n{'\n'.join([f"- {c}" for c in i['criteria']])}\n"
                    for i in rubric
                ]
            )
        print(self.fmt_rubric)

    def format_scores(self, scores, rubric):
        """
        Reformat scores to be:
        Metric: Name
        Score: Score
        Criteria: Criteria
        """
        formatted = []
        for score in scores:
            print(rubric, score['metric'])
            try:
                # Handle Pydantic model
                formatted.append(
                    f"Metric: {score.metric}\nScore: {score.score}\nCriteria: {"\n".join([f"- {c}" for c in rubric[score.metric]])}"
                )
            except AttributeError:
                # Handle dictionary
                criteria = "\n".join([f"- {c}" for c in rubric[score['metric']]])
                formatted.append(
                    f"Metric: {score['metric']}\nScore: {score['score']}\nCriteria: {criteria}"
                )
        return "\n\n".join(formatted)

    async def generate_rubric(self, prompt_type: str = "both"):
        if prompt_type == "need_only":
            prompt = rubrics.PATTERN_JUDGEMENT_RUBRIC_NEEDS.format(
                needs=self.fmt_needs, goals=self.fmt_goals, limit=5
            )
        else:
            prompt = rubrics.PATTERN_JUDGEMENT_RUBRIC.format(
                goals=self.fmt_goals, needs=self.fmt_needs, limit=5
            )
        print(prompt)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=RubricResponse
        )
        return resp

    async def evaluate_specs(self, specs: List[str]):
        tasks = []
        for spec in specs:
            prompt = rubrics.EVALUATION_PROMPT.format(
                evaluationMetrics=self.fmt_rubric, specification=spec
            )
            tasks.append(
                call_gpt(
                    self.client, prompt, self.model, resp_format=EvaluationResponse
                )
            )
        resp = await asyncio.gather(*tasks, return_exceptions=True)
        print(resp)
        return resp

    async def select_hypotheses(self, hypotheses):
        prompt = tool_spec.NEED_INDUCTION_PROMPT.format(
            context=self.context, goals=self.fmt_goals, motivations=hypotheses, limit=5
        )
        print(prompt)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=MotivationResponse
        )
        return resp

    async def generate_goals(self):
        prompt = tool_spec.GOAL_INDUCTION_PROMPT.format(context=self.context, limit=3)
        resp = await call_gpt(self.client, prompt, self.model, resp_format=GoalResponse)
        self.format_goals(resp.goals)
        return resp

    async def generate_tools(self):
        prompt = tool_spec.PATTERN_INDUCTION_PROMPT.format(
            context=self.context,
            goals=self.fmt_goals,
            limit=10,
            user=self.user,
            json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA,
        )
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=PatternInductionResponse
        )
        return resp

    async def generate_tools_needs(self, needs):
        prompt = tool_spec.PATTERN_INDUCTION_PROMPT_NEEDS.format(
            context=self.context,
            goals=self.fmt_goals,
            needs=needs,
            limit=5,
            user=self.user,
            json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA,
        )
        print(prompt)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=PatternInductionResponse
        )
        return resp

    async def judge_tools(self, tool, needs):
        prompt = tool_spec.PATTERN_JUDGE.format(design_pattern=tool, user_need=needs)
        resp = await call_gpt(
            self.client, prompt, self.model, resp_format=PatternJudgeResponse
        )
        return resp


async def evaluate(
    filename: str, model: str, fidx: str, timestep: str, is_annotated: int
):
    eval_file = json.load(open(filename, "r"))
    timestamp = time.strftime("%Y%m%d")
    file = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{fidx}/{timestep}.md"
    with open(file, "r") as f:
        transcription = [i for i in f.readlines()]
    context = "\n".join(transcription)
    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)

    for dk in ["tools", "tools_needs"]:
        tools = eval_file[dk]
        needs = eval_file["needs"]

        if is_annotated == 1:
            fmt_needs = "\n".join(
                [
                    f"Need: {i['need']} | Reasoning: {i['reasoning']}"
                    for i in needs
                    if i["real"] == 1
                ]
            )
        else:
            fmt_needs = "\n".join(
                [f"Need: {i['need']} | Reasoning: {i['reasoning']}" for i in needs]
            )
        print(fmt_needs)
        tasks = []
        for tool in tools["patterns"]:
            tasks.append(pipeline.judge_tools(tool=tool, needs=fmt_needs))
        resp = await asyncio.gather(*tasks)

        for idx, r in enumerate(resp):
            tools["patterns"][idx]["judge"] = r.response
            tools["patterns"][idx]["judge_reasoning"] = r.reasoning
        eval_file[dk] = tools
    with open(filename, "wb") as f:
        f.write(orjson.dumps(eval_file, option=orjson.OPT_INDENT_2))


async def iterate_rubric(
    model: str, fidx: str, setting: str, tool_path: str, timestep: str
):
    file = (
        f"../data/{fidx}/tool_eval/{setting}/processed_data/transcripts/{timestep}.md"
    )
    with open(file, "r") as f:
        transcription = [i for i in f.readlines()]
        transcription = "".join(transcription)
    file = f"../data/{fidx}/tool_eval/{setting}/processed_data/summaries/{timestep}.md"
    with open(file, "r") as f:
        summaries = [i for i in f.readlines()]
        summaries = "".join(summaries)
    context = f"Summary: {summaries}\n\nTranscription: {transcription}"

    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)

    # get needs
    filename = "cluster_gt"
    hypo_data = json.load(
        open(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}.json", "r")
    )
    fmt_motivations = "\n".join(
        [
            f"{idx + 1}. {i['name']}: {i['need']} {i['motivation']}"
            for idx, i in enumerate(hypo_data)
        ]
    )
    pipeline.fmt_needs = fmt_motivations


    # get goals
    goals_file = f"../data/{fidx}/tool_eval/{setting}/goals.json"
    goal_output = json.load(open(goals_file, "r"))
    goals = goal_output["goals"]
    pipeline.format_goals(goals)


    # get score
    iters, max_score = 0, 0

    metrics = json.load(open(f"../data/core_rubric.json", "r"))
    pipeline.format_rubric(metrics["metrics"])
    metric_weights = {metric["name"]: metric["weight"] for metric in metrics["metrics"]}
    metric_criteria = {metric["name"]: metric["criteria"] for metric in metrics["metrics"]}
    if os.path.exists(tool_path):
        tool_candidates = json.load(open(tool_path, "r"))
    else:
        return

    tool_candidates = tool_candidates["tools_needs"]["patterns"]
    max_score, best_idx = 0, 0
    candidate_scores = ""
    for tool in tool_candidates:
        scores = tool["evaluation_core"]["scores"]
        total = 0
        for score in scores:
            score_name = score["metric"]
            score_num = score["score"]
            total += metric_weights[score_name] * score_num
        if total > max_score:
            max_score = total
            # Exclude evaluation from best_tool
            best_tool = {k: v for k, v in tool.items() if k != "evaluation"}
            candidate_scores = scores
    info = {
            "iteration": 0,
            "spec": best_tool,
            "scores":candidate_scores,
            "total": max_score,
    }
    intermittent_refinement = [info]
    out_file = f"../data/{fidx}/tool_eval/{setting}/intermittent_refinement_core.json"

    while iters <= 3:
        fmt_scores = pipeline.format_scores(candidate_scores, metric_criteria)
        
        refined_tool = await pipeline.refine_tool(
            tool=best_tool, scores=fmt_scores, criteria=fmt_scores
        )
        scores = await pipeline.evaluate_spec(spec=refined_tool.patterns)
        total = 0
        for score in scores.scores:
            score_name, score_num = score.metric, score.score
            total += metric_weights[score_name] * score_num
        if total > max_score:
            max_score = total
            best_tool = {k: v for k, v in refined_tool.model_dump().items() if k != "evaluation"}
            candidate_scores = scores.scores
            best_idx = iters + 1
        info = {
            "iteration": iters + 1,
            "spec": refined_tool.model_dump(),
            "scores": scores.model_dump(),
            "total": total,
        }
        intermittent_refinement.append(info)
        iters += 1
        with open(out_file, "wb") as f:
            f.write(orjson.dumps(intermittent_refinement, option=orjson.OPT_INDENT_2))
        if max_score > 90:
            break 

    output = {
        "intermittent_refinement": intermittent_refinement,
        "best_tool": {
            "score": max_score,
            "iteration": best_idx
        }
    }
    with open(out_file, "wb") as f:
        f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
    #     iters += 1


async def gt_needs(model: str, fidx: str, setting: str, timestep: str):
    file = (
        f"../data/{fidx}/tool_eval/{setting}/processed_data/transcripts/{timestep}.md"
    )
    with open(file, "r") as f:
        transcription = [i for i in f.readlines()]
        transcription = "".join(transcription)
    # file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/{fidx}/{timestep}.md'
    file = f"../data/{fidx}/tool_eval/{setting}/processed_data/summaries/{timestep}.md"
    with open(file, "r") as f:
        summaries = [i for i in f.readlines()]
        summaries = "".join(summaries)
    context = f"Summary: {summaries}\n\nTranscription: {transcription}"

    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)
    goals_file = f"../data/{fidx}/tool_eval/{setting}/goals.json"
    if os.path.exists(goals_file):
        goal_output = json.load(open(goals_file, "r"))
        goals = goal_output["goals"]
        pipeline.format_goals(goals)
    else:
        resp = await pipeline.generate_goals()
        goal_output = resp.model_dump()
        goals = resp.goals
        with open(goals_file, "wb") as f:
            f.write(orjson.dumps(goal_output, option=orjson.OPT_INDENT_2))

    # # tools without needs
    tools_file = f"../data/{fidx}/tool_eval/{setting}/tools_noneeds.json"
    if not os.path.exists(tools_file):
        resp = await pipeline.generate_tools()
        tools = resp.patterns
        tools_output = resp.model_dump()
        with open(tools_file, "wb") as f:
            f.write(orjson.dumps(tools_output, option=orjson.OPT_INDENT_2))

    # hypotheses
    filename = "cluster_gt"
    hypo_data = json.load(
        open(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}.json", "r")
    )
    fmt_motivations = "\n".join(
        [
            f"{idx + 1}. {i['name']}: {i['need']} {i['motivation']}"
            for idx, i in enumerate(hypo_data)
        ]
    )
    pipeline.fmt_needs = fmt_motivations

    resp = await pipeline.generate_tools_needs(needs=fmt_motivations)
    tools_needs_output = resp.model_dump()

    output = {
        "tools_needs": tools_needs_output,
    }

    print(output)
    save_file = f"../data/{fidx}/tool_eval/{setting}/tool_{filename}.json"
    with open(save_file, 'wb') as f:
        f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
    
    for pt in ["need_only", "both"]:
        resp = await pipeline.generate_rubric(prompt_type=pt)
        rubric_output = resp.model_dump()
        with open(f"../data/{fidx}/tool_eval/{setting}/rubrics/rubric_{pt}.json", "wb") as f:
            f.write(orjson.dumps(rubric_output, option=orjson.OPT_INDENT_2))



    # # rubric_file = f"../data/{fidx}/tool_eval/{setting}/rubric_gt.json"
    # rubrics = [{"file": "../data/core_rubric.json", "name": "evaluation_core"}, \
    #     {"file": f"../data/{fidx}/tool_eval/{setting}/rubric_gt.json", "name": "evaluation"}]
    # rubric = {}
    # for rub in rubrics[:1]:
    #     rubric_file = rub["file"]
    #     rubric_name = rub["name"]
    #     if not os.path.exists(rubric_file):
    #         resp = await pipeline.generate_rubric()
    #         rubric_output = resp.model_dump()
    #         with open(rubric_file, "wb") as f:
    #             f.write(orjson.dumps(rubric_output, option=orjson.OPT_INDENT_2))
    #         pipeline.format_rubric(rubric_output["metrics"])
    #     else:
    #         rubric_output = json.load(open(rubric_file, "r"))
    #         for metric in rubric_output["metrics"]:
    #             rubric[metric["name"]] = metric
    #         pipeline.format_rubric(rubric_output["metrics"])

    #     # tools w needs
    #     tools_needs_file = f"../data/{fidx}/tool_eval/{setting}/tool_{filename}.json"
    #     with open(tools_needs_file, "r") as f:
    #         tools_needs = json.load(f)
    #     tools = tools_needs["tools_needs"]["patterns"]
    #     resps = await pipeline.evaluate_specs(tools)
    #     for idx, r in enumerate(resps):
    #         tools_needs["tools_needs"]["patterns"][idx][rubric_name] = r.model_dump()
    # with open(tools_needs_file, "wb") as f:
    #     f.write(orjson.dumps(tools_needs, option=orjson.OPT_INDENT_2))


async def main(
    model: str, fidx: str, setting: str, timestep: str, is_annotated: int, filename: str
):
    timestamp = time.strftime("%Y%m%d")

    # file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{fidx}/{timestep}.md'
    file = (
        f"../data/{fidx}/tool_eval/{setting}/processed_data/transcripts/{timestep}.md"
    )
    with open(file, "r") as f:
        transcription = [i for i in f.readlines()]
        transcription = "".join(transcription)
    # file = f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/{fidx}/{timestep}.md'
    file = f"../data/{fidx}/tool_eval/{setting}/processed_data/summaries/{timestep}.md"
    with open(file, "r") as f:
        summaries = [i for i in f.readlines()]
        summaries = "".join(summaries)
    context = f"Summary: {summaries}\n\nTranscription: {transcription}"

    pipeline = PoppinsPipeline(model=model, params={}, user="Dora", context=context)
    resp = await pipeline.generate_goals()
    goal_output = resp.model_dump()
    goals = resp.goals

    # # tools without needs
    resp = await pipeline.generate_tools()
    tools = resp.patterns
    tools_output = resp.model_dump()

    # hypotheses
    hypo_data = json.load(
        open(f"../data/{fidx}/pipeline_outputs/session-meta/{filename}", "r")
    )
    fmt_hypotheses = "\n".join(
        [
            f"{i + 1}. {h['name']}: {h['need']} {h['motivation']}"
            for i, h in enumerate(hypo_data)
        ]
    )
    resp = await pipeline.select_hypotheses(fmt_hypotheses)
    motivations = resp.model_dump()

    fmt_motivations = "\n".join(
        [
            f"{i.motivation}: {i.description}\n Design implications: {i.implications}"
            for i in resp.motivations
        ]
    )

    resp = await pipeline.generate_tools_needs(needs=fmt_motivations)
    tools_needs_output = resp.model_dump()

    output = {
        "goals": goal_output,
        "motivations": motivations,
        "tools": tools_output,
        "tools_needs": tools_needs_output,
    }

    print(output)
    save_file = f"../data/{fidx}/tool_eval/{setting}/tool_clustered-motivations.json"
    with open(save_file, "wb") as f:
        f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--arg_type", type=str, required=True)
    parser.add_argument("--fidx", type=str, required=True)
    parser.add_argument("--timestep", type=str, required=True)
    parser.add_argument("--is_annotated", type=int, required=True)
    parser.add_argument("--setting", type=str, required=True)
    args = parser.parse_args()
    model = args.model
    is_annotated = args.is_annotated
    asyncio.run(gt_needs(model, fidx=args.fidx, setting=args.setting, timestep=args.timestep))
    

    # asyncio.run(
    #     iterate_rubric(
    #         model,
    #         fidx=args.fidx,
    #         setting=args.setting,
    #         timestep=args.timestep,
    #         tool_path=f"../data/{args.fidx}/tool_eval/{args.setting}/tool_clustered-gt.json",
    #     )
    # )
    # asyncio.run(gt_needs(model, fidx=args.fidx, setting=args.setting, timestep=args.timestep))
    # if args.arg_type == "main":
    #     asyncio.run(main(model, fidx=args.fidx, setting=args.setting, timestep=args.timestep, is_annotated=is_annotated))
    # elif args.arg_type == "evaluate":
    #     filename = f'/Users/dorazhao/Documents/modelgardens/src/results/tool_eval/{args.fidx}_tools_gpt-5_20251007_{args.is_annotated}.json'
    #     asyncio.run(evaluate(filename, model, fidx=args.fidx, setting=args.setting, timestep=args.timestep, is_annotated=is_annotated))
    # elif args.arg_type == "gt_needs":
    #     asyncio.run(gt_needs(model, fidx=args.fidx, setting=args.setting, timestep=args.timestep))
    # else:
    #     raise ValueError(f"Invalid argument type: {args.arg_type}")
