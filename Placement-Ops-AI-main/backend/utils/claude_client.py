import os
import json
import logging
from typing import Optional, Dict, Any
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    Anthropic = None
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)

def get_claude_client() -> Optional[Any]:
    if not HAS_ANTHROPIC or Anthropic is None:
        logger.warning("Anthropic library is not installed.")
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY is not set. Claude client cannot be initialized.")
        return None
    return Anthropic(api_key=api_key)

def call_claude_for_agent13(
    system_prompt: str,
    context_snapshot: Dict[str, Any],
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 2000,
    temperature: float = 0.2
) -> Optional[Dict[str, Any]]:
    """
    Calls Anthropic Claude strictly with a pre-computed JSON snapshot.
    Enforces a low temperature to prioritize deterministic explanation over creativity.
    Expects structured JSON output as defined by the system prompt.
    """
    client = get_claude_client()
    if not client:
        return None

    # The user prompt contains ONLY the deterministic SQL outputs.
    user_message = f"Here is the pre-computed SQL evidence snapshot for this student. " \
                   f"Explain the profile, opportunity matches, and faculty matches based ONLY on this data.\n\n" \
                   f"<snapshot>\n{json.dumps(context_snapshot, indent=2)}\n</snapshot>"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = response.content[0].text
        
        # Parse the JSON from Claude's response
        try:
            # Often LLMs wrap JSON in ```json blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            return json.loads(json_str)
        except json.JSONDecodeError as parse_err:
            logger.error(f"Failed to parse Claude JSON response: {parse_err}\nRaw text: {response_text}")
            return None

    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return None
