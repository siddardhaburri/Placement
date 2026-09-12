"""
Shared Hugging Face chat-completion client.

Extracted from what used to be inline logic in /ai/chat so Resume AI can
reuse the exact same calling pattern (router endpoint, then direct
inference endpoint fallback) instead of a second copy of this code.
"""
import os
import json
import logging
import urllib.request
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"


def get_hf_token(request_override: Optional[str] = None) -> Optional[str]:
    return (
        request_override
        or os.environ.get("HUGGINGFACE_API_KEY")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("NEXT_PUBLIC_HUGGINGFACE_API_KEY")
    )


def call_llm(
    messages: List[Dict[str, str]],
    hf_token: Optional[str],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 600,
    temperature: float = 0.7,
) -> Optional[str]:
    """Returns the model's reply text, or None if no token is configured or
    both the router and direct-inference calls failed. Callers are expected
    to have a non-LLM fallback for the None case -- this function never
    raises for "no key" or "HF unreachable", only logs and returns None so
    the rest of the system stays honest about what actually generated a
    given piece of text."""
    if not hf_token:
        return None

    # 1. HF chat-completions router
    try:
        router_url = "https://router.huggingface.co/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(router_url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            return res_json["choices"][0]["message"]["content"]
    except Exception as err1:
        logger.warning(f"HF Router error: {err1}")

    # 2. Direct model inference endpoint fallback
    try:
        formatted_input = "\n\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\n\nassistant:"
        model_url = f"https://api-inference.huggingface.co/models/{model}"
        payload = {"inputs": formatted_input, "parameters": {"max_new_tokens": max_tokens}}
        headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(model_url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            if isinstance(res_json, list) and len(res_json) > 0:
                return res_json[0].get("generated_text", "").replace(formatted_input, "").strip()
    except Exception as err2:
        logger.warning(f"HF Inference error: {err2}")

    return None
