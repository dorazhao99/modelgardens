import os
import json
import orjson
import numpy as np
import asyncio
import hdbscan
import argparse
import pandas as pd
import text_lloom.workbench as wb
from IPython.display import display
from typing import List
from prompts import observer, need_finder
from response_formats import ClusterResponse, InsightResponse, CohesionResponse, \
    DuplicateResponse, ClusterNeedResponse, GeneralJudge
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
from utils import call_gpt, get_openai_embeddings

load_dotenv()


class MetaClusterer:
    def __init__(self, fidx: str, model: str, name: str, num_sessions: int, dup_threshold: float = 0.9):
        self.fidx = fidx
        self.prefix = f"../data/{fidx}"
        self.model = model
        self.name = name
        self.num_sessions = num_sessions
        self.dup_threshold = dup_threshold
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sync_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        np.random.seed(123)

    def _save_file(self, output: List[dict], filename: str):
        with open(filename, "wb") as f:
            f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)

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
    
    def _format_insights(self, insights: List[dict]) -> str:
        return "\n".join(
            [
                f"ID {i['id']} | {i['theme']}: {i['description']}\nEvidence: {i['evidence']}"
                for i in insights
            ]
        )

    async def cluster_observations(
        self, observations: List[dict], existing_clusters: List[dict] = []
    ) -> List[dict]:
        fmt_observations = self._format_observations(observations)
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

    def _update_ids(self, observations: List[dict], session_num: int) -> List[dict]:
        for o in observations:
            o['id'] = f"{session_num}-{str(o['id'])}"
        return observations
    
    async def label_interesting(self, model: str = "o4-mini") -> List[dict]:
        tasks = []
        clusters = json.load(open(f"{self.prefix}/pipeline_outputs/session-meta/cluster_motivation_{model}.json"))
        for n in clusters:
            new_insight = f"{n['cluster_theme']}: {n['core_need']}\n{n['motivation']}. What this reveals: {n['what_this_reveals']}"
            prompt = observer.JUDGE_INTERESTING_PROMPT.format(new_insight=new_insight)
            tasks.append(
                self._guarded_call(
                    self.client, prompt, "gpt-5", resp_format=GeneralJudge
                )
            )
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for i, resp in enumerate(resps):
            clusters[i]['interesting'] = resp.judgement
            clusters[i]['reasoning'] = resp.reason
        save_file = f"{self.prefix}/pipeline_outputs/session-meta/cluster_motivation_{model}.json"
        os.makedirs(os.path.dirname(save_file), exist_ok=True)
        self._save_file(clusters, save_file)
        return clusters
    
    async def cluster_meta(
        self, merged_only: bool = False, num_iterations: int = 10
    ) -> List[dict]:
        all_to_cluster = []
        output_observations = {}

        for session in range(self.num_sessions):
            to_cluster = []
            observations = json.load(open(f"{self.prefix}/pipeline_outputs/session-{session}/cluster_o4-mini.json"))
            for o in observations:
                if 'merged' in observations[o]:
                    output_observations[o] = observations[o]
                    to_cluster.append(observations[o])
                
            merged_ids = []
            all_ids = set()
            
            if not merged_only:
                for o in observations:
                    if 'merged' in observations[o]: merged_ids.extend(observations[o]['merged'])
                    all_ids.add(int(observations[o]['id']))
                merged_ids = [int(m) for m in merged_ids]
                merged_ids = list(set(merged_ids))
                unmerged_ids = all_ids - set(merged_ids)
                unmerged_obs = [observations[o] for o in observations if int(o) in unmerged_ids]
            if not merged_only:
                to_cluster.extend(unmerged_obs)
            all_to_cluster.extend(to_cluster)
        insights = []
        is_saturated = False
        count = 0 
        while count < num_iterations and not is_saturated:
            clusters = await self.cluster_observations(all_to_cluster)

            # Step 2: Get Insights
            tasks = []
            
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

            # Step 3: Judge Cohesion
            cohesion_tasks = []
            duplicate_tasks = []
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
                input_obs = [x["description"] for x in merged_obs]
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
                    fmt_insights = self._format_insights(insights)
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

            num_duplicates, total_observations = 0, 0
            # Step 4: Save Observations
            max_id = 0
            for i, r in enumerate(resps):
                total_observations += 1
                theme = r.theme
                description = r.description
                evidence = r.evidence
                cluster_members = clusters[i].members
                cohesion = cohesion_resps[i].cohesion
                confidence = cohesion_resps[i].confidence

                if count > 0:
                    is_duplicate = duplicate_resps[i].judgement
                else:
                    is_duplicate = False

                if is_duplicate:
                    dup_id = f"meta-{str(duplicate_resps[i].id)}"
                    if dup_id in output_observations:
                        num_duplicates += 1
                        output_observations[dup_id]["evidence"].append(
                            evidence
                        )
                        if "merged" in output_observations[dup_id]:
                            existing_ids = set(
                                output_observations[dup_id]["merged"]
                            )
                        else:
                            existing_ids = set()
                        new_ids = set([str(x) for x in cluster_members])
                        output_observations[dup_id]["merged"] = list(
                            existing_ids.union(new_ids)
                        )
                    else:
                        print("Duplicate not found", dup_id)
                        obs = {
                            "id": f"meta-{str(max_id + 1)}",
                            "theme": theme,
                            "description": description,
                            "cohesion": cohesion,
                            "confidence": confidence,
                            "evidence": [evidence],
                            "merged": [str(x) for x in cluster_members],
                        }
                        output_observations[obs["id"]] = obs
                        max_id += 1
                        insights.append(obs)
                    # Add relevant ids to duplicate observation
                else:
                    obs = {
                        "id": f"meta-{str(max_id)}",
                        "theme": theme,
                        "description": description,
                        "cohesion": cohesion,
                        "confidence": confidence,
                        "evidence": [evidence],
                        "merged": [str(x) for x in cluster_members],
                    }
                    output_observations[obs["id"]] = obs
                    max_id += 1
                    insights.append(obs)

            # duplicate ratio
            dup_ratio = num_duplicates / total_observations
            print("Duplicate ratio", dup_ratio)
            if dup_ratio > self.dup_threshold:
                is_saturated = True
                print("Saturated due to duplicate ratio", dup_ratio)
            count += 1
            np.random.shuffle(all_to_cluster)
        save_file = f"{self.prefix}/pipeline_outputs/session-meta/cluster_{self.model}.json"
        os.makedirs(os.path.dirname(save_file), exist_ok=True)
        self._save_file(output_observations, save_file)
        return clusters
    
    async def cluster_interesting_only(self):
        hypotheses_to_cluster = []
        all_hypotheses = json.load(open(f"{self.prefix}/pipeline_outputs/session-meta/interesting_only_hypotheses.json"))
        clustered_observations = []
        for obs in all_hypotheses:
            hypotheses = obs['hypotheses']
            for hypothesis in hypotheses:
                hypotheses_to_cluster.append(f"{hypothesis['text']}: {hypothesis['description']}")
                clustered_observations.append(obs)
        return hypotheses_to_cluster, clustered_observations


    async def cluster_motivation(self, most_likely_hypotheses: bool = False):
        hypotheses_to_cluster = []
        clustered_observations = []
        weights = []
        for session in range(self.num_sessions):
            if most_likely_hypotheses:
                observations = json.load(open(f"{self.prefix}/pipeline_outputs/session-{session}/most_likely_hypotheses.json"))
            else:
                observations = json.load(open(f"{self.prefix}/pipeline_outputs/session-{session}/all_hypotheses.json"))
            for obs in observations:
                hypotheses = obs['hypotheses']
                if most_likely_hypotheses:
                    hypotheses = [hypotheses]
                for hypothesis in hypotheses:
                    if 'weight' in hypothesis:
                        if hypothesis['weight']:
                            weights.append(hypothesis['weight'])
                            hypotheses_to_cluster.append(f"{hypothesis['text']}: {hypothesis['description']}")
                            clustered_observations.append(obs)
                    else:
                        weights.append(-1)
                        hypotheses_to_cluster.append(f"{hypothesis['text']}: {hypothesis['description']}")
                        clustered_observations.append(obs)
        return hypotheses_to_cluster, clustered_observations, weights
    
    async def lloom_cluster(self, hypotheses_to_cluster: List[str], clustered_observations: List[dict], weights: List[int]):
        data = []
        for i, h, in enumerate(hypotheses_to_cluster): 
            data.append({'text': h, 'id': i})
        df = pd.DataFrame(data)
        distill_model = wb.OpenAIModel(
            name="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        synth_model = wb.OpenAIModel(
            name="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        score_model = wb.OpenAIModel(
            name="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        l = wb.lloom(df=df, text_col="text", id_col="id", distill_model=distill_model, synth_model=synth_model, score_model=score_model)
        await l.gen_auto()
        export_df = l.export_df(include_outliers=True)
        print(export_df)
        export_df.to_csv(f"{self.prefix}/pipeline_outputs/session-meta/lloom_cluster_{self.model}.csv", index=False)

        
    async def hdbscan_cluster(self, hypotheses_to_cluster: List[str], clustered_observations: List[dict], weights: List[int],
        is_verbose: bool = True, save_file: str = None) -> List[dict]:
        hdbscan_clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean", cluster_selection_method="leaf")
        embeddings = get_openai_embeddings(
            self.sync_client, hypotheses_to_cluster, "text-embedding-3-large"
        )
        labels = hdbscan_clusterer.fit_predict(embeddings)
        # Organize hypotheses by cluster with their associated observations
        clusters = {}
        for i, (hypothesis, label) in enumerate(zip(hypotheses_to_cluster, labels)):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append({
                'hypothesis': hypothesis,
                'observation': clustered_observations[i],
                'weight': weights[i]
            })
        
        # Print each cluster and its hypotheses with associated observations
        tasks = []
        cluster_outputs = []
        cluster_weights = []
        has_print = False
        for cluster_id, items in clusters.items():
            if cluster_id != -1:
                if is_verbose:
                    print(f"\n{'='*80}")
                    print(f"CLUSTER {cluster_id} ({len(items)} items)")
                    print(f"{'='*80}")

                # Make sure cluster items are not all from the same observation 
                if all(item['observation'] == items[0]['observation'] for item in items):
                    print("All items are from the same observation")
                    continue

                prompt_input = []
                weight = []
                for i, item in enumerate(items, 1):
                    if 'supporting_observations' in item['observation']:
                        evidence = [i['description'] for i in item['observation']['supporting_observations']]
                        evidence = " ".join(evidence)
                    else:
                        evidence = " ".join(item['observation']['evidence'])
                    info = f"{i}. OBSERVATION: {item['observation']['observation']} The reason for this behavior is because of {item['hypothesis']}\n\nEVIDENCE: {evidence}\n"
                    prompt_input.append(info)
                    if 'weight' in item:
                        weight.append(item['weight'])
                    else:
                        weight.append(-1)
                cluster_weights.append(weight)
                prompt_input = "\n".join(prompt_input)
                print(prompt_input)
        #         task_input = need_finder.HYPOTHESIS_CLUSTER_PROMPT_V2.format(
        #             input=prompt_input
        #         )
        #         if is_verbose and not has_print:
        #             print(prompt_input)
        #             has_print = True

        #         cluster_outputs.append(items)
        #         tasks.append(
        #             self._guarded_call(
        #                 self.client,
        #                 task_input,
        #                 "gpt-5",
        #                 resp_format=ClusterNeedResponse,
        #             )
        #         )
        # cluster_resps = await asyncio.gather(*tasks, return_exceptions=True)
        # output = []
        # for i, resp in enumerate(cluster_resps):
        #     output.append({
        #         "name": resp.name,
        #         "need": resp.need,
        #         "reasoning": resp.reasoning,
        #         "motivation": resp.motivation,
        #         "behaviors": resp.behaviors,
        #         "implications": resp.implications,
        #         "cluster_items": cluster_outputs[i],
        #     })
        
        # os.makedirs(os.path.dirname(f"{self.prefix}/{save_file}"), exist_ok=True)
        # self._save_file(output, f"{self.prefix}/{save_file}")
        return clusters

    async def sandbox(self, hypotheses_to_cluster: List[str], clustered_observations: List[dict], weights: List[int],
            is_verbose: bool = True) -> List[dict]:
            hdbscan_clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean", cluster_selection_method="leaf")
            embeddings = get_openai_embeddings(
                self.sync_client, hypotheses_to_cluster, "text-embedding-3-large"
            )
            labels = hdbscan_clusterer.fit_predict(embeddings)
            # Organize hypotheses by cluster with their associated observations
            clusters = {}
            for i, (hypothesis, label) in enumerate(zip(hypotheses_to_cluster, labels)):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append({
                    'hypothesis': hypothesis,
                    'observation': clustered_observations[i],
                    'weight': weights[i]
                })
            
            # Print each cluster and its hypotheses with associated observations
            tasks = []
            cluster_outputs = []
            cluster_weights = []
            has_print = False
            for cluster_id, items in clusters.items():
                if cluster_id != -1:
                    if is_verbose:
                        print(f"\n{'='*80}")
                        print(f"CLUSTER {cluster_id} ({len(items)} items)")
                        print(f"{'='*80}")

                    # Make sure cluster items are not all from the same observation 
                    if all(item['observation'] == items[0]['observation'] for item in items):
                        print("All items are from the same observation")
                        continue

                    prompt_input = []
                    weight = []
                    for i, item in enumerate(items, 1):
                        if 'supporting_observations' in item['observation']:
                            evidence = [i['description'] for i in item['observation']['supporting_observations']]
                            evidence = " ".join(evidence)
                        else:
                            evidence = " ".join(item['observation']['evidence'])
                        info = f"{i}. OBSERVATION: {item['observation']['observation']} The reason for this behavior is because of {item['hypothesis']}\n\nEVIDENCE: {evidence}\n"
                        prompt_input.append(info)
                        if 'weight' in item:
                            weight.append(item['weight'])
                        else:
                            weight.append(-1)
                    cluster_weights.append(weight)
                    prompt_input = "\n".join(prompt_input)
                    task_input = need_finder.HYPOTHESIS_CLUSTER_PROMPT_V2.format(
                        input=prompt_input
                    )
                    if is_verbose and not has_print:
                        print(prompt_input)
                        has_print = True

                    cluster_outputs.append(items)
                    tasks.append(
                        self._guarded_call(
                            self.client,
                            task_input,
                            "gpt-5",
                            resp_format=ClusterNeedResponse,
                        )
                    )
                    break
            cluster_resps = await asyncio.gather(*tasks, return_exceptions=True)
            print(cluster_resps)
            


async def loop():
    model = "o4-mini"
    # pilots = [{'fidx': 'dora_pilot', 'name': 'Dora', 'num_sessions': 6}, {'fidx': 'msl_pilot', 'name': 'Michelle', 'num_sessions': 4}, {'fidx': 'mjr_pilot', 'name': 'Michael', 'num_sessions': 4}]
    # for pilot in [{'fidx': 'dora_pilot', 'name': 'Dora', 'num_sessions': 6}]:
    for pilot in [{'fidx': 'dora_pilot', 'name': 'Dora', 'num_sessions': 6}]:
        meta_clusterer = MetaClusterer(fidx=pilot['fidx'], model=model, name=pilot['name'], num_sessions=pilot['num_sessions'])
        # await meta_clusterer.cluster_meta(merged_only=True)
        hypotheses_to_cluster, clustered_observations = await meta_clusterer.cluster_motivation(most_likely_hypotheses=False)
        save_file = f"pipeline_outputs/session-meta/cluster_motivation_{model}_hypothesis2.json"
        await meta_clusterer.hdbscan_cluster(hypotheses_to_cluster, clustered_observations, is_verbose=True, save_file=save_file)
        # # # await meta_clusterer.cluster_motivation(is_verbose=True, most_likely_hypotheses=False, save_file=save_file)
        # await meta_clusterer.label_interesting()
async def main(args):
    meta_clusterer = MetaClusterer(fidx=args.fidx, model=args.model, name=args.name, num_sessions=args.num_sessions)
    hypotheses_to_cluster, clustered_observations, weights = await meta_clusterer.cluster_motivation(most_likely_hypotheses=False)
    # await meta_clusterer.lloom_cluster(hypotheses_to_cluster, clustered_observations, weights)
    save_file = f"pipeline_outputs/session-meta/cluster_motivation_{args.model}_hypothesis_colloquial.json"
    await meta_clusterer.hdbscan_cluster(hypotheses_to_cluster, clustered_observations, weights, is_verbose=True, save_file=save_file)

async def prompt_sandbox(args):
    meta_clusterer = MetaClusterer(fidx=args.fidx, model=args.model, name=args.name, num_sessions=args.num_sessions)
    hypotheses_to_cluster, clustered_observations, weights = await meta_clusterer.cluster_motivation(most_likely_hypotheses=False)
    sandbox_output = await meta_clusterer.sandbox(hypotheses_to_cluster, clustered_observations, weights, is_verbose=True)
    return sandbox_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MetaClusterer on transcripts.")
    parser.add_argument("--fidx", type=str, default="dora_pilot", help="Dataset index.")
    parser.add_argument("--name", type=str, default="Dora", help="User name.")
    parser.add_argument("--num_sessions", type=int, default=6, help="Number of sessions.")
    parser.add_argument("--model", type=str, default="o4-mini", help="Model name.")
    args = parser.parse_args()
    asyncio.run(main(args))
