from ast import Dict
from math import e
import os
import random
import hdbscan
import pdb
import asyncio
import json
import argparse
import time
import pdb
import numpy as np
import re
import uuid
import orjson
from utils import call_gpt, get_openai_embeddings
from openai import AsyncOpenAI, OpenAI
from prompts import need_finder, observer
from response_formats import (
    RelationsResponse,
    InsightResponse,
    ClusterResponse,
    CohesionResponse,
    DuplicateResponse,
    GeneralJudge,
)
from dotenv import load_dotenv
from BM25 import BM25NeedsIndex
from EmbeddingStore import EmbeddingsStore
from typing import List, Dict
from prompts import test_dataset



class Clusterer:
    def __init__(self, model, params, dup_threshold: float = 0.9):
        load_dotenv()
        self.model = model
        self.count = 0
        self.name = params["user"]
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sync_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sim_threshold = 0.8
        self.embed_store = EmbeddingsStore(
            st_model_name="all-MiniLM-L6-v2",
            sim_threshold=self.sim_threshold,
            device="cpu",
            ann_max=int(os.getenv("ANN_MAX_ELEMENTS", "200000")),
        )
        # Speed/quality knobs
        self.need_index = BM25NeedsIndex({})
        self.prompt2name = {
            "baseline": need_finder.BASELINE_PROMPT,
            "baseline_image": need_finder.BASELINE_IMAGE_PROMPT,
            "text": need_finder.NEEDFINDING_TEXT_PROMPT,
            "text_conf": need_finder.NEEDFINDING_TEXT_PROMPT_CONF,
            "text_image": need_finder.NEEDFINDING_TEXT_IMAGE_PROMPT,
        }
        self.all_needs = {}
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.timestamp = time.strftime("%Y%m%d")
        self.dup_threshold = dup_threshold

    def _query_text(self, q):
        if isinstance(q, dict):
            return f"{q.get('need','')}\n{q.get('reasoning','')}"
        return str(q)

    def _search_bm25(self, q, top_k: int = 3):
        query = self._query_text(q)
        return self.need_index.search(query, top_k=top_k)

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)

    def _exists_id(self, nid: str) -> bool:
        return nid in self.all_needs

    def _process_resp(self, resps, output):
        for resp in resps:
            gid = uuid.uuid4()
            for n in resp.user_needs:
                nid = f"{self.count}"
                item = {
                    "id": nid,
                    "need": n.need,
                    "reasoning": n.reasoning,
                    "confidence": n.confidence,
                    "merged_ids": n.merged,
                    "step": n.step,
                    "group_id": gid,
                }
                output.append(item)
                self.count += 1
        return output

    def _format_observations(self, observations: List[dict]) -> str:
        output = []
        for o in observations:
            if "text" in o:
                output.append(f"ID {o['id']} | {o['text']}")
            else:
                output.append(
                    f"ID {o['id']} | {o['description']}\nEvidence: {' '.join(o['evidence'])}"
                )
        return "\n".join(output)

    def _merge_observations(self, items, scores, threshold=8) -> List[dict]:
        n = len(items)
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            parent[find(x)] = find(y)

        # Merge items with scores >= threshold
        for (i, j), score in scores.items():
            if score >= threshold:
                union(i, j)

        # Group items by their root parent
        clusters = {}
        for i in range(n):
            root = find(i)
            clusters.setdefault(root, set()).add(items[i])

        return list(clusters.values())

    async def cluster_observations(
        self,
        observations: List[dict],
        seed: List[str] = [],
        existing_clusters: List[dict] = [],
    ) -> List[dict]:
        fmt_observations = self._format_observations(observations)
        if len(seed) > 0:
            prompt = observer.LLM_CLUSTER_PROMPT_SEED.format(
                observations=fmt_observations, seed=seed, user_name=self.name
            )
        else:
            if len(existing_clusters) > 0:
                fmt_existing = [
                    f"Cluster {i +1}: {c['description']}\nMerged IDs: {', '.join(c['merged'])}"
                    for i, c in enumerate(existing_clusters)
                ]
                fmt_existing = "\n".join(fmt_existing)
                prompt = observer.LLM_CLUSTER_PROMPT_UPDATE.format(
                    observations=fmt_observations,
                    existing_clusters=fmt_existing,
                    user_name=self.name,
                )
            else:
                prompt = observer.LLM_CLUSTER_PROMPT.format(
                    observations=fmt_observations, user_name=self.name
                )
        resp = await self._guarded_call(
            self.client, prompt, self.model, resp_format=ClusterResponse
        )
        clusters = resp.clusters
        return clusters

    async def get_insights(
        self, clusters: List[dict], output_observations: Dict
    ) -> List[dict]:
        tasks = []
        for cluster in clusters:
            members = [output_observations[str(member)] for member in cluster.members]
            fmt_observations = self._format_observations(members)
            prompt = observer.LLM_INSIGHT_PROMPT.format(
                observations=fmt_observations, reasoning=cluster.evidence
            )
            tasks.append(
                self._guarded_call(
                    self.client, prompt, "gpt-5", resp_format=InsightResponse
                )
            )
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        return resps

    def format_insights(self, insights: List[dict]) -> str:
        return "\n".join(
            [
                f"ID {i['id']} | {i['theme']}: {i['description']}\nEvidence: {i['evidence']}"
                for i in insights
            ]
        )

    async def label_interesting(self, insights: List[dict]) -> List[dict]:
        tasks = []
        for insight in insights:
            new_insight = f"{insight['description']}\nEvidence: {insight['evidence']}"
            prompt = observer.JUDGE_INTERESTING_PROMPT.format(new_insight=new_insight)
            tasks.append(
                self._guarded_call(
                    self.client, prompt, "gpt-5", resp_format=GeneralJudge
                )
            )
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        return resps

    def save_file(self, out_path: str, output_observations):
        data = {str(k): v for k, v in output_observations.items()}
        with open(out_path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    async def llm_pipeline_alt(
        self,
        fidx: str,
        session_num: int,
        observations: List[dict] | Dict,
        num_iterations: int = 10,
        seed: List[str] = [],
    ) -> Dict:
        out_path = f"../data/{fidx}/pipeline_outputs/session-{session_num}/cluster_{self.model}.json"
        np.random.seed(123)
        output_observations = {}
        max_id = 0

        # For test dataset, insert existing granular observations into the output
        if isinstance(observations, dict):
            observations = list(observations.values())

        for o in observations:
            evidence = o["evidence"]
            if "text" in o:
                description = o["text"]
            else:
                description = o["description"]
            output_observations[str(o["id"])] = {
                "id": str(o["id"]),
                "description": description,
                "evidence": evidence,
                "confidence": o["confidence"],
            }
            max_id = max(max_id, int(o["id"]))

        count = 0

        uncovered_ids = set([str(o["id"]) for o in observations])
        all_ids = set([str(o["id"]) for o in observations])

        insights = []
        is_saturated = False

        while count < num_iterations and not is_saturated:
            tasks = []
            sampled_observations = observations
            clusters = await self.cluster_observations(
                sampled_observations, seed, existing_clusters=insights
            )
            for cluster in clusters:
                members = [
                    output_observations[str(member)]
                    for member in cluster.members
                    if str(member) in output_observations
                ]
                fmt_members = self._format_observations(members)
                prompt = observer.LLM_INSIGHT_PROMPT.format(
                    observations=fmt_members, reasoning=cluster.evidence
                )
                tasks.append(
                    self._guarded_call(
                        self.client, prompt, self.model, resp_format=InsightResponse
                    )
                )

            resps = await asyncio.gather(*tasks, return_exceptions=True)
            new_observations = []

            # Judge Cohesion
            cohesion_tasks = []
            duplicate_tasks = []
            for i, r in enumerate(resps):
                theme = r.theme
                description = r.description
                cluster_members = clusters[i].members
                merged_obs = [
                    output_observations[str(x)]
                    for x in cluster_members
                    if str(x) in output_observations
                ]

                input_obs = []
                for x in merged_obs:
                    if "theme" in x:
                        input_obs.append(f"{x['theme']}: {x['description']}")
                    else:
                        input_obs.append(x["description"])

                cohesion_prompt = observer.JUDGE_COHESION_PROMPT.format(
                    observations="\n".join(input_obs),
                    grouping=f"{theme}: {description}",
                )
                cohesion_tasks.append(
                    self._guarded_call(
                        self.client,
                        cohesion_prompt,
                        "gpt-4.1",
                        resp_format=CohesionResponse,
                    )
                )

                if len(insights) > 0:
                    fmt_insights = self.format_insights(insights)
                    duplicate_prompt = observer.JUDGE_DUPLICATE_PROMPT.format(
                        new_insight=f"{theme}: {description}",
                        existing_insights=fmt_insights,
                    )
                    duplicate_tasks.append(
                        self._guarded_call(
                            self.client,
                            duplicate_prompt,
                            "gpt-4.1",
                            resp_format=DuplicateResponse,
                        )
                    )

            cohesion_resps = await asyncio.gather(
                *cohesion_tasks, return_exceptions=True
            )
            duplicate_resps = await asyncio.gather(
                *duplicate_tasks, return_exceptions=True
            )

            # SAVE OBSERVATIONS
            num_duplicates = 0
            total_observations = 0

            for i, r in enumerate(resps):
                theme = r.theme
                description = r.description
                evidence = r.evidence

                cluster_members = clusters[i].members
                merged_obs = [
                    output_observations[str(x)]
                    for x in cluster_members
                    if str(x) in output_observations
                ]
                try:
                    cohesion = cohesion_resps[i].cohesion
                    confidence = cohesion_resps[i].confidence
                except Exception as e:
                    cohesion = 0
                    confidence = 0

                if len(insights) > 0:
                    is_duplicate = duplicate_resps[i].judgement
                    dup_reason = duplicate_resps[i].reason
                else:
                    is_duplicate = False

                if cohesion < 6:
                    print("Discarded Cohesion", theme, description, merged_obs)
                    break

                total_observations += 1
                if is_duplicate:
                    print(
                        "Discarded Duplicate", theme, dup_reason 
                    )
                    num_duplicates += 1
                    dup_id = str(duplicate_resps[i].id)
                    if dup_id in output_observations:
                        output_observations[dup_id]["evidence"].append(
                            evidence
                        )
                        if "merged" in output_observations[dup_id]:
                            existing_ids = set(
                                output_observations[dup_id]["merged"]
                            )
                        else:
                            existing_ids = set()
                        new_ids = set([str(x) for x in cluster_members if str(x) != dup_id])
                        output_observations[dup_id]["merged"] = list(
                            existing_ids.union(new_ids)
                        )
                    else:
                        print("Duplicate not found", dup_id)
                    # Add relevant ids to duplicate observation
                else:
                    new_id = str(max_id + 1)
                    obs = {
                        "id": new_id,
                        "theme": theme,
                        "description": description,
                        "cohesion": cohesion,
                        "confidence": confidence,
                        "evidence": [evidence],
                        "merged": [str(x) for x in cluster_members],
                        "observations": [output_observations[str(x)] for x in cluster_members if str(x) in output_observations],
                    }

                    for m in cluster_members:
                        if str(m) in uncovered_ids:
                            uncovered_ids.remove(str(m))

                    all_ids.add(obs["id"])
                    output_observations[obs["id"]] = obs
                    new_observations.append(obs)
                    max_id += 1

            # duplicate ratio
            dup_ratio = num_duplicates / total_observations
            print("Duplicate ratio", dup_ratio)
            if dup_ratio > self.dup_threshold:
                is_saturated = True
                print("Saturated due to duplicate ratio", dup_ratio)

            observations.extend(new_observations)
            insights.extend(new_observations)
            np.random.shuffle(observations)

            self.save_file(out_path, output_observations)
            print(f"Iteration: {count} | Next Level: {len(observations)}")
            count += 1

        # print("Insights")
        # interesting_resps = await self.label_interesting(insights)
        # for insight, resp in zip(insights, interesting_resps):
        #     iid = insight["id"]
        #     output_observations[iid]["interesting"] = resp.judgement
        #     output_observations[iid]["reasoning"] = resp.reason
        self.save_file(out_path, output_observations)
        return output_observations

    async def llm_pipeline(
        self,
        fidx: str,
        observations: List[dict] | Dict,
        num_iterations: int = 10,
        seed: List[str] = [],
    ) -> Dict:
        output_observations = {}
        max_id = 0
        out_path = f"../data/{fidx}/llm_outputs/cluster_{self.model}_hierarchical.json"
        # For test dataset, insert existing granular observations into the output
        if isinstance(observations, dict):
            observations = list(observations.values())

        for o in observations:
            if "generality" in o:
                generality = o["generality"]
                evidence = o["evidence"]
            else:
                generality = 0
                evidence = o["evidence"]
            if "text" in o:
                description = o["text"]
            else:
                description = o["description"]
            output_observations[str(o["id"])] = {
                "id": str(o["id"]),
                "description": description,
                "generality": generality,
                "evidence": evidence,
            }
            max_id = max(max_id, int(o["id"]))

        count = 0

        uncovered_ids = set([str(o["id"]) for o in observations])
        all_ids = set([str(o["id"]) for o in observations])
        insights = []
        while len(observations) >= 2 and count < num_iterations:
            tasks = []
            clusters = await self.cluster_observations(observations, seed)
            for cluster in clusters:
                members = [
                    output_observations[str(member)]
                    for member in cluster.members
                    if str(member) in output_observations
                ]
                fmt_members = self._format_observations(members)
                prompt = observer.LLM_INSIGHT_PROMPT.format(
                    observations=fmt_members, reasoning=cluster.evidence
                )
                tasks.append(
                    self._guarded_call(
                        self.client, prompt, self.model, resp_format=InsightResponse
                    )
                )
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            new_observations = []

            # Judge Cohesion
            cohesion_tasks = []
            for i, r in enumerate(resps):
                for observation in r.observations:
                    cluster_members = clusters[i].members
                    merged_obs = [
                        output_observations[str(x)]
                        for x in cluster_members
                        if str(x) in output_observations
                    ]
                    input_obs = [x["description"] for x in merged_obs]
                    cohesion_prompt = observer.JUDGE_COHESION_PROMPT.format(
                        observations="\n".join(input_obs),
                        grouping=observation.description,
                    )
                    cohesion_tasks.append(
                        self._guarded_call(
                            self.client,
                            cohesion_prompt,
                            "gpt-4o",
                            resp_format=CohesionResponse,
                        )
                    )
            cohesion_resps = await asyncio.gather(
                *cohesion_tasks, return_exceptions=True
            )

            # SAVE OBSERVATIONS
            for i, r in enumerate(resps):
                for observation in r.observations:
                    cluster_members = clusters[i].members
                    merged_obs = [
                        output_observations[str(x)]
                        for x in cluster_members
                        if str(x) in output_observations
                    ]
                    cohesion = cohesion_resps[i].cohesion

                    if cohesion < 6:
                        print("Discarded Cohesion", observation.description, merged_obs)
                        break

                    is_general = True

                    generality = observation.generality
                    for m in merged_obs:
                        if "generality" in m and m["generality"] > generality:
                            is_general = False
                            print("Discarded Generality", m)
                            break

                    if is_general and len(cluster_members) > 1:
                        obs = {
                            "id": str(max_id + 1),
                            "description": observation.description,
                            "generality": observation.generality,
                            "cohesion": cohesion,
                            "evidence": [observation.evidence],
                            "merged": [str(x) for x in cluster_members],
                        }
                        for m in cluster_members:
                            if str(m) in uncovered_ids:
                                uncovered_ids.remove(str(m))

                        all_ids.add(obs["id"])
                        output_observations[obs["id"]] = obs
                        new_observations.append(obs)
                        uncovered_ids.add(obs["id"])
                        max_id += 1
                        insights.append(obs)
            next_rounds_observations = []
            print(uncovered_ids)
            for o in observations:
                if str(o["id"]) in uncovered_ids:
                    next_rounds_observations.append(o)
            next_rounds_observations.extend(new_observations)
            observations = next_rounds_observations
            # out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/{self.entry}_{self.model}_{self.timestamp}.json"
            data = {str(k): v for k, v in output_observations.items()}
            self.save_file(out_path, data)
            print(f"Iteration: {count} | Next Level: {len(observations)}")
            count += 1

        print("Insights")
        interesting_resps = await self.label_interesting(insights)
        for insight, resp in zip(insights, interesting_resps):
            iid = insight["id"]
            output_observations[iid]["interesting"] = resp.judgement
            output_observations[iid]["reasoning"] = resp.reason
        self.save_file(out_path, output_observations)
        return output_observations

    async def cluster_pipeline(
        self, observations: List[dict], num_iterations: int = 10, seed: List[str] = []
    ) -> Dict:
        output_observations = {}
        max_id = 0

        # For test dataset, insert existing granular observations into the output
        for o in observations:
            if "generality" in o:
                generality = o["generality"]
                evidence = o["evidence"]
            else:
                generality = 0
                evidence = []
            if "text" in o:
                description = o["text"]
            else:
                description = o["description"]
            output_observations[str(o["id"])] = {
                "id": str(o["id"]),
                "description": description,
                "generality": generality,
                "evidence": evidence,
            }
            max_id = max(max_id, int(o["id"]))

        tasks = []
        for i in range(num_iterations):
            if i > 0:
                random.shuffle(observations)
            tasks.append(self.cluster_observations(observations))
        output = {}
        clusters = await asyncio.gather(*tasks, return_exceptions=True)
        for i, cluster in enumerate(clusters):
            output[str(i)] = [c.model_dump() for c in cluster]
        print(output)
        out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/clusters/perturbation_6_{self.model}.json"
        with open(out_path, "wb") as f:
            f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))
        return output

    # async def llm_pipeline_2(self, observations: List[dict], max_iters: int = 5) -> Dict:
    #     """
    #         Instead of only grouping merged observations, add merged into original and merge again
    #     """
    #     output_observations = {}
    #     max_id = 0

    #     # For test dataset, insert existing granular observations into the output
    #     for o in observations:
    #         if 'generality' in o:
    #             generality = o['generality']
    #             evidence = o['evidence']
    #         else:
    #             generality = 0
    #             evidence = []
    #         if 'text' in o:
    #             description = o['text']
    #         else:
    #             description = o['description']
    #         output_observations[str(o['id'])] = {
    #             'id': str(o['id']),
    #             'description': description,
    #             'generality': generality,
    #             'evidence': evidence
    #         }
    #         max_id = max(max_id, int(o['id']))
    #     count = 0

    #     uncovered_ids = set([str(o['id']) for o in observations])

    #     while(len(observations) >= 2 and count < max_iters):
    #         fmt_observations = self._format_observations(observations)
    #         prompt = observer.LLM_CLUSTER_PROMPT.format(observations=fmt_observations)
    #         resp = await self._guarded_call(self.client, prompt, self.model, resp_format=ClusterResponse)
    #         print(resp)
    #         tasks = []
    #         clusters = resp.clusters
    #         new_observations = []
    #         for cluster in clusters:
    #             merged_obs = [output_observations[str(x)] for x in cluster.members]
    #             generality = cluster.generality
    #             cohesion = cluster.cohesion
    #             is_general, is_cohesive = True, True
    #             for m in merged_obs:
    #                 if m["generality"] > generality:
    #                     is_general = False
    #                     print("Discarded", m, cluster.summary)
    #                     break
    #                 if 'cohesion' in m and m["cohesion"] < cohesion:
    #                     is_cohesive = False
    #                     print("Discarded", m, cluster.summary)
    #                     break
    #             if is_general and is_cohesive and len(cluster.members) > 1:
    #                 obs = {
    #                     'id': str(max_id + 1),
    #                     'description': cluster.summary,
    #                     'generality': cluster.generality,
    #                     'cohesion': cluster.cohesion,
    #                     'evidence': [cluster.evidence],
    #                     'merged': [str(x) for x in cluster.members]
    #                 }
    #                 print(cluster.summary, cluster.cohesion)
    #                 output_observations[obs['id']] = obs
    #                 new_observations.append(obs)
    #                 max_id += 1
    #         observations = new_observations
    #         if len(seed) > 0:
    #             out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline2/synthetic_{self.model}_seed.json"
    #         else:
    #             out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline2/synthetic_{self.model}.json"
    #         data = {str(k): v for k, v in output_observations.items()}

    #         with open(out_path, "wb") as f:
    #             f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    #         print(f"Iteration: {count} | Next Level: {len(observations)}")
    #         count += 1
    #     return output_observations

    async def baseline_pipeline(
        self, observations: List[dict], max_iters: int = 5
    ) -> Dict:
        print(observations)
        output_observations = {}
        max_id = 0
        for o in observations:
            if "generality" in o:
                generality = o["generality"]
                evidence = o["evidence"]
            else:
                generality = 0
                evidence = o["evidence"]
            if "text" in o:
                description = o["text"]
            else:
                description = o["description"]
            output_observations[str(o["id"])] = {
                "id": str(o["id"]),
                "description": description,
                "generality": generality,
                "evidence": evidence,
            }
            max_id = max(max_id, int(o["id"]))

        props, data = [], []
        for o in observations:
            props.append(f"{o['text']}")
            data.append(o)
        embeddings = get_openai_embeddings(
            self.sync_client, props, "text-embedding-3-large"
        )
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean")
        labels = clusterer.fit_predict(embeddings)

        for need, label in zip(props, labels):
            print(f"Cluster {label}: {need}")

        clusters = {}
        for d, label in zip(data, labels):
            if label != -1:
                clusters.setdefault(label, []).append(d)
        tasks = []
        for c in clusters:
            fmt_members = []
            for member in clusters[c]:
                fmt_members.append(f"ID {member['id']} | {member['text']}")
            prompt = observer.LLM_INSIGHT_PROMPT.format(observations=fmt_members)
            tasks.append(
                self._guarded_call(
                    self.client, prompt, self.model, resp_format=InsightResponse
                )
            )
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        print(resps)
        for resp, c in zip(resps, clusters):
            for observation in resp.observations:
                output_observations[str(max_id + 1)] = {
                    "id": str(max_id + 1),
                    "description": observation.description,
                    "generality": observation.generality,
                    "cohesion": observation.cohesion,
                    "evidence": [observation.evidence],
                    "merged": [str(x["id"]) for x in clusters[c]],
                }
                max_id += 1

        out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/baseline/synthetic-small_{self.model}.json"
        data = {str(k): v for k, v in output_observations.items()}

        with open(out_path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        return resps


async def test():
    params = {
        "name": "text_conf",
        "user": "Dora",
    }
    need_p = Observer(args.model, params)
    filename = "/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline_alt/40_o4-mini_20251009.json"
    observations = json.load(open(filename))
    insights = {str(k): v for k, v in observations.items() if "merged" in v}
    print(insights)
    interesting_resps = await need_p.label_interesting(insights)
    for iid, resp in zip(insights, interesting_resps):
        print(insights[iid]["description"], resp.judgement, resp.reason)


async def main(args):
    params = {
        "user": args.user,
    }
    need_p = Clusterer(args.model, params)

    if args.type == "perturbation":
        tasks = []
        for fidx in range(3, 21):
            dataset = json.load(
                open(
                    f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/perturbations/{fidx}_interview_shuffled.json"
                )
            )
            tasks.append(
                need_p.llm_pipeline_alt(
                    fidx, observations=dataset, seed=[], num_iterations=5
                )
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        fidx = args.fidx
        for i in range(3,args.num_sessions):
            dataset = json.load(
                open(
                    f"../data/{fidx}/pipeline_outputs/session-{i}/observations_gpt-4.1.json"
                )
            )
            results = await need_p.llm_pipeline_alt(
                fidx, observations=dataset, seed=[], session_num=i
            )

    # results = await need_p.baseline_pipeline(test_dataset.SMALL_TESTSET)

    # os.makedirs(args.output_dir, exist_ok=True)
    # out_path = os.path.join(args.output_dir, "41.json")
    # with open(out_path, "wb") as f:
    #     f.write(orjson.dumps(results, option=orjson.OPT_INDENT_2))
    # print("Saved:", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Clusterer on transcripts.")
    parser.add_argument("--user", type=str, default="Dora")
    parser.add_argument("--fidx", type=str, default="dora_pilot")
    parser.add_argument("--num_sessions", type=int, default=6)
    parser.add_argument(
        "--model", type=str, default="gpt-4o-mini", help="OpenAI model name."
    )
    parser.add_argument("--bs", type=int)
    parser.add_argument("--type", type=str)
    args = parser.parse_args()
    # asyncio.run(main(args))
    asyncio.run(main(args))


"""
 cluster_members = clusters[i].members
                    # cluster_ids = set([str(x) for x in cluster_members])
                    # available_ids = all_ids - cluster_ids
                    # random_id = random.choice(list(available_ids)) if available_ids else None
                    # random_obs = f"ID {random_id} | {output_observations[random_id]['description']}"
                    merged_obs = [output_observations[str(x)] for x in cluster_members]
                    # formatted_merged_obs = [f"ID {x['id']} | {x['description']}" for x in merged_obs]
                    # formatted_merged_obs.append(random_obs)
                    # random.shuffle(formatted_merged_obs)
                    # formatted_merged_obs = "\n".join(formatted_merged_obs)

                #     # INTRUSION TEST
                #     prompt = observer.INTRUSION_TEST.format(observations=formatted_merged_obs)
                #     intrusion_tasks.append(self._guarded_call(self.client, prompt, "gpt-4o", resp_format=IntrusionResponse))
                # intrusion_resps = await asyncio.gather(*intrusion_tasks, return_exceptions=True)
                # for intrusion_resp, observation in zip(intrusion_resps, r.observations):
                    is_general, is_cohesive = True, True
                #     cluster_members = clusters[i].members
                    
                #     print(cluster_members, intrusion_resp)
                #     intruder = intrusion_resp.intruder
                    
                #     if intruder in cluster_members:
                #         is_cohesive = False
                """
