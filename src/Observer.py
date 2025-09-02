from ast import Dict
import os
import random
import hdbscan

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
from prompts import need_finder, reflection_module, observer, gum, test_dataset
from response_formats import RelationsResponse, ObservationResponse, ClusterResponse
from dotenv import load_dotenv
from BM25 import BM25NeedsIndex
from EmbeddingStore import EmbeddingsStore
from typing import List, Dict
from prompts import test_dataset
USER = "Dora"

class Observer():
    def __init__(self, model, params):
        load_dotenv()
        self.model = model
        self.count = 0 
        self.name = params['name']
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sync_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sim_threshold = 0.8
        st_model = "all-MiniLM-L6-v2"
        self.embed_store = EmbeddingsStore(
            st_model_name=st_model,
            sim_threshold=self.sim_threshold,
            device="cpu",
            ann_max=int(os.getenv("ANN_MAX_ELEMENTS", "200000"))
        )
        self.already_merged = set([])
        # Speed/quality knobs
        self.need_index = BM25NeedsIndex({})
        
        self.prompt2name = {
            'baseline': need_finder.BASELINE_PROMPT,
            'baseline_image': need_finder.BASELINE_IMAGE_PROMPT,
            'text': need_finder.NEEDFINDING_TEXT_PROMPT,
            'text_conf': need_finder.NEEDFINDING_TEXT_PROMPT_CONF,
            'text_image': need_finder.NEEDFINDING_TEXT_IMAGE_PROMPT
        }
        self.all_needs = {}
        self.final_needs = []
        self.tokenizer = lambda text: re.findall(r"\w+", text.lower())

        # Async control
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))

    @staticmethod
    def _load_markdown(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

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
                    "group_id": gid
                }
                output.append(item)
                self.count += 1
        return output 
    
    def _get_actions(self, fnames):
        actions = []
        for idx, fname in enumerate(fnames):
            actions.append(f"{idx + 1}.")
            actions.append("Transcription of what is on the user's screen:")
            actions.append(Observer._load_markdown(f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/40/{fname}'))
            actions.append("Summary of actions:")
            actions.append(Observer._load_markdown(f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/40/{fname}'))
        actions = '\n'.join(actions)
        return actions 

    def _handle_identical(self, new_obs:dict, targets: list[str]):
        new_evidence = new_obs['evidence']
        # add new source's evidence to existing propisitions
        for tid_ in targets:
            tid_ = str(tid_)
            tgt = self.all_needs[tid_]
            self.all_needs[tid_]['evidence'].extend(new_evidence)

    def _handle_different(self, new_obs:dict, description_only:str):
        if not self._exists_id(new_obs["id"]):
            self.all_needs[new_obs['id']] = new_obs
            self.need_index.add_needs([(new_obs["id"], description_only)])
        return 
    
    def _handle_similar(self, new_obs: dict, source: str, targets: list[str]):
        parts = []
        max_generality = 0
        if not self._exists_id(source):
            self.all_needs[source] = new_obs
            src_item = new_obs
        else:
            src_item = self.all_needs.get(source)

        if src_item:
            evidence = ' '.join(src_item['evidence'])
            if src_item['generality'] > max_generality:
                max_generality = src_item['generality']
            parts.append(f"ID: {src_item['id']} | {src_item['description']}: {evidence} | Generality: {src_item['generality']}")

        for tid_ in targets:
            tgt = self.all_needs.get(tid_)
            if tgt:
                evidence = ' '.join(tgt['evidence'])
                if tgt['generality'] > max_generality:
                    max_generality = tgt['generality']
                parts.append(f"ID: {tgt['id']} | {tgt['description']}: {evidence} | Generality: {tgt['generality']}")
                
        if parts:
            formatted = "\n".join(parts)
            if max_generality >= 6:
                merge_prompt = observer.FEEL_PROMPT.format(body=formatted)
                print(merge_prompt)
            else:
                merge_prompt = observer.SIMPLIFIED_REVISE_PROMPT.format(body=formatted)
            return merge_prompt
        else:
            return None
    
    async def observer_pipeline(self, input_dir):
        prompt = observer.OBSERVE_PROMPT

        files = sorted(
            [f for f in os.listdir(input_dir) if f.endswith(".md")],
            key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
        )

        window_size = 5
        to_check = []
        print("Observer Pipeline", len(files))
        for index in range(0, len(files), 5):
            try:
                fnames = files[index: index + window_size]
                start_file = fnames[0]
                tid = os.path.splitext(start_file)[0]
                iter_t0 = time.perf_counter()
                # try:
                # ----- Load and propose -----
                actions = self._get_actions(fnames)
                input_prompt = prompt.format(body=actions)
                new_needs = await self._guarded_call(self.client, input_prompt, self.model, resp_format=ObservationResponse)

                # ----- Assemble candidates -----
                cand_items = []
                
                for prop in new_needs.observations:
                    nid = f"{self.count}"
                    item = {"id": nid, "description": prop.description, "evidence": [prop.evidence], "generality": prop.generality}
                    self.count += 1
                    cand_items.append(item)
                
                # ----- Batch embed + ANN pre-filter -----
                desc_only = [f"{c['description']}" for c in cand_items]
                vecs = self.embed_store.encode(desc_only, batch_size=int(os.getenv("EMB_BATCH", "256")))
                keep_mask = self.embed_store.batch_add_if_new([c["id"] for c in cand_items], vecs)
                kept = int(np.sum(keep_mask)) if len(keep_mask) else 0
                print(f"[{tid}] kept {kept}/{len(cand_items)}")

                # Prepare survivors but DO NOT add to BM25 yet
                survivors = [(c, do) for keep, c, do in zip(keep_mask, cand_items, desc_only) if keep]
                if not survivors:
                    print(f"[{tid}] skip: all proposed needs failed ANN threshold")
                    continue

                if len(self.need_index.needs) == 0:
                    for c, t in survivors:
                        nid = c['id']
                        self.all_needs[nid] = c
                        self.need_index.add_needs([(nid, t)])
                else:
                    for new_obs, do in survivors:
                        # --- (a) BM25 retrieval body for THIS survivor only (no self in index yet) ---
                        input = f"ID: {new_obs['id']} | {new_obs['description']}"
                        retrieved = self._search_bm25(do, top_k=3) # use description only to search for retrieved
                        existing = []
                        for r in retrieved:
                            existing.append(f"ID: {r['id']} | {r['description']}")

                        classifier_prompt = observer.SIMILAR_PROMPT.format(new=input, existing=existing)
                        # print(classifier_prompt)
                        resp = await self._guarded_call(self.client, classifier_prompt, self.model, resp_format=RelationsResponse)
                        print('Relations', resp)

                        to_merge_ids = []
                        merge_tasks = []
                        relation = resp.relations
                        label = relation.score
                        s, t_targets = str(relation.source), relation.target
                        t_ids = [str(x) for x in (t_targets if isinstance(t_targets, list) else [t_targets])]

                        if label < 7:
                            self._handle_different(new_obs, do) 
                        elif label >= 7:
                            if t_targets:
                                self._handle_identical(new_obs, t_targets)
                        # else:
                        #     mids = sorted(list(set([s] + t_ids)))
                        #     to_merge = "-".join(mids)
                        #     if to_merge in self.already_merged:
                        #         continue

                        #     merge_prompt = self._handle_similar(new_obs, s, t_ids)
                            
                        #     if merge_prompt is not None:
                        #         merge_tasks.append(
                        #             self._guarded_call(self.client, merge_prompt, "o3", resp_format=ObservationResponse)
                        #         )
                        #         self.already_merged.add(to_merge)
                        #         to_merge_ids.append(mids)

                        #     merged_needs = []
                        #     if merge_tasks:
                        #         merged_needs = await asyncio.gather(*merge_tasks, return_exceptions=True)

                        #     merges_added = 0
                        #     for midx, merge_res in enumerate(merged_needs):
                        #         if isinstance(merge_res, Exception) or merge_res is None:
                        #             continue
                        #         gid = uuid.uuid4()
                        #         merged_ids = to_merge_ids[midx]
                        #         for mn in merge_res.observations:
                        #             nid = f"{self.count}"
                        #             generality = mn.generality 
                        #             vec = self.embed_store.encode([mn.description])[0]

                        #             is_general = True
                        #             # Check generality --> only add if generality is greater than targets
                        #             for mid in merged_ids:
                        #                 merged_obs = self.all_needs[mid]
                        #                 if merged_obs["generality"] > generality: 
                        #                     is_general = False 
                        #                     print("Discarded", merged_obs, mn.description)
                        #             if self.embed_store.add_if_new(nid, vec) and is_general:
                        #                 item = {
                        #                     "id": nid,
                        #                     "description": mn.description,
                        #                     "evidence": [mn.evidence],
                        #                     "merged": merged_ids,
                        #                     "generality": generality,
                        #                     "group_id": gid
                        #                 }

                        #                 self.all_needs[nid] = item
                        #                 self.need_index.add_needs([(nid, mn.description)])
                        #                 self.count += 1
                        #                 merges_added += 1

                                            # REMOVE FROM BM-25
                                            # for merged_id in merged_ids:
                                            #     self.need_index.remove_need(merged_id)
            except Exception as e:
                print(f"[{tid}] ERROR: {e}")
            
            out_path = "/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/text_summary_gpt-4o_gum_reflect/40_granular.json"
            with open(out_path, "wb") as f:
                f.write(orjson.dumps(self.all_needs, option=orjson.OPT_INDENT_2))
            # out_path = "/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/text_summary_gpt-4o_gum_reflect/41_prompts_o3.json"
            # with open(out_path, "wb") as f:
            #     f.write(orjson.dumps(to_check, option=orjson.OPT_INDENT_2))
            print(f"[{tid}] done. total_needs={len(self.all_needs)} | iter={time.perf_counter()-iter_t0:.2f}s")
            # if int(tid) >= 100:
            #     break
        return self.all_needs
    
    def _format_observations(self, observations: List[dict]) -> str:
        output = []
        for o in observations:
            if 'text' in o:
                output.append(f"ID {o['id']} | {o['text']}")
            else: 
                output.append(f"ID {o['id']} | {o['description']} Evidence:{o['evidence']}")
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
            if score >= threshold: union(i, j)

        # Group items by their root parent
        clusters = {}
        for i in range(n):
            root = find(i)
            clusters.setdefault(root, set()).add(items[i])

        return list(clusters.values())

    async def llm_pipeline(self, observations: List[dict], num_iterations: int = 10, seed: List[str] =[]) -> Dict:
        output_observations = {}
        max_id = 0

        # For test dataset, insert existing granular observations into the output
        for o in observations:
            if 'generality' in o:
                generality = o['generality']
                evidence = o['evidence'] 
            else:
                generality = 0
                evidence = []
            if 'text' in o:
                description = o['text']
            else:
                description = o['description']
            output_observations[str(o['id'])] = {
                'id': str(o['id']),
                'description': description,
                'generality': generality, 
                'evidence': evidence
            }
            max_id = max(max_id, int(o['id']))
        count = 0
        
        uncovered_ids = set([str(o['id']) for o in observations])
        while(len(observations) >= 2 and count < num_iterations):
            fmt_observations = self._format_observations(observations)
            if len(seed) > 0:
                prompt = observer.LLM_CLUSTER_PROMPT_SEED.format(observations=fmt_observations, seed=seed)
            else:
                prompt = observer.LLM_CLUSTER_PROMPT.format(observations=fmt_observations)
            resp = await self._guarded_call(self.client, prompt, self.model, resp_format=ClusterResponse) 
            print(resp)
            tasks = []
            clusters = resp.clusters

            # CLUSTER RESPONSES 
            for cluster in clusters:
                members = [output_observations[str(member)] for member in cluster.members]
                for m in members:
                    if str(m['id']) in uncovered_ids:
                        uncovered_ids.remove(str(m['id']))
                fmt_members = self._format_observations(members)
                prompt = observer.LLM_INSIGHT_PROMPT.format(observations=fmt_members, reasoning=cluster.evidence)
                tasks.append(self._guarded_call(self.client, prompt, self.model, resp_format=ObservationResponse))
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            print(resps)
            new_observations = []
            # SAVE OBSERVATIONS
            for i, r in enumerate(resps):
                for observation in r.observations:
                    cluster_members = clusters[i].members
                    merged_obs = [output_observations[str(x)] for x in cluster_members]
                    cohesion = observation.cohesion
                    generality = observation.generality
                    is_general, is_cohesive = True, True

                    for m in merged_obs:
                        if 'generality' in m and m["generality"] > generality: 
                            is_general = False 
                            print("Discarded Generality", m)
                            break
                        if 'cohesion' in m and m["cohesion"] < cohesion:
                            is_cohesive = False 
                            print("Discarded Cohesion", m)
                            break
                    if is_general and is_cohesive and len(cluster_members) > 1:
                        obs = {
                            'id': str(max_id + 1),
                            'description': observation.description,
                            'generality': observation.generality,
                            'evidence': [observation.evidence],
                            'merged': [str(x) for x in cluster_members]
                        }
                        output_observations[obs['id']] = obs
                        new_observations.append(obs)
                        max_id += 1
            next_rounds_observations = []
            for o in observations:
                if str(o['id']) in uncovered_ids:
                    next_rounds_observations.append(o)
            next_rounds_observations.extend(new_observations)
            observations = next_rounds_observations
            if len(seed) > 0:
                out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/perturbation_1_{self.model}_seed.json"
            else:
                out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/perturbation_1_{self.model}.json"
            data = {str(k): v for k, v in output_observations.items()}

            with open(out_path, "wb") as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            print(f"Iteration: {count} | Next Level: {len(observations)}")
            count += 1
        return output_observations

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
    
    async def baseline_pipeline(self, observations: List[dict], max_iters: int = 5) -> Dict:
        print(observations)
        output_observations = {}
        max_id = 0
        for o in observations:
            if 'generality' in o:
                generality = o['generality']
                evidence = o['evidence'] 
            else:
                generality = 0
                evidence = []
            if 'text' in o:
                description = o['text']
            else:
                description = o['description']
            output_observations[str(o['id'])] = {
                'id': str(o['id']),
                'description': description,
                'generality': generality, 
                'evidence': evidence
            }
            max_id = max(max_id, int(o['id']))

        props, data = [], []
        for o in observations:
            props.append(f"{o['text']}")
            data.append(o)
        embeddings = get_openai_embeddings(self.sync_client, props, "text-embedding-3-large")
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric='euclidean')
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
            tasks.append(self._guarded_call(self.client, prompt, self.model, resp_format=ObservationResponse))
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        print(resps)
        for resp, c in zip(resps, clusters):
            for observation in resp.observations:
                output_observations[str(max_id + 1)] = {
                    'id': str(max_id + 1),
                    'description': observation.description,
                    'generality': observation.generality,
                    'evidence': [observation.evidence],
                    'merged': [str(x['id']) for x in clusters[c]]
                }
                max_id += 1
        
        out_path = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/baseline/synthetic-small_{self.model}.json"
        data = {str(k): v for k, v in output_observations.items()}

        with open(out_path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        return resps




async def main(args):
    params = {
        'name': args.name,
        'user': 'Dora'
    }
    need_p = Observer(args.model, params)
    print("Observe")
    # results = await need_p.observer_pipeline(args.input_dir + "/summaries/40")
    # dataset = json.load(open(f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/text_summary_gpt-4o_gum_reflect/41_granular.json"))
    # Convert the dataset dictionary to a list of its values and shuffle the order
    # dataset_list = list(dataset.values())
    # random.shuffle(dataset_list)
    # print(dataset_list)
    perturbations = json.load(open(f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/perturbations/1_shuffled.json"))
    results = await need_p.llm_pipeline(perturbations)
    # results = await need_p.llm_pipeline(test_dataset.TESTSET, seed=[])
    # results = await need_p.baseline_pipeline(test_dataset.SMALL_TESTSET)

    # os.makedirs(args.output_dir, exist_ok=True)
    # out_path = os.path.join(args.output_dir, "41.json")
    # with open(out_path, "wb") as f:
    #     f.write(orjson.dumps(results, option=orjson.OPT_INDENT_2))
    # print("Saved:", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Observer on transcripts.")
    parser.add_argument("--name", type=str, required=True,
                        help="Prompt type to use for need-finding.")
    parser.add_argument("--action_input", type=str, required=True,
            choices=["summary", "transcript", "video", "action"])
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="OpenAI model name.")
    parser.add_argument("--input_dir", type=str, required=True,
                        help="Path to dataset")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Path to save results.")
    parser.add_argument("--bs", type=int)
    parser.add_argument("--is_test", type=int, required=True)
    parser.add_argument("--run_all", type=int, required=True)
    parser.add_argument("--window_size", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(main(args))
