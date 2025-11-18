import os
import yaml
import csv
import time
from pathlib import Path
from typing import List, Union, Dict, Optional
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

if __package__ is None or __package__ == "":
    from llm import LLM
    from insight_discovery import InsightDiscovery
    from prompts import REFRAME_PROBLEM_PROMPT
    from response_formats import ReframedProblems
    from utils import parse_model_json
else:
    from .llm import LLM
    from .insight_discovery import InsightDiscovery
    from .prompts import REFRAME_PROBLEM_PROMPT
    from .response_formats import ReframedProblems
    from .utils import parse_model_json


class NeedFinder:
    def __init__(
        self,
        user_name: str,
        observer_model: LLM = None,
        insight_model: LLM = None,
        synthesis_model: LLM = None,
        reframer_model: LLM = None,
    ):
        @staticmethod
        def get_environ_api_key(model_type: str):
            if model_type == "openai":
                if "OPENAI_API_KEY" not in os.environ:
                    raise Exception(
                        "API key not found. Please set the OPENAI_API_KEY environment variable."
                    )
                return os.environ.get("OPENAI_API_KEY")
            elif model_type == "anthropic":
                if "ANTHROPIC_API_KEY" not in os.environ:
                    raise Exception(
                        "API key not found. Please set the ANTHROPIC_API_KEY environment variable"
                    )
                return os.environ.get("ANTHROPIC_API_KEY")
            else:
                return

        if observer_model is None:
            observer_model = LLM(name="gpt-4.1", api_key=get_environ_api_key("openai"))

        if insight_model is None:
            insight_model = LLM(
                name="claude-sonnet-4-5-20250929",
                api_key=get_environ_api_key("anthropic"),
            )

        if synthesis_model is None:
            synthesis_model = LLM(
                name="claude-sonnet-4-5-20250929",
                api_key=get_environ_api_key("anthropic"),
            )

        if reframer_model is None:
            reframer_model = LLM(
                name="claude-sonnet-4-5-20250929",
                api_key=get_environ_api_key("anthropic"),
            )

        self.user_name = user_name
        self.observer_model = observer_model
        self.insight_model = insight_model
        self.synthesis_model = synthesis_model
        self.reframer_model = reframer_model
        # Store model names as strings for methods that expect string model names
        self.user_insights = []

    def _parse_config(self, config_path: Union[str, Path]) -> dict:
        """Parse YAML config file and return configuration dictionary."""
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config

    def _format_insights(self) -> str:
        fmt_insights = []
        for i, insight in enumerate(self.user_insights["insights"]):
            fmt_insight = f"ID {i} | {insight['title']}: {insight['tagline']}\n{insight['insight']}\nContext Insight Applies: {insight['context']}"
            fmt_insights.append(fmt_insight)
        return "\n\n".join(fmt_insights)

    async def get_insights(
        self,
        transcripts: List[List[str]],
        summaries: List[List[str]],
        timestamps: Optional[List[List[str]]] = None,
        context_anns: Optional[List[List[str]]] = None,
    ) -> List[dict]:
        """
        Get user insights from transcripts and summaries.

        Args:
            transcripts: List[List[str]] - List of transcripts for each session
            summaries: List[List[str]] - List of summaries for each session
            timestamps: Optional[List[List[str]]] - List of timestamps for each session (optional)
            context_anns: Optional[List[List[str]]] - List of context annotations for each segment of each session (optional)


        Returns:
            List[dict] - List of insights for each session
        """
        if len(transcripts) != len(summaries):
            raise ValueError("Transcripts and summaries must have the same length")
        if timestamps is not None and len(timestamps) != len(transcripts):
            raise ValueError(
                "Timestamps must have the same length as transcripts when provided"
            )

        # Process each session through the insight discovery pipeline
        insight = InsightDiscovery(user_name=self.user_name)
        all_session_insights = []

        for i, (transcript, summary) in enumerate[tuple[List[str], List[str]]](
            zip(transcripts, summaries)
        ):
            session_timestamps = [timestamps[i]] if timestamps is not None else None
            context_ann = context_anns[i] if i in context_anns else None
            # Make observations for this session
            observations = await insight.make_session_observations(
                model=self.observer_model,
                transcripts=transcript,
                summaries=summary,
                timestamps=session_timestamps,
                context_ann=context_ann,
            )

            # Get insights from observations
            session_insights = await insight.get_insights(
                observations=observations, model=self.insight_model
            )
            all_session_insights.append(session_insights)

        # Synthesize insights across all sessions
        self.user_insights = all_session_insights
        user_insights = await insight.synthesize_insights(
            insights=self.user_insights, model=self.synthesis_model
        )
        return user_insights

    async def reframe_problem(
        self, problem_description: str, insight_lim: int = 1, reframe_lim: int = 3
    ) -> ReframedProblems:
        """
        Reframe the problem description using the user insights.

        Args:
            problem_description: str - The problem description to reframe
            insight_lim: int - The maximum number of insights to use
            reframe_lim: int - The maximum number of problem reframings to generate

        Returns:
            ReframedProblems: An object with the following attributes:
                insights: List[dict] - List of selected insights
                hmw_candidates: List[str] - List of candidates problem reframings
                reasoning: str - Reasoning for selecting the insights and problem reframings
        """
        if len(self.user_insights) == 0:
            raise Exception("No insights found. Please run get_insights() first.")
        if len(problem_description) == 0:
            raise Exception(
                "Problem description is empty. Please provide a problem description."
            )
        fmt_insights = self._format_insights()
        prompt = REFRAME_PROBLEM_PROMPT.format(
            problem=problem_description,
            insights=fmt_insights,
            insight_lim=insight_lim,
            hmw_lim=reframe_lim,
            user_name=self.user_name,
        )
        if self.reframer_model.provider == "openai":
            response = await self.reframer_model.call(
                prompt, resp_format=ReframedProblems
            )
        else:
            response = await self.reframer_model.call(prompt)
            response = parse_model_json(response)
        return response
