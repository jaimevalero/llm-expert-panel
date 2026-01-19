"""
Model interface for parsing-llm experiments.
Supports both OpenRouter and Ollama providers.
"""

import asyncio
import aiohttp
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from openai import AsyncOpenAI


@dataclass
class ModelResponse:
    """Response from a model API call."""
    model_name: str
    content: str
    tokens_used: int
    block: str
    round: int
    question_num: Optional[int]
    timestamp: datetime
    cost: float = 0.0
    provider: str = "unknown"

    def __str__(self) -> str:
        return f"{self.model_name}: {self.tokens_used} tokens, ${self.cost:.4f}"


class ModelInterface:
    """
    Unified interface for different LLM providers.
    Routes requests to OpenRouter or Ollama based on configuration.
    """

    def __init__(self, config):
        """
        Initialize model interface.

        Args:
            config: Config instance
        """
        self.config = config

        # Initialize appropriate provider
        if config.execution_mode == "openrouter":
            self.provider = OpenRouterModel(config)
        elif config.execution_mode == "ollama":
            self.provider = OllamaModel(config)
        else:
            raise ValueError(f"Unknown execution mode: {config.execution_mode}")

    async def generate_response(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        block: str,
        round_num: int = 1,
        question_num: Optional[int] = None
    ) -> ModelResponse:
        """
        Generate a response from a model with retries.

        Args:
            model_name: Name of the model (gemini, kimi, claude, chatgpt)
            prompt: Full prompt text
            max_tokens: Maximum tokens to generate
            block: Block name
            round_num: Round number
            question_num: Optional question number

        Returns:
            ModelResponse instance
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.config.max_retries:
            try:
                response = await self.provider.generate(
                    model_name=model_name,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    timeout=self.config.timeout_seconds
                )

                # Create ModelResponse
                return ModelResponse(
                    model_name=model_name,
                    content=response["content"],
                    tokens_used=response.get("tokens_used", 0),
                    cost=response.get("cost", 0.0),
                    provider=self.config.execution_mode,
                    block=block,
                    round=round_num,
                    question_num=question_num,
                    timestamp=datetime.now()
                )

            except Exception as e:
                last_error = e
                retry_count += 1

                if retry_count <= self.config.max_retries:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** retry_count
                    await asyncio.sleep(wait_time)
                else:
                    # Max retries exceeded
                    raise Exception(
                        f"Failed to generate response after {self.config.max_retries} retries: {last_error}"
                    )


class OpenRouterModel:
    """OpenRouter API client (OpenAI-compatible)."""

    def __init__(self, config):
        """
        Initialize OpenRouter client.

        Args:
            config: Config instance
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url
        )

        # Cost per 1M tokens (approximate, update as needed)
        self.cost_per_1m_tokens = {
            "gemini": 0.50,
            "kimi": 0.30,
            "claude": 3.00,
            "chatgpt": 2.50
        }

    async def generate(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        timeout: int
    ) -> dict:
        """
        Generate response via OpenRouter.

        Args:
            model_name: Model name (gemini, kimi, claude, chatgpt)
            prompt: Full prompt
            max_tokens: Max tokens to generate
            timeout: Timeout in seconds

        Returns:
            Dict with content, tokens_used, cost
        """
        # Get model config
        model_config = self.config.models.get(model_name)
        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")

        # Check if OpenRouter ID is configured
        if not model_config.openrouter_id:
            raise ValueError(
                f"Model {model_name} does not have an OpenRouter ID configured. "
                f"Please set MODEL_*_OPENROUTER in your .env file."
            )

        # Make API call
        try:
            response = await self.client.chat.completions.create(
                model=model_config.openrouter_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=timeout
            )

            # Extract response
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Calculate cost
            cost = self._calculate_cost(model_name, tokens_used)

            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost": cost
            }

        except Exception as e:
            raise Exception(f"OpenRouter API error for {model_name}: {str(e)}")

    def _calculate_cost(self, model_name: str, tokens: int) -> float:
        """Calculate cost based on tokens used."""
        cost_per_million = self.cost_per_1m_tokens.get(model_name, 1.0)
        return (tokens / 1_000_000) * cost_per_million


class OllamaModel:
    """Ollama API client for local models."""

    def __init__(self, config):
        """
        Initialize Ollama client.

        Args:
            config: Config instance
        """
        self.config = config
        self.base_url = config.ollama_base_url

    async def generate(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        timeout: int
    ) -> dict:
        """
        Generate response via Ollama.

        Args:
            model_name: Model name (gemini, kimi, claude, chatgpt)
            prompt: Full prompt
            max_tokens: Max tokens to generate
            timeout: Timeout in seconds

        Returns:
            Dict with content, tokens_used, cost
        """
        # Get model config
        model_config = self.config.models.get(model_name)
        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")

        # Check if Ollama ID is configured
        if not model_config.ollama_id:
            raise ValueError(
                f"Model {model_name} does not have an Ollama ID configured. "
                f"Please set MODEL_*_OLLAMA in your .env file."
            )

        # Get Ollama model name
        ollama_model = model_config.ollama_id

        # Prepare request
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7
            }
        }

        # Make API call
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Ollama API error (status {response.status}): {error_text}"
                        )

                    result = await response.json()

                    # Extract response
                    content = result.get("response", "")

                    # Estimate tokens (Ollama doesn't always return this)
                    # Rough estimate: 1 token ≈ 4 characters
                    tokens_used = len(content) // 4

                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "cost": 0.0  # Ollama is free
                    }

        except asyncio.TimeoutError:
            raise Exception(f"Ollama API timeout for {model_name}")
        except Exception as e:
            raise Exception(f"Ollama API error for {model_name}: {str(e)}")


async def test_model_interface():
    """Test function to verify model interface works."""
    from src.config import Config

    # Load config
    config = Config.load()

    # Create interface
    interface = ModelInterface(config)

    # Test prompt
    test_prompt = "Hello, please introduce yourself in one sentence."

    # Test each model
    for model_name in config.get_model_list():
        print(f"\nTesting {model_name}...")
        try:
            response = await interface.generate_response(
                model_name=model_name,
                prompt=test_prompt,
                max_tokens=100,
                block="TEST",
                round_num=1,
                question_num=1
            )
            print(f"✓ {model_name}: {response.tokens_used} tokens")
            print(f"  Response: {response.content[:100]}...")
        except Exception as e:
            print(f"✗ {model_name}: {e}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_model_interface())
