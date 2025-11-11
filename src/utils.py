from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import APIError, RateLimitError
import asyncio, base64, mimetypes
import re
import anthropic
import numpy as np
from typing import List, TypeVar, Type
from pathlib import Path
from pydantic import BaseModel, ValidationError
import json

T = TypeVar('T', bound=BaseModel)

def parse_llm_json_response(response: str, model: Type[T]) -> T:
    """
    Parse and validate a JSON response from an LLM.
    
    Args:
        response: The raw text response from the LLM, which may contain markdown code fences
        model: A Pydantic model class to validate against
        
    Returns:
        An instance of the Pydantic model with validated data
        
    Raises:
        ValidationError: If the JSON doesn't match the Pydantic model schema
        json.JSONDecodeError: If the response is not valid JSON
    """
    # Remove markdown code fences if present
    cleaned = response.strip()
    
    # Remove ```json or ``` markers
    if cleaned.startswith('```'):
        # Find the first newline after opening fence
        first_newline = cleaned.find('\n')
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        else:
            # No newline, just remove ```json or ```
            cleaned = re.sub(r'^```(?:json)?', '', cleaned)
    
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    # Parse JSON
    print("Cleaned", cleaned)
    parsed_data = json.loads(cleaned)
    
    # Validate against Pydantic model
    return model.model_validate(parsed_data)

async def call_gpt_logprobs(client, prompt, model):
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "text"},
        logprobs=True,
        top_logprobs=2,
    )
    return resp

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=5),
    stop=stop_after_attempt(1),
    retry=retry_if_exception_type((APIError, RateLimitError))
)
async def call_gpt(client, prompt, model, base_url="https://api.openai.com/v1", resp_format=None):
    try:
        if resp_format == None: 
            resp = await client.chat.completions.create(
                model=model,
                base_url=base_url,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "text"},
            )
            return resp.choices[0].message.content
        else: 
            resp = await client.responses.parse(
                model=model,
                input=[{"role": "user", "content": prompt}],
                text_format=resp_format,
            )
        
            return resp.output_parsed
    except Exception as e:
        print(e)

def encode_image_as_data_url(img_path: str) -> str:
    mime, _ = mimetypes.guess_type(img_path)
    if mime is None:
        mime = "image/jpeg" 
    b64 = Path(img_path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(b64).decode()}"

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((APIError, RateLimitError))
)
async def call_gpt_vision(client, prompt, model, images, resp_format):
    # Encode images concurrently
    try:
        data_urls = await asyncio.gather(
            *[asyncio.to_thread(encode_image_as_data_url, p) for p in images]
        )

        content = []
        for url in data_urls:
            content.append({
                "type": "input_image",
                "image_url": url, 
            })
        content.append({
            "type": "input_text",
            "text": prompt
        })

        resp = await client.responses.parse(
            model=model,
            input=[{"role": "user", "content": content}],
            text_format=resp_format 
        )
        return resp.output_parsed
    except Exception as e:
        print(e)

def human_sort(s: str) -> List:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def numeric_stem(filename: str):
    # Extract numeric stem from "123.md" (returns int or None)
    m = re.match(r"^(\d+)\.md$", filename)
    return int(m.group(1)) if m else None

def load_markdown(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
    
def batched(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]
        
def get_openai_embeddings(client, texts, model: str, batch_size: int = 2048):
    """Embed texts via OpenAI in batches; returns (N, D) numpy array."""
    all_vecs = []
    for chunk in batched(texts, batch_size):
        # One request per chunk (cheaper/faster than per-text)
        resp = client.embeddings.create(model=model, input=chunk)
        # The SDK returns a list with .data[i].embedding
        vecs = [item.embedding for item in resp.data]
        all_vecs.extend(vecs)
    return np.asarray(all_vecs, dtype=np.float32)

def format_needs(needs):
    needs = "\n".join(
        [
            f"{i + 1}. {h['name']}: {h['need']} {h['motivation']}"
            for i, h in enumerate(needs)
        ]
    )
    return needs

def format_goals(goals):
        try:
            return "\n".join([f"{i.goal}: {i.description}" for i in goals])
        except:
            return "\n".join(
                [f"{i['goal']}: {i['description']})\n" for i in goals]
            )

def call_anthropic(client, prompt, model):
    message = client.messages.create(
        model=model,
        max_tokens=5000,
        temperature=1,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )
    print(message)
    return message.content[0].text