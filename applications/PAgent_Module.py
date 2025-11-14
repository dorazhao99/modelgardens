import os
import asyncio
import json
import orjson
import requests
import tkinter as tk
import time
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from typing import List
from dotenv import load_dotenv
from utils import call_gpt, call_anthropic
from advice import INSIGHT_ADVICE_PROMPTS
from agent_prompts import AGENT_CONSTRAINTS, BASELINE_AGENT_PROMPT, AGENT_SPEC, AgentSpec

load_dotenv()


class PersonalizedAgent:
    def __init__(self, model: str, fidx: str, user: str, save_file: str, limit: int = 2):
        self.model = model
        self.fidx = fidx
        self.user = user
        self.save_file = save_file
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.insights = json.load(open(f"../data/{self.fidx}/pipeline_outputs/session-meta/insights_prompt.json"))["insights"]
        self.fmt_insights = self._format_insights()
        self.insight_prompt = INSIGHT_ADVICE_PROMPTS["v3"]
        self.limit = limit
        self.claude_model = "claude-sonnet-4-5-20250929"

    def _format_insights(self):
        insights = []
        for i, insight in enumerate(self.insights):
            fmt_insight = f"ID {i} | {insight['title']}: {insight['tagline']}\n{insight['insight']}\nContext Insight Applies: {insight['context']}"
            insights.append(fmt_insight)
        return "\n\n".join(insights)

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)
    

    def _get_user_input(self, placeholder_name: str, description: str) -> str:
       
        """Display a tkinter dialog to get user input."""
        root = tk.Tk()
        # root.withdraw()  # Hide the main window
        
        # Create a custom dialog
        dialog = tk.Toplevel(root)
        dialog.title(f"Input: {placeholder_name}")
        dialog.geometry("500x500")
        dialog.resizable(True, True)
        
        # Center the window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Make dialog modal and bring to front
        dialog.transient(root)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()
        
        result = [None]  # Use list to allow modification in nested function
        
        # Label
        label = tk.Label(dialog, text=f"{placeholder_name}\n{description}", 
                        wraplength=450, justify="left", padx=10, pady=5)
        label.pack(pady=5, anchor="w")
        
        # Frame for text widget and scrollbar
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Text widget for multi-line input
        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=60, height=20)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_widget.focus()
        
        # Scrollbar for text widget
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        def submit():
            result[0] = text_widget.get("1.0", tk.END).strip()
            dialog.destroy()
            root.destroy()
        
        def on_ctrl_enter(event):
            submit()
            return "break"
        
        # Bind Ctrl+Enter to submit (Enter alone creates new line)
        text_widget.bind('<Control-Return>', on_ctrl_enter)
        
        # Submit button
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=5)
        button = tk.Button(button_frame, text="Submit", command=submit, width=10)
        button.pack()
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result[0] if result[0] is not None else ""
    
    def _format_prompt(self, spec: AgentSpec):
        prompt = spec.execution_prompt
        for user_input in spec.user_inputs:
            user_value = self._get_user_input(user_input.placeholder_name, user_input.description)
            if user_input.placeholder_name in prompt:
                prompt = prompt.replace(user_input.placeholder_name, user_value)
        return prompt
    
    async def get_baseline_solutions(self, query:str):
        baseline_prompt = BASELINE_AGENT_PROMPT.format(scenario=query, constraints=AGENT_CONSTRAINTS, limit=self.limit, user_name=self.user)
        print(baseline_prompt)
        baseline_response = await call_anthropic(self.anthropic_client, baseline_prompt, self.claude_model)
        return baseline_response
    
    async def draft_spec(self, solution: str | List[str], scenario: str, problem: str):
        if isinstance(solution, str):
            solution = [solution]
        tasks = []
        for sol in solution:
            spec_prompt = AGENT_SPEC.format(solution=sol, constraints=AGENT_CONSTRAINTS, \
            limit=self.limit, user_name=self.user, problem=problem, scenario=scenario)
            spec_response = self._guarded_call(self.client, spec_prompt, self.model, resp_format=AgentSpec)
            tasks.append(spec_response)
        resps = await asyncio.gather(*tasks)
        return resps
    
    def run_agent(self, execution_prompt: str):
        url = "http://localhost:8000/chat"
        headers = {"Content-Type": "application/json"}
        data = {"message": execution_prompt}

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            print("Response:", response.json())
            return response.json()
        except Exception as e:
            print(f"Error calling FastAPI server: {e}")
            return None


async def sandbox():
    agent = PersonalizedAgent(model="gpt-4.1", fidx="dora_pilot", user="Dora", save_file="advice.json", limit=3)
    # scenario = "Need assistance when writing CHI reviews"
    # problem="Question the assumption: HMW make it safe for Dora to trust her subjective impressions without exhaustive comparison to standards?"
    # solution = """Complexity-Clarity Translator: When Dora writes a nuanced, multi-perspective analysis, the agent generates 2-3 alternative phrasings at different clarity levels in a side-by-side view, explicitly labeling the tradeoffs made in each version (e.g., "Version A preserves X perspective but may lose Y readers"). This externalizes the ethical tension, making it a design choice rather than a personal inadequacy, and validates that her struggle represents thoughtfulness rather than incompetence."""
    scenario = "Help with drafting a research statement for academic faculty applications" 
    problem = ""
    solution = """Benchmark Against Successful Examples in Her Field: Conduct web searches to find publicly available research statements from recently hired faculty in Michelle's specific discipline and target institution types. Use the LLM to analyze common structural patterns, thematic elements, and successful framing strategies, then generate a customized draft that incorporates these best practices while maintaining Michelle's authentic research narrative.
    """
    specs = await agent.draft_spec(solution, scenario, problem)
    for idx, spec in enumerate(specs):
        print(spec)
        with open(f"spec_{idx}_{time.strftime('%Y%m%d_%H%M%S')}.json", "wb") as f:
            f.write(orjson.dumps(spec.model_dump(), option=orjson.OPT_INDENT_2))
        execution_prompt = agent._format_prompt(spec)
        agent.run_agent(execution_prompt)

    # resp = await advice_seeker.get_baseline_solutions("Help with drafting a research blog post about 'Sporks of AGI'")


async def main():
    # questions = [
    #     "I have a big presentation coming up for the end of my grant. How should I prep my slides?", 
    #     "I have to balance three different projects at work. How should I prioritize them?",
    #     "I want to tell my advisor that I want to quit one of my projects, but I'm afraid they'll be angry. What should I do?",
    #     "I need to develop a mobile app for my new project, but I've literally never done this before and I'm afraid I'll mess it up. What should I do?",
    #     "I need to  potential collaborator who I've never met before about setting up a meeting to chat about a new project. What should I say?",
    #     "I'm going to meet my partner's parents for the first time... what are some tips for making a good impression?",
    #     "I've been really struggling with my productivity lately like I can't get any work done during the day and am stressed and worried about falling behind. How do I get back on track?",
    #     "I'm working on a project with some collaborators but they're literally not doing anything and expecting me to do everything. What do I do?",
    #     "I got asked to be a panelist for a conference and I have no idea what to say. What should I do?",
    # ]
    # questions = [
    #     "I've been really struggling with my productivity lately like I can't get any work done during the day and am stressed and worried about falling behind. How do I get back on track?",
    # ]
    questions = [
        "Build a personalized calendar manager that helps me manage my time and schedule my tasks.",
    ]
    advice_seeker = AdviceSeeker(model="gpt-4.1", fidx="dora_pilot", user="Dora", save_file="advice.json")

    tasks = []
    for q in questions:
        tasks.append(advice_seeker.get_advice(q))
        
    results = await asyncio.gather(*tasks)
    for r, q in zip(results, questions):
        i_response = r
        print(q)
        print("Model Response:")
        print(i_response['model_response'])
        print("\n")
        print("Baseline Response:")
        print(i_response['baseline_response'])
        # print(ni_response)
        print("-"*100)

if __name__ == "__main__":
    asyncio.run(sandbox())
    # asyncio.run(main())