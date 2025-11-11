from ImageProcessor import ImageProcessor
from prompts import screen, goals, implementer
import os
import json
import webbrowser
import asyncio 
import tkinter as tk
from openai import OpenAI, AsyncOpenAI
from google import genai
from response_formats import * 
from dotenv import load_dotenv
from utils import call_gpt

class ToolCreator():
    def __init__(self, workflow: str, file_directory: str, is_debug: bool):
        load_dotenv()
        self.is_debug = is_debug
        self.config = ''
        self.workflow = workflow
        self.client=genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.start_frame = 80
        self.max_frame = 0
        self.fp = 10 # how many frames to process
        self.can_process = True
        self.file_directory = file_directory
        # self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.async_oai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def process_goal(self, actions: str, is_new: bool, past: dict) -> str:
        if is_new:
            goal_prompt = goals.INITIAL_GOALS_PROMPT.format(actions=actions)
            goal_format = NewGoalData
        else:
            past_goal = past['goal']
            if 'tasks' in past:
                past_tasks = past['tasks']
            else:
                past_tasks = past['existing_tasks'].extend(past['new_tasks'])
            past_context = past['context']
            goal_prompt = goals.CONTINUING_GOALS_PROMPT.format(past_goal=past_goal, \
                                                                past_tasks=past_tasks, \
                                                                past_context=past_context,\
                                                                actions=actions)
            goal_format = ContinueGoalData

        resp = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=goal_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": goal_format,
            }
        )
        output=resp.text
        ### remove json markdown
        json_data = output.strip('` \n')
        if json_data.startswith('json'):
            json_data = json_data[4:]
        json.dump(json_data, open('transcripts/workflow_{}/{}_goals.json'.format(self.workflow, self.start_frame), 'w'))
        return output

    def generate_tools(self, info: dict, tool_info: dict, is_start: bool): 
        print('Generating Tools')
        task_context = ', '.join(info['context'])
        if is_start:
            tasks = info['tasks']
            fmt_tasks = ['- {}: {}'.format(i['task'], i['description']) for i in tasks]
            fmt_tasks = '\n'.join(fmt_tasks)
            tools_prompt = goals.ALTERNATIVE_TOOLS_PROMPT.format(tasks=fmt_tasks, task_context=task_context)
            # tools_prompt = goals.NEW_TOOLS_PROMPT.format(tasks=tasks, goal=goal, task_context=task_context)
        else:
            tasks = info['existing_tasks']
            tasks.extend(info['new_tasks'])
            
            fmt_tasks = ['- {}: {}'.format(i['task'], i['description']) for i in tasks]
            fmt_tasks = '\n'.join(fmt_tasks)

            if 'agents' in tool_info:
                tools = tool_info['agents']
            else:
                tools = tool_info['existing']
                tools.extend(info['new'])
            tools_prompt = goals.CONTINUING_ALTERNATIVE_TOOLS_PROMPT.format(current_tools=tools, \
                    tasks=fmt_tasks, task_context=task_context)
        print(tools_prompt)
        # resp = self.client.chat.completions.create(
        #     model="gpt-4.1",
        #     messages=[{"role": "user", "content": tools_prompt}],
        #     response_format={"type": "text"},
        # )
        resp = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=tools_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AgentList,
            }
        )
        resp=resp.text
        # resp = resp.choices[0].message.content 
        json.dump(resp, open('transcripts/workflow_{}/{}_tools.json'.format(self.workflow, self.start_frame), 'w'))
        return resp
    
    async def check_tool(self, tool_list: list[str], new_tools: list[dict], user_actions: str):
        if len(tool_list) > 0:
            existing_tools = '\n'.join(tool_list)
        else: 
            existing_tools = 'No existing tools.'
        tasks = []
        for tool in new_tools:
            new_tool = '{}: {}'.format(tool['name'], tool['purpose'])
            similar_prompt = implementer.SIMILAR_PROMPT.format(existing_tools=existing_tools, new_tool=new_tool, user_actions=user_actions)
            task = call_gpt(client=self.async_oai_client, prompt=similar_prompt, model='gpt-4o', resp_format=Exists)
            tasks.append(task)
        print(len(tasks))
        resp = await asyncio.gather(*tasks)
        return resp


    def implement_tools(self, tool: list[dict], actions=str):
        implement_prompt = implementer.IMPLEMENT_PROMPT.format(description=tool['purpose'], \
                                                                implementation=tool['implementation'], \
                                                                name=tool['name'],
                                                                actions=actions, \
                                                                config=self.config)
        print(implement_prompt)
        resp = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=implement_prompt,
        )
        output=resp.text

        ## Critique the code 
        critique_prompt = implementer.CRITIQUE_PROMPT.format(description=tool['purpose'], html_code=resp, config=self.config)
        resp = self.client.models.generate_content(
            model="gemini-2.5-pro",
            contents=critique_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Critique,
            }
        )
        output=json.loads(resp.text)
        print(output)
        critique = output['critique']
        print(critique)
        code = output['code']
        code = code.strip('` \n')
        if code.startswith('html'):
            code = code[4:]

        os.makedirs(f'tools/workflow_{self.workflow}', exist_ok=True)
        file_path="/Users/dorazhao/Documents/modelgardens/tools/workflow_{}/{}.html".format(self.workflow, tool['name'])
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return file_path

if __name__ == '__main__':
    pipeline = ToolCreator('11', 'sampled_frames/workflow_11/', True)
    # params = {
    #         'feasibility': 0.9,
    #         'utility': 1.1
    # }
    # judgements = asyncio.run(pipeline.check_tool(['Music Critic: critiques the song selections and tells you why they are basic'], \
    #                                              [{'name': 'Audio Remixer', 'purpose': 'creates audio remixes'}, \
    #                                               {'name': 'Song Suggestor', 'purpose': 'finds similar songs the user might not have explored'}
    #                                             ], \
    #                                                 ['The user is on Spotify creating a new playlist to impress their friends']))
    # print(judgements)
    # names = []
    # processed_goals = json.load(open('transcripts/workflow_{}/{}_goals.json'.format('2', '20'), 'r'))
    # task_info = json.loads(processed_goals)
    # print(task_info)
    # tool_info = json.load(open('transcripts/workflow_{}/{}_tools.json'.format('2', '10'), 'r'))
    # tool_info = json.loads(tool_info)
    # pipeline.generate_tools(task_info, tool_info, False)
    # tool = json.loads(json.load(open('transcripts/workflow_1/5_tools.json')))['agents'][4]
    # with open('transcripts/workflow_1/{}.md'.format(5), 'r') as f:
    #     actions = [i.strip() for i in f.readlines()]
    # pipeline.implement_tools(tool=tool, actions=actions)


    # pipeline.implement_tools(tool: action:)
    asyncio.run(pipeline.process_actions())

    ## Initial setup 
    # info = json.loads(json.load(open('transcripts/workflow_1/10_goals.json', 'r')))
    # print(info)
    # pipeline.generate_tools(info, is_start=True, fname='10')


    ## Updating goals after initial
    # is_implemented = set([])
    # for fname in range(10, 15):
    #     tool_info = json.load(open('transcripts/workflow_1/{}_tools.json'.format(fname)))
    #     try:
    #         tool_info = json.loads(tool_info)
    #     except:
    #         print(tool_info)
    #     for agent in tool_info['agents']:
    #         name = agent['name']
    #         if name not in is_implemented:
    #             utility = int(agent['utility'])
    #             feasibility = int(agent['feasibility'])
    #             if utility > 8 and feasibility > 8: 
    #                 print(agent)
    #                 is_implemented.add(name)
    #         print(is_implemented)
                            



    # info = json.loads(json.load(open('transcripts/workflow_{}/{}_goals.json'.format('1', 10))))
    # goal = info['goal']
    # task_context = info['context']
    # tasks = info['tasks']
    # print(goals.ALTERNATIVE_TOOLS_PROMPT.format(tasks=tasks, goal=goal, task_context=task_context))
    # past = {}
    # for fname in range(12,20):
    #     with open('transcripts/workflow_1/{}_summary.md'.format(fname), 'r') as f:
    #         summary = [i.strip() for i in f.readlines()]
    #         if fname == 10: is_new = True 
    #         else: 
    #             is_new = False
    #             past = json.loads(json.load(open('transcripts/workflow_{}/{}_goals.json'.format('1', fname - 1))))
    #         processed_goals = pipeline.process_goal(actions='\n'.join(summary), fname=fname, is_new=False, past=past)
    #         print(processed_goals)
    #         task_info = json.loads(processed_goals)
    #         print(task_info)
    #         tool_info = json.loads(json.load(open('transcripts/workflow_1/{}_tools.json'.format(fname - 1))))
    #         pipeline.generate_tools(task_info, tool_info=tool_info, is_start=False, fname=fname)
    

    # # with open('transcripts/workflow_1   /10.md', 'r') as f:
    # #     actions = [i.strip() for i in f.readlines()]
    # summary = '\n'.join(summary)
    # data = json.loads(json.load(open('transcripts/workflow_1/10_goals.json', 'r')))
    # responses = asyncio.run(pipeline.generate_tools(data['goals'], summary))
    # print(responses)
    # tools = json.load(open('transcripts/workflow_1/10_tools.json', 'r'))
    # updated_tools = []
    # for tool_list in tools:
    #     tool_list = json.loads(tool_list)
    #     for tool in tool_list['agents']:
    #         score = params['feasibility'] * int(tool['feasibility']) + params['utility'] * int(tool['utility'])
    #         tool['score'] = score
    #         updated_tools.append(tool)
    # sorted_tools = sorted(updated_tools, key=lambda x: x["score"])[-3:]
    # print(sorted_tools)
    # implementations = asyncio.run(pipeline.implement_tools(sorted_tools))
    # for idx, implementation in enumerate(implementations):
    #     name = updated_tools[idx]['name'].lower().replace(' ', '-')
    #     file_path="/Users/dorazhao/Documents/modelgardens/tools/workflow_{}/{}.html".format(pipeline.workflow, name)
    #     with open(file_path, "w", encoding="utf-8") as f:
    #         f.write(implementation)
    #     webbrowser.open('file://' + os.path.realpath(file_path))




