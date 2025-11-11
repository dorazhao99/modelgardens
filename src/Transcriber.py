from tkinter.constants import S
import cv2
import asyncio
import os
import json
import datetime
from ImageProcessor import ImageProcessor
from prompts import screen
from dotenv import load_dotenv 
from openai import AsyncOpenAI 
import pdb

path_prefix = "/Users/dorazhao/Documents/modelgardens/src/infact_dataset"


class Transcriber():
    def __init__(
        self,
        model: str = "gpt-5-mini", 
        batch_size: int = 50,
        file_window: int = 10,
        input_dir: str = path_prefix,
    ):
        self.model = model
        self.batch_size = batch_size
        self.file_window = file_window
        self.input_dir = f"{input_dir}/raw_data"
        self.files = sorted(
            [f for f in os.listdir(self.input_dir) if f.lower().endswith('.jpg')],
            key=lambda x: os.path.getmtime(os.path.join(self.input_dir, x))
        )
        self.sessions = self._split_sessions()
        self.processor = ImageProcessor()
        self.last_processed_file = ""
    
    def _get_readable_timestamp(self, file: str):
        timestamp = os.path.getmtime(os.path.join(self.input_dir, file))
        readable = datetime.datetime.fromtimestamp(timestamp)
        return readable.strftime("%Y-%m-%d %H:%M:%S")

    
    def _split_sessions(self, threshold: int = 3600):
        """
            Split files into active sessions. 
            An active session is a period of time where there are continuous screenshots. 
        """
        sessions = []
        prev_timestamp = 0
        session_start = 0
        for i, file in enumerate(self.files):
            
            timestamp = os.path.getmtime(os.path.join(self.input_dir, file))
            if i == 0:
                prev_timestamp = timestamp
            time_diff = timestamp - prev_timestamp
            
            assert time_diff >= 0, "Time difference is negative"
            if time_diff > threshold:
                sessions.append(self.files[session_start:i])
                start_time = self._get_readable_timestamp(self.files[session_start])
                end_time = self._get_readable_timestamp(self.files[i - 1])
                session_start = i
                print(f"Session {len(sessions)}: {start_time} - {end_time} | {len(sessions[-1])}")
            prev_timestamp = timestamp
        sessions.append(self.files[session_start:])
        start_time = self._get_readable_timestamp(self.files[session_start])
        end_time = self._get_readable_timestamp(self.files[-1])
        print(f"Session {len(sessions)}: {start_time} - {end_time} | {len(sessions[-1])}")
        return sessions


    def sample_frames(self, video_path: str, output_dir: str, fps: int = 10):
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        # Get original FPS of the video
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(round(original_fps / fps))  # frames to skip between samples
        
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frame_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.jpg")
                cv2.imwrite(frame_filename, frame)
                saved_count += 1
            
            frame_count += 1
        
        cap.release()
        print(f"Saved {saved_count} frames to '{output_dir}'")

    async def transcribe_folder(self, output_dir: str, force_overwrite: bool = False):
        files = sorted(
            [f for f in os.listdir(self.input_dir) if f.endswith(".jpg")],
            key=lambda x: os.path.getmtime(os.path.join(self.input_dir, x))
        )

        idx = 0
        tasks = []
        task_count = 0
        while idx < len(files):
            batch = files[idx: idx + self.file_window]
            image_paths = [os.path.join(self.input_dir, fname) for fname in batch]
            tasks.append(self.processor.call_gpt_vision(prompt=screen.TRANSCRIPTION_PROMPT, images=image_paths, id=idx))
            idx += self.file_window
            task_count += 1
            if len(tasks) == self.batch_size or idx >= len(files):
                print(f"Transcribing batch of {len(tasks)} tasks")
                res = await asyncio.gather(*tasks)
                for transcript, id in res:
                    with open('{}/{}.md'.format(output_dir, id // self.file_window), 'w') as f:
                        f.write(transcript)
                tasks = []
    
    async def summarize_folder(self, output_dir: str, force_overwrite: bool = False):
        files = sorted(
            [f for f in os.listdir(self.input_dir) if f.endswith(".jpg")],
            key=lambda x: os.path.getmtime(os.path.join(self.input_dir, x))
        )

        idx = 0
        tasks = []
        task_count = 0
        while idx < len(files):
            batch = files[idx: idx + self.file_window]
            image_paths = [os.path.join(self.input_dir, fname) for fname in batch]
            tasks.append(self.processor.call_gpt_vision(prompt=screen.SUMMARY_PROMPT, images=image_paths, id=idx))
            idx += self.file_window
            task_count += 1
            if len(tasks) == self.batch_size or idx >= len(files):
                print(f"Transcribing batch of {len(tasks)} tasks")
                res = await asyncio.gather(*tasks)
                for transcript, id in res:
                    with open('{}/{}.md'.format(output_dir, id // self.file_window), 'w') as f:
                        f.write(transcript)
                tasks = []

    async def transcribe_trajectories(self, output_dir: str, force_overwrite: bool = False): 
        idx = 0 

        print(f"Total files: {len(self.files)} | Transcripts: {len(self.files) // self.file_window}")

        tasks = []


        task_count = 0

        for session_num, session in enumerate(self.sessions):
            while idx < len(session):
                image_paths = [os.path.join(self.input_dir, i) for i in session[idx: idx + self.file_window]]
                tasks.append(self.processor.call_gpt_vision(prompt=screen.TRANSCRIPTION_PROMPT, images=image_paths, id=idx))
                idx += self.file_window
                task_count += 1

                # If we've accumulated BATCH_SIZE tasks or reached the end, process and save
                if len(tasks) == self.batch_size or idx >= len(session):
                    print(f"Session {session_num} | Transcribing batch of {len(tasks)} tasks")
                    res = await asyncio.gather(*tasks)
                    for transcript, id in res:
                        with open('{}/session-{}_{}.md'.format(output_dir, session_num, id // self.file_window), 'w') as f:
                            f.write(transcript)
                    tasks = []  # Reset for next batch
            idx = 0

    async def summarize_trajectories(self, output_dir: str, force_overwrite: bool):
        # Only run if the output dir does NOT exist
        if os.path.exists(output_dir) and not force_overwrite:
            print(f"Skip: {output_dir} already exists.")
            return output_dir  # or return None

        os.makedirs(output_dir, exist_ok=True)  # fail if a race creates it


        idx = 0

        tasks = []
        times = []
        print(f"Total files: {len(self.files)} | Summaries: {len(self.files) // self.file_window}")

        task_count = 0
        for session_num, session in enumerate(self.sessions):
            print(f"Summarizing session {session_num} | {len(session)} files")
            while idx < len(session):
                batch = session[idx: idx + self.file_window]
                self.last_processed_file = batch[-1]
                start_time = self._get_readable_timestamp(batch[0])
                end_time = self._get_readable_timestamp(batch[-1])
                times.append(f"Summary of Actions between {start_time} and {end_time}\n")
                image_paths = [os.path.join(self.input_dir, fname) for fname in batch]
                tasks.append(
                    self.processor.call_gpt_vision(
                        prompt=screen.SUMMARY_PROMPT,
                        images=image_paths,
                        id=idx
                    )
                )
                idx += self.file_window
                task_count += 1

                # If we've accumulated BATCH_SIZE tasks or reached the end, process and save
                if len(tasks) == self.batch_size or idx >= len(session):
                    print(f"Session {session_num + 1} | Transcribing batch of {len(tasks)} tasks")
                    res = await asyncio.gather(*tasks, return_exceptions=True)
                    count = 0
                    for transcript, id in res:
                        with open('{}/session-{}_{}.md'.format(output_dir, session_num, id // self.file_window), 'w') as f:
                            f.write(times[count])
                            f.write(transcript)
                            count += 1
                    times = []
                    tasks = []  # Reset for next batch
            idx = 0
        return output_dir

def prepare_directory(data_location: str):
    
    processed_folder = f"{data_location}/processed_data"
    raw_folder = f"{data_location}/raw_data"
    summaries_folder = f"{data_location}/processed_data/summaries"
    transcripts_folder = f"{data_location}/processed_data/transcripts"
    os.makedirs(data_location, exist_ok=True)
    os.makedirs(processed_folder, exist_ok=True)
    os.makedirs(raw_folder, exist_ok=True)
    os.makedirs(summaries_folder, exist_ok=True)
    os.makedirs(transcripts_folder, exist_ok=True)
    return summaries_folder, transcripts_folder
    

async def main():
    load_dotenv()

    sel_file = "msl_pilot"
    input_dir = f"../data/{sel_file}"
    summaries_dir, transcripts_dir = prepare_directory(input_dir)
    observer = Transcriber(model="gpt-5-mini", batch_size=50, file_window=10, input_dir=input_dir)
    await observer.summarize_trajectories(summaries_dir, force_overwrite=True)
    await observer.transcribe_trajectories(transcripts_dir, force_overwrite=True)

async def tool_prep():
    load_dotenv()
    sel_file = "dora_pilot/tool_eval/chi_review"
    input_dir = f"../data/{sel_file}"
    summaries_dir, transcripts_dir = prepare_directory(input_dir)
    t = Transcriber(model="gpt-5-mini", batch_size=50, file_window=10, input_dir=input_dir)
    await t.summarize_folder(summaries_dir, force_overwrite=True)
    await t.transcribe_folder(transcripts_dir, force_overwrite=True)

if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(main())