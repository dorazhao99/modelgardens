import os
import json
import math
import cv2
import numpy as np
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, List, Optional, Tuple
from utils import human_sort

def rmse_between_images(p1: Optional[str], p2: Optional[str]) -> float:
    """
    Root Mean Squared Error (RMSE) between two images.
    Returns +inf if paths are None or shapes differ.
    """
    if not p1 or not p2:
        return float('inf')
    im1 = cv2.imread(p1)
    im2 = cv2.imread(p2)
    if im1 is None or im2 is None:
        return float('inf')
    if im1.shape != im2.shape:
        return float('inf')
    diff = im1.astype(np.float32) - im2.astype(np.float32)
    mse = np.mean(diff ** 2)
    return float(math.sqrt(mse))

@dataclass
class Segment:
    """A contiguous run of frames forming one step."""
    start_idx: int
    end_idx: int               # inclusive
    frame_paths: List[str]
    rmse_with_prev: List[float]  # RMSE between consecutive frames within this segment
    actions: Optional[List[str]] = None
    annotation: Optional[dict] = None

    @property
    def length(self) -> int:
        return len(self.frame_paths)


class ActionProcessor:
    def __init__(
        self,
        frames_dir: str,
        rmse_threshold: float = 8000.0,
        remerge_min_len: int = 3,     # segments shorter than this are candidates for re-merge
        extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png"),
        verbose: bool = False,
    ):
        self.frames_dir = frames_dir
        self.rmse_threshold = rmse_threshold
        self.remerge_min_len = remerge_min_len
        self.extensions = tuple(ext.lower() for ext in extensions)
        self.verbose = verbose

        self.frame_paths: List[str] = self._load_frame_paths()
        if len(self.frame_paths) < 2:
            raise ValueError("Need at least 2 frames to compute RMSE and segment.")
        self.rmses: List[float] = []     # RMSE between frame[i-1] and frame[i], with rmses[0] = 0.0

    # ----- I/O helpers

    def _load_frame_paths(self) -> List[str]:
        files = [
            f for f in os.listdir(self.frames_dir)
            if os.path.splitext(f)[1].lower() in self.extensions
        ]
        files.sort(key=human_sort)
        return [os.path.join(self.frames_dir, f) for f in files]

    # ----- Step 1: RMSE

    def compute_rmses(self) -> List[float]:
        if self.verbose:
            print("Computing RMSE across frames...")
        rmses = [0.0]
        for i in range(1, len(self.frame_paths)):
            r = rmse_between_images(self.frame_paths[i-1], self.frame_paths[i])
            rmses.append(r)
        self.rmses = rmses
        if self.verbose:
            print(f"Computed {len(rmses)} RMSE values.")
        return rmses

    # ----- Step 2: Segment by RMSE threshold

    def segment_by_threshold(self) -> List[Segment]:
        if not self.rmses:
            self.compute_rmses()

        segments: List[Segment] = []
        start = 0
        curr_rmse_inside: List[float] = [0.0]  # RMSE list inside segment (aligned to frames)

        for i in range(1, len(self.frame_paths)):
            if self.rmses[i] <= self.rmse_threshold:
                curr_rmse_inside.append(self.rmses[i])
            else:
                # close segment at i-1
                seg_paths = self.frame_paths[start:i]
                segments.append(Segment(
                    start_idx=start,
                    end_idx=i-1,
                    frame_paths=seg_paths,
                    rmse_with_prev=curr_rmse_inside
                ))
                # start new
                start = i
                curr_rmse_inside = [0.0]

        # last segment
        seg_paths = self.frame_paths[start:]
        segments.append(Segment(
            start_idx=start,
            end_idx=len(self.frame_paths)-1,
            frame_paths=seg_paths,
            rmse_with_prev=curr_rmse_inside
        ))

        if self.verbose:
            lens = [s.length for s in segments]
            print(f"Initial segmentation → {len(segments)} segments; lengths: {lens}")
        return segments

    # ----- Step 3: Iterative re-merge with neural LLM

    @staticmethod
    def _merge_two(a: Segment, b: Segment) -> Segment:
        merged_paths = a.frame_paths + b.frame_paths
        # rmse_with_prev for merged: keep a's, then append b's (first element of b is 0.0 already)
        merged_rmse = a.rmse_with_prev + b.rmse_with_prev
        return Segment(
            start_idx=a.start_idx,
            end_idx=b.end_idx,
            frame_paths=merged_paths,
            rmse_with_prev=merged_rmse,
            actions=None,
            annotation=None
        )

    def remerge_iterative(
        self,
        segments: List[Segment],
        neural_similarity_fn: Callable[[str, str], bool],
    ) -> List[Segment]:
        """
        Re-merge adjacent segments when the smaller of the pair has length < remerge_min_len
        AND the LLM says the representative frames are the same software/context.

        `neural_similarity_fn` should return True if two frames are "same software".
        We use the last frame of seg A and the first frame of seg B for a quick check.
        """
        if self.verbose:
            print("Starting iterative re-merge with neural similarity...")

        changed = True
        while changed:
            changed = False
            merged: List[Segment] = []
            i = 0
            while i < len(segments) - 1:
                a, b = segments[i], segments[i+1]
                short_len = min(a.length, b.length)
                if short_len < self.remerge_min_len:
                    # probe representative frames
                    last_a = a.frame_paths[-1]
                    first_b = b.frame_paths[0]
                    try:
                        same = neural_similarity_fn(last_a, first_b)
                    except Exception as e:
                        if self.verbose:
                            print(f"neural_similarity_fn failed: {e}")
                        same = False

                    if same:
                        merged_seg = self._merge_two(a, b)
                        merged.append(merged_seg)
                        i += 2
                        changed = True
                        if self.verbose:
                            print(f"  Merged segments at {a.start_idx}-{a.end_idx} + {b.start_idx}-{b.end_idx} → len {merged_seg.length}")
                        continue

                # no merge
                merged.append(a)
                i += 1

            if i == len(segments) - 1:
                merged.append(segments[-1])

            segments = merged

        if self.verbose:
            lens = [s.length for s in segments]
            print(f"After re-merge → {len(segments)} segments; lengths: {lens}")
        return segments

    # ----- Step 4: Annotate actions with an LLM

    def annotate_segments(
        self,
        segments: List[Segment],
        annotate_fn: Callable[[List[str]], dict],
    ) -> List[Segment]:
        """
        `annotate_fn` takes a list of frame paths (the segment) and returns a dict like:
            {
              "summary": "...",
              "actions": ["click button", "open file", ...],
              "meta": {...}  # optional
            }
        """
        for s in segments:
            try:
                ann = annotate_fn(s.frame_paths)
            except Exception as e:
                if self.verbose:
                    print(f"annotate_fn failed on segment {s.start_idx}-{s.end_idx}: {e}")
                ann = {"summary": None, "actions": None}

            s.annotation = ann
            s.actions = ann.get("actions")
        return segments

    # ----- Orchestrator

    def run(self,
        neural_similarity_fn: Callable[[str, str], bool],
        annotate_fn: Callable[[List[str]], dict],
        save_dir: Optional[str] = None,
        save_manifest_name: str = "segments_manifest.json",
    ) -> List[Segment]:
        """
        Full pipeline. If `save_dir` is provided, saves per-segment JSON + a manifest.
        """
        segments = self.segment_by_threshold()
        segments = self.remerge_iterative(segments, neural_similarity_fn)
        segments = self.annotate_segments(segments, annotate_fn)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            manifest = []
            for i, seg in enumerate(segments):
                out = {
                    "index": i,
                    "start_idx": seg.start_idx,
                    "end_idx": seg.end_idx,
                    "length": seg.length,
                    "frame_paths": seg.frame_paths,
                    "rmse_with_prev": seg.rmse_with_prev,
                    "annotation": seg.annotation,
                }
                seg_path = os.path.join(save_dir, f"segment_{i:03d}.json")
                with open(seg_path, "w") as f:
                    json.dump(out, f, indent=2)
                manifest.append({"index": i, "path": seg_path, "length": seg.length})

            with open(os.path.join(save_dir, save_manifest_name), "w") as f:
                json.dump({"segments": manifest}, f, indent=2)

            if self.verbose:
                print(f"Saved {len(segments)} segments to {save_dir}")
        return segments

# ---------- Example wiring (stubs you can replace) ----------

def example_neural_same_software(frame_a: str, frame_b: str) -> bool:
    """
    Replace this with your LLM-based check. Expected to return True if "same software".
    For now, this stub always returns False (never merges).
    """
    # Example: call your own function:
    # url_a = encode_image(frame_a, return_url=True)
    # url_b = encode_image(frame_b, return_url=True)
    # resp = call_llm(PROMPT, [{"type":"image_url","image_url":{"url":url_a}},
    #                          {"type":"image_url","image_url":{"url":url_b}}])
    # return "YES" in resp
    return False

def example_annotate_actions(frame_paths: List[str]) -> dict:
    """
    Replace with an LLM call that inspects the segment (you can pass a subset of frames).
    Return a dict with at least "actions": List[str] (or None) and "summary": str.
    """
    # Example: take the first & last frames as context for the LLM.
    # content = [...]
    # resp = call_llm(ANNOTATION_PROMPT, content)
    # return parsed_json_dict
    return {
        "summary": f"Segment of {len(frame_paths)} frames.",
        "actions": [],
    }

# ---------- Minimal usage ----------
# segmenter = FrameStepSegmenter("/path/to/frames", rmse_threshold=8000.0, remerge_min_len=3, verbose=True)
# segments = segmenter.run(
#     neural_similarity_fn=example_neural_same_software,
#     annotate_fn=example_annotate_actions,
#     save_dir="/path/to/output_segments"
# )

def main():
    segmenter = ActionProcessor("infact_dataset/user_trajectories/35", rmse_threshold=100.0, remerge_min_len=3, verbose=True)
    print(segmenter.segment_by_threshold())

if __name__ == '__main__':
    main()
         