# import os
# import asyncio
# from openai import AsyncOpenAI
# from prompts.screen import TRANSCRIPTION_PROMPT
# from llm import LLM
# from typing import List

# class ScreenObserver():
#     def __init__(self, model, params):
#         self.model = model
#         self.params = params
#         self.client = LLM(model)
#         self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))


#     def observe(self, transcripts: List[str], summaries: List[str]):
#         response = self.client.chat.completions.create(
#             model=self.model,
#             messages=[{"role": "user", "content": prompt}],


#         """
#         prompt = observer.OBSERVE_PROMPT
#         # files = sorted(
#         #     [f for f in os.listdir(input_dir) if f.endswith(".md")],
#         #     key=lambda x: os.path.getctime(os.path.join(input_dir, x))
#         # )
#         # print(files)
#         # split files into active sessions
#         # sessions = self._split_sessions(input_dir, files)
#         # files = sort_sessions(os.listdir(input_dir))
#         # sessions = self._split_sessions(input_summaries_dir)
#         # print(files)
#         sessions = group_and_sort_sessions(os.listdir(input_dir))
#         print("Transcriber Pipeline", end_file)

#         to_end_count = 0
#         end_session = False

#         for session in sessions[1:2]:
#             session_length = len(session)
#             for index in range(0, session_length, window_size):
#                 try:
#                     fnames = session[index: index + window_size]
#                     start_file = fnames[0]
#                     tid = os.path.splitext(start_file)[0]
#                     iter_t0 = time.perf_counter()
#                     # try:
#                     # ----- Load and propose -----
#                     actions = self._get_actions(fnames, include_transcript=include_transcript)
#                     input_prompt = prompt.format(actions=actions, user_name=self.name)
#                     new_needs = await self._guarded_call(self.client, input_prompt, self.model, resp_format=ObservationResponse)


#                     for prop in new_needs.observations:
#                         nid = f"{self.count}"
#                         item = {"id": nid, "description": prop.description, "evidence": [prop.evidence], "confidence": prop.confidence}
#                         self._handle_different(item)
#                         # item = {"id": nid, "description": prop.description, "evidence": [prop.evidence], "generality": prop.generality, "interestingness": prop.interestingness}
#                         self.count += 1
#                         # cand_items.append(item)
#                 except Exception as e:
#                     print(f"[{tid}] ERROR: {e}")
#                 #     # ----- Batch embed + ANN pre-filter -----
#                 #     desc_only = [f"{c['description']}" for c in cand_items]
#                 #     vecs = self.embed_store.encode(desc_only, batch_size=int(os.getenv("EMB_BATCH", "256")))
#                 #     keep_mask = self.embed_store.batch_add_if_new([c["id"] for c in cand_items], vecs)
#                 #     kept = int(np.sum(keep_mask)) if len(keep_mask) else 0
#                 #     print(f"[{tid}] kept {kept}/{len(cand_items)}")

#                 #     # Prepare survivors but DO NOT add to BM25 yet
#                 #     survivors = [(c, do) for keep, c, do in zip(keep_mask, cand_items, desc_only) if keep]
#                 #     if not survivors:
#                 #         print(f"[{tid}] skip: all proposed needs failed ANN threshold")
#                 #         continue

#                 #     if len(self.actions_index.needs) == 0:
#                 #         for c, t in survivors:
#                 #             nid = c['id']
#                 #             self.all_actions[nid] = c
#                 #             self.actions_index.add_needs([(nid, t)])
#                 #     else:
#                 #         for new_obs, do in survivors:
#                 #             # --- (a) BM25 retrieval body for THIS survivor only (no self in index yet) ---
#                 #             input = f"ID: {new_obs['id']} | {new_obs['description']}"
#                 #             retrieved = self._search_bm25(do, top_k=3) # use description only to search for retrieved
#                 #             existing = []
#                 #             for r in retrieved:
#                 #                 existing.append(f"ID: {r['id']} | {r['description']}")

#                 #             classifier_prompt = observer.SIMILAR_PROMPT.format(new=input, existing=existing)
#                 #             # print(classifier_prompt)
#                 #             resp = await self._guarded_call(self.client, classifier_prompt, self.model, resp_format=RelationsResponse)
#                 #             print('Relations', resp)

#                 #             relation = resp.relations
#                 #             label = relation.score
#                 #             _, t_targets = str(relation.source), relation.target

#                 #             if label < 8:
#                 #                 self._handle_different(new_obs, do)
#                 #             elif label >= 8:
#                 #                 if t_targets:
#                 #                     self._handle_identical(new_obs, t_targets)
#                 #     to_end_count += len(fnames)
#                 #     if to_end_count >= end_file:
#                 #         end_session = True
#                 #         break
#                 # except Exception as e:
#                 #     print(f"[{tid}] ERROR: {e}")
#             # Save at the end of each session
#             print("Save to", self.save_file)
#             with open(self.save_file, "wb") as f:
#                 f.write(orjson.dumps(self.all_actions, option=orjson.OPT_INDENT_2))
#             print(f"[{tid}] done. total actions={len(self.all_actions)} | iter={time.perf_counter()-iter_t0:.2f}s")
#             if end_session: break
#         return self.all_actions
