"""
LLM Provider Implementations
Supports multiple LLM providers with a unified interface.
"""
import httpx
import logging
from abc import ABC, abstractmethod
from app.core.logger import logs

class BaseLLMProvider(ABC):
    """Base class for all LLM providers"""
    
    @abstractmethod
    async def generate(self, messages: list, temperature: float = 0.1, timeout: float = 10.0) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the provider"""
        pass


class MistralProvider(BaseLLMProvider):
    """Mistral AI Provider"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, messages: list, temperature: float = 0.1, timeout: float = 10.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logs.log(logging.ERROR, f"Mistral API error: {str(e)}")
                raise
    
    def get_provider_name(self) -> str:
        return "Mistral AI"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-3.5, GPT-4, etc.)"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, messages: list, temperature: float = 0.1, timeout: float = 10.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logs.log(logging.ERROR, f"OpenAI API error: {str(e)}")
                raise
    
    def get_provider_name(self) -> str:
        return "OpenAI"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    async def generate(self, messages: list, temperature: float = 0.1, timeout: float = 10.0) -> str:
        # Convert OpenAI-style messages to Anthropic format
        # Extract system message if present
        system_message = None
        converted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                converted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        payload = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": 1024
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"].strip()
            except Exception as e:
                logs.log(logging.ERROR, f"Anthropic API error: {str(e)}")
                raise
    
    def get_provider_name(self) -> str:
        return "Anthropic Claude"


class GroqProvider(BaseLLMProvider):
    """Groq Provider (Fast inference with Llama, Mixtral, etc.)"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, messages: list, temperature: float = 0.1, timeout: float = 10.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logs.log(logging.ERROR, f"Groq API error: {str(e)}")
                raise
    
    def get_provider_name(self) -> str:
        return "Groq"
