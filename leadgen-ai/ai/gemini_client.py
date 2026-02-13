"""
Google Gemini API client wrapper.
Uses the new google-genai SDK (replaces deprecated google-generativeai).
Handles API calls, rate limiting, token tracking, and structured output.
"""

import json
import logging
import time
from typing import Dict, Optional

from config.settings import Config

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wrapper around Google GenAI SDK (Gemini).
    Manages rate limiting, retries, and token usage tracking.
    """
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = 'gemini-2.0-flash'
        self.temperature = Config.GEMINI_TEMPERATURE
        self.max_tokens = Config.GEMINI_MAX_TOKENS
        self.max_retries = 3
        self.retry_delay = 5
        self._client = None
        self._total_tokens_used = 0
        self._call_count = 0
    
    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set. Add it to config/.env")
            
            from google import genai
            
            self._client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini client initialized: {self.model_name}")
        
        return self._client
    
    def generate(self, prompt: str, expect_json: bool = False) -> Optional[str]:
        """
        Generate text from Gemini API.
        
        Args:
            prompt: The prompt to send
            expect_json: If True, attempt to parse response as JSON
            
        Returns:
            Generated text or None on failure
        """
        client = self._get_client()
        
        from google.genai import types
        
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Gemini API call (attempt {attempt + 1})")
                
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                
                if response and response.text:
                    self._call_count += 1
                    text = response.text.strip()
                    
                    if expect_json:
                        text = self._clean_json(text)
                    
                    return text
                else:
                    logger.warning("Gemini returned empty response")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Gemini API error (attempt {attempt + 1}): {error_msg}")
                
                if '429' in error_msg or 'quota' in error_msg.lower():
                    # If daily quota exhausted, don't waste time retrying
                    if 'per day' in error_msg.lower() or 'PerDay' in error_msg:
                        logger.warning("Daily quota exhausted. Skipping retries.")
                        return None
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                elif 'safety' in error_msg.lower():
                    logger.warning("Content blocked by safety filter")
                    return None
                else:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        logger.error(f"Gemini API failed after {self.max_retries} attempts")
        return None
    
    def _clean_json(self, text: str) -> str:
        """Strip markdown code fences from JSON response."""
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        return text.strip()
    
    @property
    def stats(self) -> Dict:
        """Get usage statistics."""
        return {
            'total_calls': self._call_count,
            'model': self.model_name,
        }
