"""
LLM Client using Anthropic SDK.

Provides a simple interface for Claude API calls with rate limiting
and retry logic.

Usage:
    from llm_client import client, generate

    response = generate(
        prompt="Score this job...",
        system_prompt="You are a job scoring assistant.",
    )
"""

import time
import random
import logging
from typing import Optional

import anthropic

import config
import cost_tracker

logger = logging.getLogger(__name__)

# Initialize the Anthropic client
client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    model: Optional[str] = None,
    max_retries: int = 3,
) -> str:
    """
    Generate content using Claude.

    Args:
        prompt: The user message
        system_prompt: Optional system instruction
        temperature: Temperature for generation
        max_tokens: Maximum tokens in response
        model: Model override (defaults to config.SCORING_MODEL)
        max_retries: Max retries on rate-limit errors

    Returns:
        The generated text content as a string
    """
    model = model or config.SCORING_MODEL

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }

    if system_prompt:
        kwargs["system"] = system_prompt

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(**kwargs)

            # Track cost
            cost_tracker.tracker.record(
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            content = response.content[0].text
            return content.strip() if content else ""

        except anthropic.RateLimitError as e:
            last_exception = e
            if attempt < max_retries:
                delay = (2**attempt) * 10 + random.uniform(0, 5)
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue
            raise

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    raise last_exception
