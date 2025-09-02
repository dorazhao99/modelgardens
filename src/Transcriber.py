import json
import os
import asyncio
import time
import numpy as np
import orjson
from prompts import observer
from response_formats import ObservationResponse, RelationsResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class Transcriber():
    def __init__(self, filename, save_file):
        self.data = json.load(open(filename))
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))
        self.save_file = save_file
        self.all_actions = {}
    async def observer_pipeline(self, input_dir):
        prompt = observer.OBSERVE_PROMPT

        files = sorted(
            [f for f in os.listdir(input_dir) if f.endswith(".md")],
            key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else x
        )

        window_size = 5
        print("Transcriber Pipeline", len(files))
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
                        self.all_actions[nid] = c
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

                        relation = resp.relations
                        label = relation.score
                        _, t_targets = str(relation.source), relation.target

                        if label < 7:
                            self._handle_different(new_obs, do) 
                        elif label >= 7:
                            if t_targets:
                                self._handle_identical(new_obs, t_targets)
            except Exception as e:
                print(f"[{tid}] ERROR: {e}")
            
            with open(self.save_file, "wb") as f:
                f.write(orjson.dumps(self.all_actions, option=orjson.OPT_INDENT_2))
            print(f"[{tid}] done. total actions={len(self.all_actions)} | iter={time.perf_counter()-iter_t0:.2f}s")
        return self.all_actions



### Old Code ###
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
    #                                 #     self.need_index.remove_need(merged_id)
    # except Exception as e: