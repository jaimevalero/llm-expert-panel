"""
Configuration management for parsing-llm experiments.
Loads environment variables and validates configuration.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    name: str  # Short name (e.g., "gemini")
    openrouter_id: str  # OpenRouter model ID
    ollama_id: str  # Ollama model ID
    display_name: str  # Long display name
    max_context_tokens: int = 32000  # Maximum context window size


@dataclass
class BlockConfig:
    """Configuration for a block (token limits per round)."""
    name: str
    round1_max_tokens: int
    round2_max_tokens: int = 0
    round3_max_tokens: int = 0


@dataclass
class Config:
    """Main configuration class."""

    # Execution mode
    execution_mode: str = "openrouter"  # 'openrouter' or 'ollama'

    # API Configuration
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_base_url: str = "http://localhost:11434"

    # LangSmith Telemetry
    langsmith_enabled: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "parsing-llm-experiments"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # Runtime Configuration
    track_tokens: bool = True
    max_retries: int = 3
    timeout_seconds: int = 60
    log_level: str = "INFO"

    # Model Mappings
    models: Dict[str, ModelConfig] = field(default_factory=dict)

    # Block Configurations
    blocks: Dict[str, BlockConfig] = field(default_factory=dict)

    # Paths
    prompts_dir: str = "experiment3/prompts"
    output_dir: str = field(default_factory=lambda: Config._generate_output_dir())

    @staticmethod
    def _generate_output_dir() -> str:
        """
        Generate a timestamped output directory.

        Returns:
            Path to timestamped output directory (e.g., 'output/2026-01-19-1430')
        """
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        base_dir = "output"
        timestamped_dir = os.path.join(base_dir, timestamp)
        return timestamped_dir

    @classmethod
    def load(cls, env_path: Optional[str] = None) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            env_path: Optional path to .env file. If None, uses default.

        Returns:
            Config instance with loaded values.
        """
        # Load .env file
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        # Create config instance
        config = cls()

        # Load execution mode
        config.execution_mode = os.getenv("EXECUTION_MODE", "openrouter")

        # Load API configuration
        config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        config.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1"
        )
        config.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434"
        )

        # Load LangSmith configuration
        langsmith_tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower()
        config.langsmith_enabled = langsmith_tracing in ("true", "1", "yes")
        config.langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
        config.langsmith_project = os.getenv(
            "LANGCHAIN_PROJECT",
            "parsing-llm-experiments"
        )
        config.langsmith_endpoint = os.getenv(
            "LANGCHAIN_ENDPOINT",
            "https://api.smith.langchain.com"
        )

        # Load runtime configuration
        config.track_tokens = os.getenv("TRACK_TOKENS", "true").lower() in ("true", "1", "yes")
        config.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        config.timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "60"))
        config.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Load model mappings
        config._load_models()

        # Load block configurations
        config._load_blocks()

        # Validate configuration
        config.validate()

        return config

    def _load_models(self):
        """
        Load model configurations dynamically from environment.

        Looks for MODEL_N_* variables where N is 1, 2, 3, etc.
        Each model needs:
        - MODEL_N_NAME: Short name (e.g., "gemini")
        - MODEL_N_OPENROUTER: OpenRouter model ID
        - MODEL_N_OLLAMA: Ollama model ID
        - MODEL_N_MAX_CONTEXT: Maximum context tokens (optional, default 32000)
        - MODEL_N_DISPLAY_NAME: Long display name
        """
        self.models = {}
        model_index = 1

        while True:
            # Look for MODEL_N_NAME
            name_key = f"MODEL_{model_index}_NAME"
            name = os.getenv(name_key)

            if not name:
                # No more models found
                break

            # Load other properties for this model
            openrouter_id = os.getenv(
                f"MODEL_{model_index}_OPENROUTER",
                ""
            )
            ollama_id = os.getenv(
                f"MODEL_{model_index}_OLLAMA",
                ""
            )
            display_name = os.getenv(
                f"MODEL_{model_index}_DISPLAY_NAME",
                name.upper()  # Default to uppercase name if not specified
            )
            max_context = int(os.getenv(
                f"MODEL_{model_index}_MAX_CONTEXT",
                "32000"  # Default to 32K tokens
            ))

            # Add to models dict
            self.models[name] = ModelConfig(
                name=name,
                openrouter_id=openrouter_id,
                ollama_id=ollama_id,
                display_name=display_name,
                max_context_tokens=max_context
            )

            model_index += 1

        # If no models were loaded, use defaults
        if not self.models:
            self._load_default_models()

    def _load_default_models(self):
        """Load default model configuration as fallback."""
        self.models = {
            "gemini": ModelConfig(
                name="gemini",
                openrouter_id="google/gemini-pro-1.5",
                ollama_id="gemma:7b",
                display_name="Google Gemini Pro 1.5",
                max_context_tokens=32000
            ),
            "kimi": ModelConfig(
                name="kimi",
                openrouter_id="moonshot/kimi-chat",
                ollama_id="qwen:7b",
                display_name="Moonshot Kimi Chat",
                max_context_tokens=32000
            ),
            "claude": ModelConfig(
                name="claude",
                openrouter_id="anthropic/claude-sonnet-4.5",
                ollama_id="llama3:8b",
                display_name="Anthropic Claude Sonnet 4.5",
                max_context_tokens=200000
            ),
            "chatgpt": ModelConfig(
                name="chatgpt",
                openrouter_id="openai/gpt-4-turbo",
                ollama_id="mistral:7b",
                display_name="OpenAI GPT-4 Turbo",
                max_context_tokens=128000
            ),
        }

    def _load_blocks(self):
        """Load block configurations (token limits per round)."""
        # Helper to get token limit from env with default
        def get_token_limit(block: str, round_num: int, default: int) -> int:
            env_key = f"BLOCK_{block}_ROUND{round_num}_MAX_TOKENS"
            return int(os.getenv(env_key, default))

        self.blocks = {
            "A": BlockConfig(
                name="A",
                round1_max_tokens=get_token_limit("A", 1, 1600),
                round2_max_tokens=get_token_limit("A", 2, 1000),
                round3_max_tokens=get_token_limit("A", 3, 400)
            ),
            "B": BlockConfig(
                name="B",
                round1_max_tokens=get_token_limit("B", 1, 1400),
                round2_max_tokens=get_token_limit("B", 2, 1000),
                round3_max_tokens=get_token_limit("B", 3, 400)
            ),
            "C": BlockConfig(
                name="C",
                round1_max_tokens=get_token_limit("C", 1, 1500),
                round2_max_tokens=get_token_limit("C", 2, 0),
                round3_max_tokens=get_token_limit("C", 3, 0)
            ),
            "D": BlockConfig(
                name="D",
                round1_max_tokens=get_token_limit("D", 1, 1500),
                round2_max_tokens=get_token_limit("D", 2, 0),
                round3_max_tokens=get_token_limit("D", 3, 0)
            ),
        }

    def validate(self):
        """Validate configuration and raise errors if invalid."""
        # Validate execution mode
        if self.execution_mode not in ("openrouter", "ollama"):
            raise ValueError(
                f"Invalid execution mode: {self.execution_mode}. "
                "Must be 'openrouter' or 'ollama'."
            )

        # Validate OpenRouter configuration
        if self.execution_mode == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY is required when execution_mode is 'openrouter'. "
                    "Please set it in your .env file."
                )

        # Validate LangSmith configuration
        if self.langsmith_enabled and not self.langsmith_api_key:
            print(
                "Warning: LangSmith tracing is enabled but LANGCHAIN_API_KEY is not set. "
                "Disabling LangSmith."
            )
            self.langsmith_enabled = False

        # Validate paths exist
        if not os.path.exists(self.prompts_dir):
            raise ValueError(
                f"Prompts directory not found: {self.prompts_dir}. "
                "Please ensure experiment3/prompts/ exists."
            )

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def get_model_list(self) -> list[str]:
        """Get list of model names in order."""
        return list(self.models.keys())

    def get_max_tokens(self, block: str, round_num: int = 1) -> int:
        """
        Get maximum tokens for a specific block and round.

        Args:
            block: Block name ('A', 'B', 'C', 'D')
            round_num: Round number (1, 2, or 3)

        Returns:
            Maximum tokens allowed
        """
        block_config = self.blocks.get(block)
        if not block_config:
            raise ValueError(f"Unknown block: {block}")

        if round_num == 1:
            return block_config.round1_max_tokens
        elif round_num == 2:
            return block_config.round2_max_tokens
        elif round_num == 3:
            return block_config.round3_max_tokens
        else:
            raise ValueError(f"Invalid round number: {round_num}")

    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(\n"
            f"  execution_mode={self.execution_mode},\n"
            f"  models={list(self.models.keys())},\n"
            f"  blocks={list(self.blocks.keys())},\n"
            f"  langsmith_enabled={self.langsmith_enabled},\n"
            f"  track_tokens={self.track_tokens}\n"
            f")"
        )
