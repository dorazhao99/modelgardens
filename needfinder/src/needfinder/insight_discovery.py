from typing import List, Tuple
import asyncio

if __package__ is None or __package__ == '':
    # uses current directory visibility
    from prompts import OBSERVE_PROMPT, INSIGHT_PROMPT, INSIGHT_JSON_FORMATTING_PROMPT, INSIGHT_FORMAT, INSIGHT_SYNTHESIS_PROMPT
    from response_formats import Observations, Insights
    from utils import parse_model_json
    from llm import LLM
else:
    # uses current package visibility
    from .prompts import OBSERVE_PROMPT, INSIGHT_PROMPT, INSIGHT_JSON_FORMATTING_PROMPT, INSIGHT_FORMAT, INSIGHT_SYNTHESIS_PROMPT
    from .response_formats import Observations, Insights
    from .utils import parse_model_json
    from .llm import LLM
   

class InsightDiscovery:
    def __init__(self, user_name: str):
        self.user = user_name

    def _get_actions(self, transcripts: List[str], summaries: List[str], timestamps: List[str]):
        for transcript, summary, timestamp in zip(transcripts, summaries, timestamps):
            actions.append(f"User's Actions at {timestamp}")
            actions.append(summary)
            actions.append(f"Transcription of User's Screen")
            actions.append(transcript)
        actions = "\n".join(actions)
        return actions

    def _extract_actions_and_feelings(self, observations: List[dict]) -> Tuple[str, str]:
        actions = []
        feelings = []
        for observation in observations:
            actions.append(observation['action'])
            feelings.append(observation['feeling'])
        return actions, feelings

    def _reformat_observations(self, responses: List[Observations]) -> List[dict]:
        output = []
        for response in responses:
            output.append(
                {
                    "feeling": response.description,
                    "action": response.evidence[0],
                    "confidence": response.confidence,
                }
            )
        return output


    async def make_session_observations(
        self,
        transcripts: List[str],
        summaries: List[str],
        timestamps: List[str],
        model: str = "gpt-4.1",
        window_size: int = 5,
    ) -> List[dict]:
        """
        Make observations for a session of transcripts and summaries.

        Args:
            transcripts: List[str] - List of transcripts for the session
            summaries: List[str] - List of summaries for the session
            timestamps: List[str] - List of timestamps for the session
            user_name: str - Name of the user
            model: str - Model to use for the observations
            window_size: int - Number of transcripts to include in a window (determined by context)

        Returns:
            List of observation responses for the session
        """
        prompt = OBSERVE_PROMPT.format(transcripts=transcripts, summaries=summaries)

        assert len(transcripts) == len(summaries), "Transcripts and summaries must have the same length"
        assert len(transcripts) == len(timestamps), "Transcripts and timestamps must have the same length"

        session_length = len(transcripts)

        tasks = []
        for index in range(0, session_length, window_size):
            sel_transcripts = transcripts[index : index + window_size]
            sel_summaries = summaries[index : index + window_size]
            sel_timestamps = timestamps[index : index + window_size]
            actions = self._get_actions(sel_transcripts, sel_summaries, sel_timestamps)
            fmt_prompt = prompt.format(actions=actions, user_name=self.user)
            tasks.append(LLM.call(fmt_prompt, model, resp_format=ObservationResponse))
        response = await asyncio.gather(*tasks, return_exceptions=True)
        response = self._reformat_observations(response)
        return response

    async def get_insights(self, observations: List[dict], model: str, limit: int = 3) -> List[dict]:
        """
        Get insights for a session of observations.

        Args:
            observations: List[dict] - List of observations for the session
            model: str - Model to use for the insights
            limit: int - Number of insights to generate

        Returns:
            List of insights
        """
        if len(observations) == 0 or limit <= 0:
            return []
        actions, feelings = self._extract_actions_and_feelings(observations)
        prompt = INSIGHT_PROMPT.format(actions=actions, feelings=feelings, limit=limit, user_name=self.user)
        resp = await LLM.call(prompt, model)
        insight_prompt = INSIGHT_JSON_FORMATTING_PROMPT.format(insights=resp, format=INSIGHT_FORMAT)
        insight_resp = await LLM.call(insight_prompt, model, resp_format=Insights)
        structured_insights = parse_model_json(insight_resp)
        return structured_insights  
    
    async def synthesize_insights(self, insights: List[List[dict]], model: str) -> List[dict]:
        """
        Synthesize insights across multiple sessions.

        Args:
            insights: List[List[dict]] - List of insights for each session
            model: str - Model to use for the synthesis

        Returns:
            List of final insights
        """
        if len(insights) == 0:
            return []

        fmt_insights = []
        for session_id, insights in enumerate(insights):
            for idx, insight in enumerate(insights):
                fmt_insight = f"ID {session_id}-{idx} | {insight['title']}: {insight['insight']}\nContext Insight Applies: {insight['context']}"
                fmt_insights.append(fmt_insight)
        fmt_insights = "\n".join(fmt_insights)
        prompt = INSIGHT_SYNTHESIS_PROMPT.format(input=fmt_insights, user_name=self.user, session_num=len(insights))
        resp = await LLM.call(prompt, model)
        final_insights = parse_model_json(resp)
        return final_insights

a