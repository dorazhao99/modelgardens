from prompts import insights as insights_prompts
from utils import call_gpt, call_anthropic, parse_llm_json_response
from anthropic import Anthropic
import os
import orjson
import json
import asyncio 
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm import tqdm

load_dotenv()

class Insights():
    def __init__(self, fidx: str, model: str, index: str, user: str, save_file: str, prose_insights: dict = None, user_insights: dict = None):
        self.model = model
        self.claude_model = "claude-sonnet-4-5-20250929"
        self.fidx = fidx
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.index = index
        self.user = user
        self.save_file = save_file
        self.actions = []
        self.feelings = []
        if user_insights is not None:
            self.user_insights = user_insights
        else:
            self.user_insights = {}
        if prose_insights is not None:
            self.prose_insights = prose_insights    
        else:
            self.prose_insights = {}

    def _save_file(self, save_type: str):
        if save_type == "support":
            save_file = self.save_file
        else:
            save_file = self.save_file.replace(".json", "_prose.json")
        with open(save_file, "wb") as f:
            f.write(orjson.dumps(self.prose_insights if save_type == "prose" else self.user_insights, option=orjson.OPT_INDENT_2))

    def _set_actions_feelings(self, observations: list[dict], include_confidence: bool = False):
        actions, feelings, confidences = [], [], []

        for d in observations:
            feelings.append(observations[d]['description'])
            actions.append(observations[d]['evidence'][0])
            confidences.append(observations[d]['confidence'])

        if include_confidence:
            self.actions = "\n".join([f"- {action}" for action, confidence in zip(actions, confidences)])
            self.feelings = "\n".join([f"- {feeling} (Confidence: {confidence})" for feeling, confidence in zip(feelings, confidences)])
        else:
            self.actions = "\n".join([f"- {action}" for action in actions])
            self.feelings = "\n".join([f"- {feeling}" for feeling in feelings])   
        return self.actions, self.feelings

    async def _reformat_insight(self, insights: str):
        prompt = insights_prompts.INSIGHT_JSON_FORMATTING_PROMPT.format(insights=insights)
        print(prompt)
        response = await call_gpt(self.client, prompt, self.model, resp_format=insights_prompts.Insights)
        return response

    async def get_prose_insights(self, observations: list[dict], interview: str = None):
        self._set_actions_feelings(observations)
        if interview is not None:
            prompt = insights_prompts.INSIGHT_PROMPT_INTERVIEW.format(user_name=self.user, limit=5, actions=self.actions, feelings=self.feelings, what_i_say=interview)
            print(prompt)
        else:
            prompt = insights_prompts.INSIGHT_PROMPT.format(user_name=self.user, limit=5, actions=self.actions, feelings=self.feelings)
        response = call_anthropic(self.anthropic_client, prompt, self.claude_model)
        reformat_response = await self._reformat_insight(response)
        self.prose_insights[str(self.index)] = {
            "raw": response,
            "formatted": [{"title": it.title, "insight": it.insight} for it in reformat_response.insights]
        }
        print(self.prose_insights[str(self.index)])
        self._save_file("prose")
        return reformat_response
    
    async def score_insights(self, insights, evidence, idx):
        tasks = []
        actions, feelings = self._set_actions_feelings(evidence, include_confidence=True)
        print(actions)
        print(feelings)
        if "insights" in insights:
            insights = insights["insights"]
        else:
            insights = insights

        for insight in insights:
            fmt_insight = f"{insight['title']}: {insight['insight']}"
            prompt = insights_prompts.INSIGHT_SUPPORT_PROMPT.format(insight=fmt_insight, actions=actions, feelings=feelings, user_name=self.user)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=insights_prompts.InsightSupportResponse))
       
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        new_output = []
        for insight, response in zip(insights, responses):
            if "confidence" not in insight:
                insight["confidence"] = {}
            insight["confidence"][str(idx)] = response.model_dump()
            new_output.append(insight)
        output = {"insights": new_output}
        with open(f"../data/{self.fidx}/pipeline_outputs/session-meta/insights_prompt_support.json", "wb") as f:
            f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
        return output
        

    async def support_insights(self):
        if str(self.index) not in self.user_insights:
            self.user_insights[str(self.index)] = {}
        insights = self.prose_insights[str(self.index)]['formatted']
        tasks = []
        for insight in insights:
            fmt_insight = f"{insight['title']}: {insight['insight']}"
            prompt = insights_prompts.INSIGHT_SUPPORT_PROMPT.format(insight=fmt_insight, actions=self.actions, feelings=self.feelings, user_name=self.user)
            tasks.append(call_gpt(self.client, prompt, self.model, resp_format=insights_prompts.InsightSupportResponse))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, response in enumerate(responses):
            self.user_insights[str(self.index)][str(idx)] = {
                "insight": insights[idx],
                "support": response.model_dump()
            }
        self._save_file("support")
        
    def _format_insight(self, insight: dict, iid: str = None):
        if iid is not None:
            overview = [f"INSIGHT #{iid}: {insight['insight']['title']}: {insight['insight']['insight']}"]
        else:
            overview = [f"INSIGHT: {insight['insight']['title']}: {insight['insight']['insight']}"]
        overview.append(f"EVIDENCE: {" ".join(insight['support']['evidence'])}")
        overview.append(f"CONFIDENCE: {insight['support']['confidence']}")
        overview.append(f"CONTEXT: {insight['support']['context']}")
        return "\n".join(overview)
    
    async def refine_insights(self, new_insights: list[dict]):
        max_id = max(int(k) for k in self.user_insights.keys()) + 1

        for nid in tqdm(new_insights):
            new_insight = new_insights[nid]
           
            existing_insights = [] 
            for i in self.user_insights:
                if "is_deleted" not in self.user_insights[i] or not self.user_insights[i]["is_deleted"]:
                    existing_insights.append(f"ID: {i} | {self._format_insight(self.user_insights[i])}")
            print("Existing insights", len(existing_insights))
            existing_insights = "\n\n".join(existing_insights)

            insight = self._format_insight(new_insight)
            prompt = insights_prompts.FIND_SIMILAR_INSIGHTS_PROMPT.format(source_insight=insight, target_insights=existing_insights)
        
            response = await call_gpt(self.client, prompt, self.model, resp_format=insights_prompts.ClassifierMerge)
            print(response)

           
            to_remove, response_group = set([]), []
            label, target = response.label, response.target

            for t in target:
                response_group.append(self._format_insight(self.user_insights[str(t)], iid=t))
            response_group = "\n\n".join(response_group)
            
            # Add new insight to dictionary for record
            original_id = str(max_id)
            max_id += 1
            self.user_insights[original_id] = new_insight

            # Handle identicial, similar, or different insights
            if label == "IDENTICAL":
                identical_prompt = insights_prompts.HANDLE_IDENTICAL_PROMPT.format(source_insight=insight, target_insights=response_group)
                identical_insight = call_anthropic(self.anthropic_client, identical_prompt, self.claude_model)
                # print("Identical")
                # print(identical_insight)
                try:
                    identical_insight = parse_llm_json_response(identical_insight, insights_prompts.RefinedInsightResponse)
                except Exception as e:
                    print("Unable to parse output", e)
                    continue
                # remove identical insights from self.insights 
                for i in target:
                    to_remove.add(i)
                # add new insights to self.insights
                try:
                    self.user_insights[str(max_id)] = identical_insight.model_dump()
                except:
                    self.user_insights[str(max_id)] = identical_insight
                self.user_insights[str(max_id)]["merged"] = [str(t) for t in target]
                self.user_insights[str(max_id)]["merged"].append(str(original_id))
                self.user_insights[original_id]["is_deleted"] = True
                max_id += 1
            elif label == "SIMILAR":
                similar_prompt = insights_prompts.HANDLE_SIMILAR_PROMPT.format(source_insight=insight, target_insights=response_group)
                similar_insights = call_anthropic(self.anthropic_client, similar_prompt, self.claude_model)
                # remove similar insights from self.insights 
                # print("Similar")
                try:
                    similar_insights = parse_llm_json_response(similar_insights, insights_prompts.SimilarInsightsResponse)
                except Exception as e:
                    print("Unable to parse output", e)
                    continue
                # print(similar_insights)

                similar_insights = similar_insights.insights

                for i in target:
                    to_remove.add(i)
                
                for i in similar_insights:
                    try:
                        self.user_insights[str(max_id)] = i.model_dump()
                    except:
                        self.user_insights[str(max_id)] = i
                    self.user_insights[str(max_id)]["merged"] = [str(t) for t in target]
                    self.user_insights[str(max_id)]["merged"].append(str(original_id))
                    self.user_insights[original_id]["is_deleted"] = True
                    max_id += 1
            else:
                continue
            for iid in to_remove:
                self.user_insights[str(iid)]["is_deleted"] = True
            self._save_file("support")

def combine_insights(): 
    prompt =  ""
                
async def merge_insights():
    user_insights = json.load(open("../data/mjr_pilot/pipeline_outputs/session-1/insights.json", "r"))
    insight = Insights("gpt-5", 0, "Michael Ryan", "../data/msl_pilot/pipeline_outputs/session-0/insight_top3_iter.json", user_insights=user_insights["1"])
    for i in ["2", "3", "4"]:
        new_insights = json.load(open(f"../data/msl_pilot/pipeline_outputs/session-{i}/insights.json", "r"))
        new_insights = new_insights[i]
        await insight.refine_insights(new_insights)
    # user_insights = json.load(open("../data/dora_pilot/pipeline_outputs/session-0/insights.json", "r"))
    # insight = Insights("gpt-5", 0, "Dora", "../data/dora_pilot/pipeline_outputs/session-0/insight_top3_iter.json", user_insights=user_insights["0"])
    # for i in ["2", "3", "4", "5"]:
    #     new_insights = json.load(open(f"../data/dora_pilot/pipeline_outputs/session-{i}/insights.json", "r"))
    #     new_insights = new_insights[i]
    #     await insight.refine_insights(new_insights)

async def score_insights():
    insight_obj = Insights(model="gpt-5", index=0, fidx="dora_pilot", user="Dora", save_file="../data/dora_pilot/pipeline_outputs/session-0/insights.json")
    insights = json.load(open("../data/dora_pilot/pipeline_outputs/session-meta/insights_prompt.json", "r"))
    for idx in ["0", "2", "3", "4", "5"]:
        data = json.load(open(f"../data/dora_pilot/pipeline_outputs/session-{idx}/observations_feelings_gpt-4.1_conservative.json", "r"))
        insights = await insight_obj.score_insights(insights, data, idx)
        print(insights)

async def main():
    for i in [2]:
        insight = Insights(model="gpt-5", index=i, fidx="dora_pilot", user="Dora Zhao", save_file=f"../data/dora_pilot/pipeline_outputs/session-{i}/insights_interview.json")
        data = json.load(open(f"../data/dora_pilot/pipeline_outputs/session-{i}/observations_feelings_gpt-4.1_conservative.json", "r"))
        # WHAT_I_SAY = """
        # I saw an email about a journalist who is interested in featuring our research, and I want to promote my work more since I think that's good for visibility / good for my career but since the paper is under submission I don't want to get into any trouble since HCI venues can be
        # kind of weird about that stuff. But also he wasn't from a super big outlet that I knew, so I needed to legit check him first since I have 
        # gotten emails from randos about press that I don't follow up on. 

        # I also saw an email about scheduling interviews for Apple for my final round to get a summer internship.
        # I really really want to intern this summer and wanted to make sure I find a time on my schedule without overlaps and that gave me enough
        # time to prep. 

        # Then because I had a 1-1 with Alexandra right after since she was speaking at the HCI seminar, 
        # I wanted to check out her profile to make sure i had stuff to talk about otherwise it would be kind of awkward. 

        # Just had my advisor meeting in the morning and we had talked about evaluating hypotheses, so I wanted to update that in my code.
        # They also asked me about Omar's IRB since I could use his for my user study so wanted to confirm that.

        # I was trying to give helpful advice to Duke about the fellowship application but didn't feel super qualified.
        # I thought sharing my essays was honestly the most useful since there aren't a lot of examples online.
        # I also wanted to compare what was different between my essays that did not get me accepted and the essays
        # that did so I thought ChatGPT could be useful.

        # I was taking notes during the talk since it helps me pay attention, but lowkey I was getting bored during parts of it and I
        # needed to text my boyfriend about our plans this weekend to go to Napa for a concert and then Fleet Week. The talk topic 
        # was relevant to me since I work in Responsible AI so I was really trying to pay attention and take notes.

        # I went to class and we were doing a tutorial on Tidyverse. I have used R but never Tidyverse so I needed to follow the tutorial although 
        # I already did the problem set for the week. The rest of the class had some technical difficulties so I finished the tutorial earlier 
        # and then just did my own stuff during class time. 

        # I went to Lucy and Terry's talk. I wanted to take notes since they are definitely big names in the field and I wanted to learn from them. I was tired though 
        # from the day because I had like back-to-back-to-back meetings and my brain was kind of fried and I needed to go to Michael's book event then drive up to SF that night.
        # """
        # WHAT_I_SAY = """
        # I'm working on converting Omar's gum script into just a screen recorder. I want to collect some data from myself, Michelle, and Michael, based on feedback I received from my advisors during our meeting. The gum code is pretty complex, with a lot of asynchronous processing, and I didn’t feel it was worth the time to fully untangle it right now—my goal is just to get the recording working quickly, so I did some trial-and-error debugging and made the necessary quick fixes. I pushed the changes to GitHub, tested the script, and then sent the code to Michelle. I also shared it with Omar, though I doubt he’ll use it since he has his own system.

        # After that, I remembered I needed to do my CHI reviews. Every time I do reviews, I get a bit nervous about what a good review should look like. I looked up some guidelines that people have posted before starting. The first paper I had to review was about understanding fortune telling with LLMs. As I was reading it, I took notes and considered what thoughts and feedback I wanted to include.

        # One thing that stood out to me was that their classifier accuracy seemed suspiciously high—over 90%—which is unusual, especially using a BERT model. I don’t have deep expertise in this particular area, but my general ML experience made me question the results. Since it’s a review, I used ChatGPT to sanity-check some of my thoughts. Honestly, I didn’t think the paper was great; it wasn’t very rigorous and I didn’t feel like I learned much from it.

        # Because the paper dealt with fortune telling in Chinese culture, I looked up other articles to make sure my hunches were well-founded, given that I don’t have direct expertise in that subject. I dug into some external literature before finalizing my review, then filled everything out on PCS.

        # At one point, I pulled up my own previous reviews on PCS to remind myself of the expected length and style—that helped me confirm I was on the right track.

        # Finally, I worked on the HCLLM paper. I needed to do some literature searching to support the arguments I planned to make. I had a general sense of which papers I was looking for, so I searched for them on Google Scholar. I also came across another paper that reminded me of Michelle’s earlier work, so I sent it to her in case she hadn’t seen it.

        # In general, I find writing to be pretty challenging. My first step is usually just getting a scaffold down. If the arguments are solid, sometimes I’ll let language models help with phrasing—especially tricky transitions—but I always revise everything myself to make sure it reflects my own voice, since LLM outputs tend to be generic.

        # Lastly, I answered some questions Michelle had about the recording.
        # """
        # WHAT_I_SAY = """
        # Question: When you encounter a technical problem in your code, how often do you consult external resources (ChatGPT, documentation, guidelines) before implementing a solution?
        # Dora's Answer: "Always, for every problem
        
        # Question: To what extent do you agree with the following statement: \"I worry that errors in my code could have serious negative consequences for the project or team.
        # Dora's Answer: Disagree

        # Question: When you're stuck on a technical problem, at what point do you typically reach out to a colleague for help?
        # Dora's Answer: I rarely reach out; I prefer to solve problems independently
        # """
        WHAT_I_SAY = """
        Question: Can you walk me through what goes through your mind when you're deciding whether to ask a colleague for help versus continuing to work through a problem on your own?
        Dora's Answer: I usually don't like asking other people for help on a problem unless they know 100\% and I know 0%, and it would be really easy for them to help me out. In that case, I'm more likely to reach out. It also really depends on who the colleague is. I'm much more likely to reach out to people I consider my peers—other PhD students, master's students, or undergrads. I almost never reach out to postdocs, and I rarely reach out to my advisors or other faculty members. I think they're really busy, and I don't think it's worth their time for me to ask. It's almost like my job as a PhD student is to figure things out on my own.
        
        Question: Tell me about a time when something broke in production or a project failed unexpectedly—how did that experience shape the way you work today?
        Dora's Answer: I mean things just kind of break all the time. That's the nature of doing research. Yeah, I guess it doesn't really shape the way I work. I think when you're doing research, it's like the goal isn't to make something production ready. It's like to make something work. Like it's to kind of instantiate your vision in the fastest way possible, and then you kind of poke and prod at it.
        
        Question: When you're deep in coding work and a Slack message comes in about scheduling or administrative tasks, what factors determine whether you switch contexts immediately or stay focused on your current task?
        Answer: If I'm doing coding work or deep work and a Slack message comes in, it depends on how urgent the administrative task is and how much it means to me.
        For example, if an administrator messages me saying they're trying to process my reimbursements but need me to send a form, I'll probably deal with that immediately since it's materially important to me. I also consider who the message is from—if it's from my advisors or about something time-sensitive, I'll likely switch and handle it right away.
        But if I glance at the message and it seems low-stakes, not directly relevant to me, or more social in nature, I probably won't switch tasks.
        The last factor is timing. If I'm deep in coding, I won't interrupt myself. But if I'm finishing up a task, waiting for something to run, or just have some downtime, I might go ahead and knock out the administrative task while I have a chance, so I don't forget about it later.
        """
        await insight.get_prose_insights(data, interview=WHAT_I_SAY)
        await insight.support_insights()

async def support_insights():
    prose_insights = json.load(open("../data/dora_pilot/pipeline_outputs/session-0/insights_prose.json", "r"))
    insight = Insights("gpt-5", 0, "Dora", "../data/dora_pilot/pipeline_outputs/session-0/insights.json", prose_insights=prose_insights)
    data = json.load(open("../data/dora_pilot/pipeline_outputs/session-0/observations_feelings_gpt-4.1_conservative.json", "r"))
    insight._set_actions_feelings(data)
    await insight.support_insights()

def print_insights():
    # user_insights = json.load(open("../data/dora_pilot/pipeline_outputs/session-0/insight_top3_iter.json", "r"))
    # for i in user_insights:
    #     if "is_deleted" in user_insights[i] and user_insights[i]["is_deleted"]:
    #         continue
    #     print(f"{i}: {user_insights[i]["insight"]["title"]}: {user_insights[i]["insight"]["insight"]}")
    #     # print(user_insights[i]["support"]["evidence"])
    #     # print(user_insights[i]["support"]["confidence"])
    #     print("CONTEXT: ", user_insights[i]["support"]["context"])
        # print("-"*100)
    for i in [2]:
        data = json.load(open(f"../data/dora_pilot/pipeline_outputs/session-{i}/insights.json", "r"))
        print("SESSION ", i + 1)
        for d in data[str(i)]:
            print(f"Insight #{d}: {data[str(i)][d]["insight"]["title"]}: {data[str(i)][d]["insight"]["insight"]}")
            print("CONTEXT: ", data[str(i)][d]["support"]["context"])
            print("\n")

if __name__ == '__main__':
    # print_insights()
    asyncio.run(main())
    # asyncio.run(score_insights())
    # asyncio.run(merge_insights())

# {
#     "insights": [
#         {
#             "title": "Thematic title of the insight",
#             "insight": "Insight in 3-4 sentences",
#             "context": "1-2 sentences when this insight might apply (e.g., when writing text, in social settings)",
#             "merged": [List of insight IDs (Session #-ID) that are merged], // Return a list with a single ID if the insight is not merged
#             "reasoning": "Reasoning about why the insight is included"
#         },
#         {
#             "title": "Thematic title of the insight",
#             "insight": "Insight in 3-4 sentences",
#         },
#         ...
#     ]
# }