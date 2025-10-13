import json
import os
import argparse
import asyncio
import time
import numpy as np
import re
import orjson
import pdb
from prompts import observer
from response_formats import ObservationResponse, RelationsResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv
from BM25 import BM25NeedsIndex
from EmbeddingStore import EmbeddingsStore
from utils import call_gpt
load_dotenv()

class Transcriber():
    def __init__(self, model: str, index: str, name: str, save_file: str):
        self.name = name
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.all_actions = {}
        self.model = model
        self.index = index
        self.actions_index = BM25NeedsIndex({})
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.save_file = save_file
        self.count = 0
        self.sim_threshold = 0.8
        st_model = "all-MiniLM-L6-v2"
        self.embed_store = EmbeddingsStore(
            st_model_name=st_model,
            sim_threshold=self.sim_threshold,
            device="cpu",
            ann_max=int(os.getenv("ANN_MAX_ELEMENTS", "200000"))
        )


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
        return self.actions_index.search(query, top_k=top_k)

    async def _guarded_call(self, *args, **kwargs):
        async with self._sem:
            return await call_gpt(*args, **kwargs)

    def _exists_id(self, nid: str) -> bool:
        return nid in self.all_actions

    def _get_actions(self, fnames: list[str], include_transcript: bool = False):
        actions = []
        for fname in fnames:
            # INSERT_YOUR_CODE
            creation_time = os.path.getctime(f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/{self.index}/{fname}')
            formatted_creation_time = time.strftime("%m-%d-%Y (%H:%M:%S)", time.localtime(creation_time))
            actions.append(f"User's Actions at {formatted_creation_time}")
            actions.append(Transcriber._load_markdown(f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/summaries/{self.index}/{fname}'))
            if include_transcript:
                actions.append(f"Transcription of User's Screen")
                actions.append(Transcriber._load_markdown(f'/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{self.index}/{fname}'))
        actions = '\n'.join(actions)
        pdb.set_trace()
        return actions

    def _handle_identical(self, new_obs:dict, targets: list[str]):
        new_evidence = new_obs['evidence']
        # add new source's evidence to exsting propisitions
        for tid_ in targets:
            tid_ = str(tid_)
            tgt = self.all_actions[tid_]
            self.all_actions[tid_]['evidence'].extend(new_evidence)

    def _handle_different(self, new_obs:dict, description_only:str):
        if not self._exists_id(new_obs["id"]):
            self.all_actions[new_obs['id']] = new_obs
            self.actions_index.add_needs([(new_obs["id"], description_only)])
        return 
    
    def _split_sessions(self, input_dir: str, files: list[str], threshold: int = 3600):
        """
            Split files into active sessions. 
            An active session is a period of time where there are continuous screenshots. 
        """
        sessions = []
        prev_timestamp = 0
        session_start = 0
        for i, file in enumerate(files):
            timestamp = os.path.getctime(os.path.join(input_dir, file))
            if i == 0:
                prev_timestamp = timestamp
            time_diff = timestamp - prev_timestamp
            assert time_diff >= 0, "Time difference is negative"
            if time_diff > threshold:
                sessions.append(files[session_start:i])
                session_start = i
            prev_timestamp = timestamp
        sessions.append(files[session_start:])
        return sessions
    
    async def observer_pipeline_batched(self, input_dir, end_file=-1, include_transcript=False, window_size=5):
        """
            Same as observer_pipeline, but it is batched
        """
        return 

    async def observer_pipeline(self, input_dir, end_file=-1, include_transcript=False, window_size=5):
        """
            
        """
        prompt = observer.OBSERVE_PROMPT
        files = sorted(
            [f for f in os.listdir(input_dir) if f.endswith(".md")],
            key=lambda x: os.path.getctime(os.path.join(input_dir, x))
        )

        # split files into active sessions 
        sessions = self._split_sessions(input_dir, files)
        if end_file == -1:
            end_file = len(files)

        print("Transcriber Pipeline", end_file)

        to_end_count = 0
        end_session = False

        for session in sessions:
            session_length = len(session)
            for index in range(0, session_length, window_size):
                try:
                    fnames = session[index: index + window_size]
                    start_file = fnames[0]
                    tid = os.path.splitext(start_file)[0]
                    print(tid)
                    iter_t0 = time.perf_counter()
                    # try:
                    # ----- Load and propose -----
                    actions = self._get_actions(fnames, include_transcript=include_transcript)
                    print(actions)
                    input_prompt = prompt.format(actions=actions, user_name=self.name)
                    new_needs = await self._guarded_call(self.client, input_prompt, self.model, resp_format=ObservationResponse)

                    # ----- Assemble candidates -----
                    cand_items = []
                    
                    for prop in new_needs.observations:
                        nid = f"{self.count}"
                        item = {"id": nid, "description": prop.description, "evidence": [prop.evidence], "interestingness": prop.interestingness, "confidence": prop.confidence}
                        # item = {"id": nid, "description": prop.description, "evidence": [prop.evidence], "generality": prop.generality, "interestingness": prop.interestingness}
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

                    if len(self.actions_index.needs) == 0:
                        for c, t in survivors:
                            nid = c['id']
                            self.all_actions[nid] = c
                            self.actions_index.add_needs([(nid, t)])
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

                            relation = resp.relations
                            label = relation.score
                            _, t_targets = str(relation.source), relation.target

                            if label < 8:
                                self._handle_different(new_obs, do) 
                            elif label >= 8:
                                if t_targets:
                                    self._handle_identical(new_obs, t_targets)
                    to_end_count += len(fnames)
                    if to_end_count >= end_file:
                        end_session = True
                        break
                except Exception as e:
                    print(f"[{tid}] ERROR: {e}")
            # Save at the end of each session
            print("Save to", self.save_file)
            with open(self.save_file, "wb") as f:
                f.write(orjson.dumps(self.all_actions, option=orjson.OPT_INDENT_2))
            print(f"[{tid}] done. total actions={len(self.all_actions)} | iter={time.perf_counter()-iter_t0:.2f}s")
            if end_session: break
        return self.all_actions


async def main(args):
    include_transcript = True
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    save_file = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/actions/{args.index}_{args.model}_{'both' if include_transcript else 'summary'}_tooleval_{timestamp}.json"
    t = Transcriber(args.model, str(args.index), args.user, save_file=save_file)
    input_dir = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/transcripts/{args.index}"

    results = await t.observer_pipeline(input_dir, end_file=args.end_file, include_transcript=include_transcript)
    with open(save_file, "wb") as f:
        f.write(orjson.dumps(results, option=orjson.OPT_INDENT_2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Observer on transcripts.")
    parser.add_argument("--index", type=str)
    parser.add_argument("--model", type=str, default="gpt-4o",
                        help="OpenAI model name.")
    parser.add_argument("--user", type=str, default="Dora")
    parser.add_argument("--end_file", type=int, default=-1)
    args = parser.parse_args()
    asyncio.run(main(args))

### Old Code ###
    # def _handle_similar(self, new_obs: dict, source: str, targets: list[str]):
    #     parts = []
    #     max_generality = 0
    #     if not self._exists_id(source):
    #         self.all_actions[source] = new_obs
    #         src_item = new_obs
    #     else:
    #         src_item = self.all_actions.get(source)

    #     if src_item:
    #         evidence = ' '.join(src_item['evidence'])
    #         if src_item['generality'] > max_generality:
    #             max_generality = src_item['generality']
    #         parts.append(f"ID: {src_item['id']} | {src_item['description']}: {evidence} | Generality: {src_item['generality']}")

    #     for tid_ in targets:
    #         tgt = self.all_actions.get(tid_)
    #         if tgt:
    #             evidence = ' '.join(tgt['evidence'])
    #             if tgt['generality'] > max_generality:
    #                 max_generality = tgt['generality']
    #             parts.append(f"ID: {tgt['id']} | {tgt['description']}: {evidence} | Generality: {tgt['generality']}")
                
    #     if parts:
    #         formatted = "\n".join(parts)
    #         if max_generality >= 6:
    #             merge_prompt = observer.FEEL_PROMPT.format(body=formatted)
    #             print(merge_prompt)
    #         else:
    #             merge_prompt = observer.SIMPLIFIED_REVISE_PROMPT.format(body=formatted)
    #         return merge_prompt
    #     else:
    #         return None
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
                #                 merged_obs = self.all_actions[mid]
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

                #                 self.all_actions[nid] = item
                #                 self.actions_index.add_needs([(nid, mn.description)])
                #                 self.count += 1
                #                 merges_added += 1

                                    # REMOVE FROM BM-25
                                    # for merged_id in merged_ids:
    #                                 #     self.actions_index.remove_need(merged_id)
    # except Exception as e: