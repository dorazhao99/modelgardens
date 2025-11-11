import argparse
from response_formats import (
    GoalResponse,
    PatternInductionResponse,
    PatternJudgeResponse,
    MotivationResponse,
    RubricResponse,
    EvaluationResponse,
    FeasibilityResponse,
    Pattern
)
from prompts import tool_spec, rubrics
from utils import call_gpt, format_needs, format_goals
from openai import AsyncOpenAI
import os, json, time
import asyncio
import orjson
from dotenv import load_dotenv
from typing import List
import pdb
import traceback
load_dotenv()


class RubricIterator:
    def __init__(self, model, params, user, context, tools):
        self.model = model
        self.params = params
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.context = context
        self.tools = tools
        self.fmt_goals = ""
        self.fmt_needs = ""
        self.fmt_rubric = ""
        self.user = user
        self.save_file = True


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

    async def generate_rubric(self):
        prompt = rubrics.PATTERN_JUDGEMENT_RUBRIC.format(
            goals=self.fmt_goals, needs=self.fmt_needs
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
            print(prompt)
            tasks.append(
                call_gpt(
                    self.client, prompt, self.model, resp_format=EvaluationResponse
                )
            )
        resp = await asyncio.gather(*tasks, return_exceptions=True)
        return resp


    async def generate_tools(self):
        prompt = tool_spec.PATTERN_INDUCTION_PROMPT.format(
            context=self.context,
            goals=self.fmt_goals,
            limit=5,
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
    
    async def single_iterator(self, rubric, rubric_type: str, num_iters: int = 3, tool_type: str = "cluster_gt"):
        iteration = 0
        rubric = rubric["metrics"]
        self.format_rubric(rubric)
        
        tools = self.tools
        output = {"0": tools}

        while iteration < num_iters:
            tasks = []
            for tool in tools:
                prompt = tool_spec.PATTERN_REFINEMENT_PROMPT_CRITERIA.format(design_pattern=tool, \
                    user_needs=self.fmt_needs, goals=self.fmt_goals, criteria=self.fmt_rubric, \
                    json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
                print(prompt)
                tasks.append(call_gpt(self.client, prompt, self.model, resp_format=Pattern))
            refined_tools = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            valid_refined_tools = []
            for idx, tool in enumerate(refined_tools):
                if isinstance(tool, Exception):
                    print(f"Error refining tool {idx}: {type(tool).__name__}: {tool}")
                    traceback.print_exception(type(tool), tool, tool.__traceback__)
                    # Keep the original tool if refinement failed
                    valid_refined_tools.append(tools[idx])
                else:
                    valid_refined_tools.append(tool)

            resps = await pipeline.evaluate_specs(valid_refined_tools)
            updated_tools, output_tools = [], []
            for idx, (new_tool, resp) in enumerate(zip(valid_refined_tools, resps)):
                # Check if resp is an exception
                if isinstance(resp, Exception):
                    print(f"Error evaluating tool {idx}: {type(resp).__name__}: {resp}")
                    traceback.print_exception(type(resp), resp, resp.__traceback__)
                    # Keep the original tool if evaluation failed
                    updated_tools.append(tools[idx])
                    output_tools.append(tools[idx])
                    continue
                try:
                    new_tool = new_tool.model_dump()
                except Exception as e:
                    print(f"Error dumping tool {idx}: {type(e).__name__}: {e}")
                    new_tool = new_tool
                if "evaluation" not in new_tool:
                    new_tool["evaluation"] = {}
                    new_tool["evaluation"][rubric_type] = {}
                score = pipeline.get_grade(rubric, resp)
                
                new_tool["evaluation"][rubric_type]["scores"] = resp.model_dump()
                new_tool["evaluation"][rubric_type]["total"] = score
                existing_score = tools[idx]['evaluation'][rubric_type]['total']
                output_tools.append(new_tool)
                if existing_score > score:
                    updated_tools.append(new_tool)
                else:
                    updated_tools.append(tools[idx])
            output[str(iteration + 1)] = output_tools
            iteration += 1
            tools = updated_tools
            if self.save_file:
                filename = f"../data/{self.fidx}/tool_eval/{self.setting}/iterated_tools/tool_{tool_type}_{rubric_type}.json"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
        return output
    
    async def alternating_iterator(self):
        return 
    
    async def grade_feasibility(self):
        tasks = []
        for tool in self.tools:
            prompt = rubrics.FEASIBLITY_RUBRIC.format(spec=tool)
            print(prompt)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=FeasibilityResponse))
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        output = []
        for tool, resp in zip(self.tools, resps):
            if resp.feasibility == "Not Feasible" or resp.feasibility == "Partially Feasible":
                prompt = rubrics.SPEC_ITERATOR.format(platform_constraints=rubrics.PLATFORM_CONSTRAINTS, \
                    original_spec=tool, \
                    feasibility_assessment=resp.model_dump(), \
                    json_schema=tool_spec.PATTERN_INDUCTION_JSON_SCHEMA)
                print(prompt)
                revised_tool = await call_gpt(self.client, prompt, self.model, resp_format=Pattern)
                output.append(revised_tool.model_dump())
            else:
                output.append(tool)
        for o in output:
            print(o)
        return resps
    
    def get_grade(self, rubric, resp):
        print(resp.scores, rubric)
        name2score = {metric.metric: metric.score for metric in resp.scores}
        name2weight = {metric["name"]: metric["weight"] for metric in rubric}
        print(name2score, name2weight)
        return sum([name2weight[metric['name']] * name2score[metric["name"]] for metric in rubric])

async def iterate_tools(pipeline: RubricIterator, fidx: str, setting: str, rubric_type: str = "both", tool_type: str = "cluster_gt"):
    rubric = json.load(open(f"../data/{fidx}/tool_eval/{setting}/rubrics/rubric_{rubric_type}.json", "r"))
    print(rubric)
    await pipeline.single_iterator(rubric, rubric_type="both")

async def grade_tools(model: str, fidx: str, setting: str, tool_type: str = "cluster_gt"):
    
    tools = json.load(open(f"../data/{fidx}/tool_eval/{setting}/tool_{tool_type}.json", "r"))
    tools = tools["tools_needs"]["patterns"]

    for rubric_type in ["need_only", "both"]:
        rubric = json.load(open(f"../data/{fidx}/tool_eval/{setting}/rubrics/rubric_{rubric_type}.json", "r"))
        rubric = rubric["metrics"]
        pipeline.format_rubric(rubric)
        resps = await pipeline.evaluate_specs(tools)
        for tool, resp in zip(tools, resps):
            if "evaluation" not in tool:
                tool["evaluation"] = {'need_only': {}, 'both': {}}
            tool["evaluation"][rubric_type]['scores'] = resp.model_dump()
            score = pipeline.get_grade(rubric, resp)
            tool["evaluation"][rubric_type]["total"] = score

    filename = f"../data/{fidx}/tool_eval/{setting}/graded_tools/tool_{tool_type}.json"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(orjson.dumps(tools, option=orjson.OPT_INDENT_2))
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--arg_type", type=str, required=True)
    parser.add_argument("--fidx", type=str, required=True)
    parser.add_argument("--timestep", type=str, required=True)
    parser.add_argument("--setting", type=str, required=True)
    args = parser.parse_args()
    model = args.model

    tool_data = json.load(open(f"../data/{args.fidx}/tool_eval/{args.setting}/graded_tools/tool_cluster_gt.json", "r"))
    filename = "cluster_gt"
    need_data = json.load(
        open(f"../data/{args.fidx}/pipeline_outputs/session-meta/{filename}.json", "r")
    )
    goals_file = f"../data/{args.fidx}/tool_eval/{args.setting}/goals.json"
    goal_output = json.load(open(goals_file, "r"))
    goals = goal_output["goals"]
    pipeline = RubricIterator(model=model, params={}, user="Dora", context="", tools = tool_data)
    pipeline.fidx = args.fidx
    pipeline.setting = args.setting
    pipeline.fmt_needs = format_needs(need_data)
    pipeline.fmt_goals = format_goals(goals)
    asyncio.run(pipeline.grade_feasibility())
    # asyncio.run(grade_tools(model, args.fidx, args.setting,  tool_type="cluster_gt"))
    # asyncio.run(iterate_tools(pipeline, args.fidx, args.setting, rubric_type="both", tool_type="cluster_gt"))