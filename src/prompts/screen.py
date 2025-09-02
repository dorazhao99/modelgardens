TRANSCRIPTION_PROMPT = """Transcribe in markdown ALL the content from the screenshots of the user's screen.

NEVER SUMMARIZE ANYTHING. You must transcribe everything EXACTLY, word for word, but don't repeat yourself.

ALWAYS include all the application names, file paths, and website URLs in your transcript.

Create a FINAL structured markdown transcription."""

ACTION_PROMPT = """Transcribe in markdown ALL the actions that the user is taking based on the user's screen.

NEVER SUMMARIZE ANYTHING. For each action, give a description of what they are doing. In some cases, you may have to infer the user's actions based on outputs from the screen. For example, if text appears on the screen, this may suggest the user is typing or copy-pasted text. 

Do **NOT** make any inferences about the user's intent behind actions. Just report what actions they are taking.

If they are interacting with content on the screen, include the application names, file paths, website URLs in the action. Inaction when the user is not doing anything should also be noted. 

Return the **specific and detailed** list of actions in sequential order that they occur in the following format: 
{{
    "actions": [
        {
            "description": Description of what action the user took
            "target": What the user is interacting with
            "result": Description of the result of the user's actions, if observable
        }
    ]
}}
"""

SUMMARY_PROMPT = """
Provide a detailed description of the actions occuring across the provided images. 

Include as much relevant detail as possible, but remain concise.

Generate a handful of bullet points and reference *specific* actions the user is taking.
"""

OVERVIEW_PROMPT = """
Provide a bulleted list of observations about the user's actions, environments, interactions and objects. 

Be specific in the descriptions while still remaining concise.

{input}
"""