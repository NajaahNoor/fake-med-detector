"""
app/services/llm_client.py
---------------------------
OpenRouter LLM client with fallback model support.
"""

import requests
import json
from typing import List
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import AgentException


class LLMClient:
    """OpenRouter LLM client with failover support."""
    
    def __init__(self):
        """Initialize LLM client."""
        self.api_key = settings.openrouter_api_key
        self.api_base = settings.openrouter_base_url
        self.models = settings.get_all_models()
        self.current_model_idx = 0
        
        if not self.api_key:
            raise AgentException("OPENROUTER_API_KEY not configured")
        
        logger.info(f"LLM Client initialized with models: {self.models}")
    
    def get_current_model(self) -> str:
        """Get currently active model."""
        return self.models[self.current_model_idx]
    
    def call(
        self,
        messages: List[dict],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        json_mode: bool = False
    ) -> str:
        """
        Call LLM with fallback support.
        
        Parameters
        ----------
        messages : List[dict]
            Conversation messages
        system_prompt : str
            System prompt for the agent
        temperature : float
            Sampling temperature
        max_tokens : int
            Maximum tokens in response
        json_mode : bool
            Force JSON output format
        
        Returns
        -------
        str
            LLM response text
        """
        # Build full message with system prompt
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        # Try each model in fallback chain
        for attempt, model_idx in enumerate(range(self.current_model_idx, len(self.models))):
            model = self.models[model_idx]
            
            try:
                logger.info(f"Calling LLM - Attempt {attempt + 1}: {model}")
                
                response_text = self._call_openrouter(
                    model=model,
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )
                
                # Update current model on success
                self.current_model_idx = model_idx
                return response_text
                
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                if attempt == len(self.models) - 1:
                    logger.error("All models exhausted, raising exception")
                    raise AgentException(f"All LLM models failed: {e}")
                continue
    
    def _call_openrouter(
        self,
        model: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        json_mode: bool = False
    ) -> str:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1.0,
        }
        
        # Add response format for JSON mode
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"OpenRouter error ({response.status_code}): {error_msg}")
                raise Exception(f"OpenRouter API error: {error_msg}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"API request failed: {e}")
    
    def extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        try:
            # Try direct JSON parsing first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting from markdown code block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise AgentException(f"Could not parse JSON from response: {text}")


# Global LLM client instance
llm_client = LLMClient()
