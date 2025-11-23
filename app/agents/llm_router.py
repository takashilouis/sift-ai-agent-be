"""
Real LLM Router using Gemini API

This module provides LLM inference using Google's Gemini models.
NO keyword matching, NO canned responses - only real LLM calls.
"""

from typing import Optional, Type, TypeVar, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
from app.config import settings
import json
import asyncio


# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


T = TypeVar('T', bound=BaseModel)


async def run_llm(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system_instruction: Optional[str] = None
) -> str:
    """
    Run LLM inference with Gemini
    
    Args:
        prompt: The prompt to send to the LLM
        model: Model name (defaults to settings.LLM_MODEL)
        temperature: Sampling temperature (defaults to settings.LLM_TEMPERATURE)
        max_tokens: Maximum tokens to generate (defaults to settings.MAX_TOKENS)
        system_instruction: Optional system instruction
        
    Returns:
        LLM response text
        
    Raises:
        ValueError: If GEMINI_API_KEY is not configured
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required but not configured")
    
    model_name = model or settings.LLM_MODEL
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    max_tok = max_tokens or settings.MAX_TOKENS
    
    try:
        # Create model with configuration
        gemini_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temp,
                "max_output_tokens": max_tok,
            },
            system_instruction=system_instruction
        )
        
        # Generate content (synchronous, so we run in executor)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_model.generate_content(prompt)
        )
        
        return response.text
        
    except Exception as e:
        print(f"[LLM Router] Error calling Gemini: {e}")
        raise


async def run_llm_structured(
    prompt: str,
    response_model: Type[T],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    system_instruction: Optional[str] = None
) -> T:
    """
    Run LLM with structured JSON output
    
    Args:
        prompt: The prompt to send to the LLM
        response_model: Pydantic model for response validation
        model: Model name
        temperature: Sampling temperature
        system_instruction: Optional system instruction
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        ValueError: If GEMINI_API_KEY is not configured or response is invalid
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required but not configured")
    
    model_name = model or settings.LLM_MODEL
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    
    try:
        # Create model with JSON mode
        gemini_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temp,
                "response_mime_type": "application/json",
            },
            system_instruction=system_instruction
        )
        
        # Add schema to prompt
        schema_str = response_model.model_json_schema()
        full_prompt = f"""{prompt}

Respond with valid JSON matching this schema:
{json.dumps(schema_str, indent=2)}"""
        
        # Generate content
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gemini_model.generate_content(full_prompt)
        )
        
        # Parse and validate JSON
        response_dict = json.loads(response.text)
        validated_response = response_model(**response_dict)
        
        return validated_response
        
    except json.JSONDecodeError as e:
        print(f"[LLM Router] JSON decode error: {e}")
        print(f"[LLM Router] Response text: {response.text}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")
    except Exception as e:
        print(f"[LLM Router] Error calling Gemini with structured output: {e}")
        raise


async def run_llm_with_retry(
    prompt: str,
    max_retries: int = 3,
    **kwargs
) -> str:
    """
    Run LLM with automatic retry on failure
    
    Args:
        prompt: The prompt to send
        max_retries: Maximum number of retry attempts
        **kwargs: Additional arguments for run_llm
        
    Returns:
        LLM response text
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await run_llm(prompt, **kwargs)
        except Exception as e:
            last_error = e
            print(f"[LLM Router] Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    raise last_error


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate text to approximate token limit
    
    Args:
        text: Input text
        max_tokens: Maximum tokens
        
    Returns:
        Truncated text
    """
    estimated_chars = max_tokens * 4
    if len(text) <= estimated_chars:
        return text
    
    return text[:estimated_chars] + "..."


# Predefined system instructions for different tasks
SYSTEM_INSTRUCTIONS = {
    "summarize": """You are an expert product analyst. Create concise, informative summaries 
    that highlight key features, value proposition, and target audience. Be objective and factual.""",
    
    "sentiment": """You are a sentiment analysis expert. Analyze product reviews and data to 
    determine overall sentiment, identify key themes, and provide percentage breakdowns. 
    Be data-driven and specific.""",
    
    "compare": """You are a product comparison expert. Compare products objectively across 
    features, price, quality, and value. Provide clear recommendations for different use cases. 
    Use tables and structured comparisons.""",
    
    "extract": """You are a data extraction expert. Extract structured product information 
    from HTML content. Be thorough and accurate. If information is not available, use null.""",
}


def get_system_instruction(task_type: str) -> Optional[str]:
    """
    Get predefined system instruction for task type
    
    Args:
        task_type: Type of task (summarize, sentiment, compare, extract)
        
    Returns:
        System instruction string or None
    """
    return SYSTEM_INSTRUCTIONS.get(task_type)
