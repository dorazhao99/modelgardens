from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import APIError, RateLimitError
from typing import List, Any


def extract_text_from_output(output_items: List[Any]) -> str:
    """Fallback: pull text out of Responses API output."""
    chunks: List[str] = []
    for item in output_items:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []):
                if getattr(c, "type", None) in ("output_text", "input_text"):
                    chunks.append(getattr(c, "text", "") or "")
    return "\n".join(chunks)

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=5),
    stop=stop_after_attempt(1),
    retry=retry_if_exception_type((APIError, RateLimitError))
)
async def call_gpt(client, prompt, model, base_url="https://api.openai.com/v1", resp_format=None, systems_message=None):
    if systems_message != None:
        messages = [{"role": "system", "content": systems_message}, {"role": "user", "content": prompt}]
    else:
        messages = [{"role": "user", "content": prompt}]
    try:
        if resp_format == None: 
            resp = await client.chat.completions.create(
                model=model,
                base_url=base_url,
                messages=messages,
                response_format={"type": "text"},
            )
            return resp.choices[0].message.content
        else: 
            resp = await client.responses.parse(
                model=model,
                input=messages,
                text_format=resp_format,
            )
        
            return resp.output_parsed
    except Exception as e:
        print(e)

async def call_anthropic(client, prompt, model):
    message = await client.messages.create(
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
    return message.content[0].text