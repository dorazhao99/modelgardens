from typing import List, Tuple, Optional, Dict
import asyncio

if __package__ is None or __package__ == "":
    # uses current directory visibility
    from prompts import (
        OBSERVE_PROMPT,
        OBSERVE_PROMPT_WCONTEXT,
        INSIGHT_PROMPT,
        INSIGHT_JSON_FORMATTING_PROMPT,
        INSIGHT_FORMAT,
        INSIGHT_SYNTHESIS_PROMPT,
    )
    from response_formats import Observations, Insights
    from utils import parse_model_json
    from llm import LLM
else:
    # uses current package visibility
    from .prompts import (
        OBSERVE_PROMPT,
        OBSERVE_PROMPT_WCONTEXT,
        INSIGHT_PROMPT,
        INSIGHT_JSON_FORMATTING_PROMPT,
        INSIGHT_FORMAT,
        INSIGHT_SYNTHESIS_PROMPT,
    )
    from .response_formats import Observations, Insights
    from .utils import parse_model_json
    from .llm import LLM


class InsightDiscovery:
    def __init__(self, user_name: str):
        self.user = user_name

    def _get_actions(
        self,
        transcripts: List[str],
        summaries: List[str],
        timestamps: Optional[List[str]] = None,
    ):
        actions = []
        if timestamps is not None:
            for transcript, summary, timestamp in zip(
                transcripts, summaries, timestamps
            ):
                actions.append(f"User's Actions at {timestamp}")
                actions.append(summary)
                actions.append(f"Transcription of User's Screen")
                actions.append(transcript)
        else:
            for transcript, summary in zip(transcripts, summaries):
                actions.append("User's Actions")
                actions.append(summary)
                actions.append(f"Transcription of User's Screen")
                actions.append(transcript)
        actions = "\n".join(actions)
        return actions

    def _extract_actions_and_feelings(
        self, observations: List[dict]
    ) -> Tuple[str, str]:
        actions = []
        feelings = []
        for observation in observations:
            actions.append(observation["action"])
            feelings.append(observation["feeling"])
        return actions, feelings

    def _reformat_observations(self, observations: List[Observations]) -> List[dict]:
        output = []
        for window_obs in observations:
            try:
                window_obs = window_obs.observations
            except:
                window_obs = window_obs["observations"]
            for obs in window_obs:
                output.append(
                    {
                        "feeling": obs.description,
                        "action": obs.evidence[0],
                        "confidence": obs.confidence,
                    }
                )
        return output

    async def make_session_observations(
        self,
        model: LLM,
        transcripts: List[str],
        summaries: List[str],
        timestamps: Optional[List[str]] = None,
        context_ann: Optional[List] = None,
        window_size: int = 5,
    ) -> List[dict]:
        """
        Make observations for a session of transcripts and summaries.

        Args:
            transcripts: List[str] - List of transcripts for the session
            summaries: List[str] - List of summaries for the session
            timestamps: Optional[List[str]] - List of timestamps for the session (optional)
            user_name: str - Name of the user
            model: str - Model to use for the observations
            context_ann: Optional[List] - List of context annotations for segments of the session (optional)
            window_size: int - Number of transcripts to include in a window (determined by context)

        Returns:
            List of observation responses for the session
        """

        assert len(transcripts) == len(
            summaries
        ), "Transcripts and summaries must have the same length"
        if timestamps is not None:
            assert len(transcripts) == len(
                timestamps
            ), "Transcripts and timestamps must have the same length"

        session_length = len(transcripts)

        tasks = []

        for index in range(0, session_length, window_size):
            sel_transcripts = transcripts[index : index + window_size]
            sel_summaries = summaries[index : index + window_size]
            sel_timestamps = (
                timestamps[index : index + window_size]
                if timestamps is not None
                else None
            )

            actions = self._get_actions(sel_transcripts, sel_summaries, sel_timestamps)
            if context_ann is not None:
                sel_context_ann = context_ann[index : index + window_size]
                sel_context_ann = set(sel_context_ann)
                sel_context_ann = "\n".join(list(sel_context_ann))
                fmt_prompt = OBSERVE_PROMPT_WCONTEXT.format(
                    actions=actions, user_name=self.user, context=sel_context_ann
                )
            else:
                fmt_prompt = OBSERVE_PROMPT.format(actions=actions, user_name=self.user)
            tasks.append(model.call(prompt=fmt_prompt, resp_format=Observations))
        response = await asyncio.gather(*tasks, return_exceptions=True)
        response = self._reformat_observations(response)
        return response

    async def get_insights(
        self, observations: List[dict], model: LLM, limit: int = 3
    ) -> List[dict]:
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
        prompt = INSIGHT_PROMPT.format(
            actions=actions, feelings=feelings, limit=limit, user_name=self.user
        )
        resp = await model.call(prompt=prompt)
        insight_prompt = INSIGHT_JSON_FORMATTING_PROMPT.format(
            insights=resp, format=INSIGHT_FORMAT
        )
        insight_resp = await model.call(prompt=insight_prompt, resp_format=Insights)
        if model.provider == "anthropic":
            structured_insights = parse_model_json(insight_resp)
        else:
            structured_insights = insight_resp
        return structured_insights

    async def synthesize_insights(
        self,
        insights: List[List[dict]],
        model: LLM,
    ) -> List[dict]:
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
        session_num = len(insights)
        for session_id, insights in enumerate(insights):
            for idx, insight in enumerate(insights.insights):
                fmt_insight = f"ID {session_id}-{idx} | {insight.title}: {insight.insight}\nContext Insight Applies: {insight.context}"
                fmt_insights.append(fmt_insight)
        fmt_insights = "\n".join(fmt_insights)
        prompt = INSIGHT_SYNTHESIS_PROMPT.format(
            input=fmt_insights, user_name=self.user, session_num=session_num
        )
        resp = await model.call(prompt=prompt)
        final_insights = parse_model_json(resp)
        return final_insights
