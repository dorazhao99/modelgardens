import asyncio 
import base64
import os
from openai import AsyncOpenAI
from typing import Optional
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import APIError, RateLimitError

class ImageProcessor():
    def __init__(self):
        load_dotenv()

        self.model_name = 'gpt-4o-mini'
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    @staticmethod
    def _encode_image(img_path: str) -> str:
        """Encode an image file as base64.
        
        Args:
            img_path (str): Path/ to the image file.
            
        Returns:
            str: Base64 encoded image data.
        """
        with open(img_path, "rb") as fh:
            return base64.b64encode(fh.read()).decode()
    
    @staticmethod
    def _sample_frames(video_path: str): 
        print('TBD')

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((APIError, RateLimitError))
    )
    async def call_gpt_vision(self, prompt: str, images: list[str], id: Optional[str]):
        """Call GPT Vision API to analyze images.
        
        Args:
            prompt (str): Prompt to guide the analysis.
            img_paths (list[str]): List of image paths to analyze.
            
        Returns:
            str: GPT's analysis of the images.
        """
        content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            }
            for encoded in (await asyncio.gather(
                *[asyncio.to_thread(self._encode_image, p) for p in images]
            ))
        ]
        content.append({"type": "text", "text": prompt})

        rsp = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "text"},
        )
        return rsp.choices[0].message.content, id