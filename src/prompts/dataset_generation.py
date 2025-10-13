OBSERVATION_GENERATOR_PROMPT = """
## Prompt  

You are an expert design researcher trained in *needfinding*.  

Your task is to generate **4–6 raw behavioral observations** that would exemplify a given user need.  

### Guidelines  
- Each observation should describe **specific, concrete behaviors** — things the user does, says, or avoids.  
- Avoid generic statements; focus on **observable actions in context** (e.g., what the user clicks, says, or hesitates to do).  
- The observations should **indirectly reveal** the underlying need, not restate it.  
- Include small details (tools, settings, interactions)
- Observations MUST be observable based ONLY on computer screen recordings.

### Example  
**Need:** User needs to feel confident standing up for their opinion  

**Observations:**  
- Dora hovers over the “Raise Hand” button in Zoom but doesn’t click.  
- Dora scrolls through others’ comments on Google Docs before leaving her comment.  
- Dora selects “Accept all” to changes that others have made on her draft.  
- Dora deletes her Slack message draft after noticing that someone else already shared a similar idea.  
- Dora prefaces her contributions with “I’m not sure if this is right, but…”  

Observations should be in the following style:
- Dora assigns herself as the interviewer on multiple participant rows.
- Dora sets the “Status” field to “Invitation Sent” for her assigned participants.
- Dora applies manual color highlighting to indicate participant statuses and time slot preferences.
- The “Score” column remains empty for all entries despite multiple timestamped updates.

### Input  
Need: {need} 

### Output Format  
Return a list of 4–6 distinct observations about Dora that exemplify the need and adhere to the Guidelines. Remember observations MUST be observable based ONLY on computer screen recordings.
"""