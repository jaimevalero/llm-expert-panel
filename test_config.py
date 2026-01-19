#!/usr/bin/env python3
"""
Test script to verify model configuration is loaded correctly.
Run this to check your .env file is configured properly.

Usage:
    python test_config.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.config import Config
from loguru import logger


def test_config():
    """Test configuration loading."""
    logger.info("=" * 60)
    logger.info("Testing Model Configuration")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Load config
        config = Config.load()

        logger.success("Configuration loaded successfully!")
        logger.info("")

        # Print execution mode
        mode_emojis = {
            "openrouter": "🚀",
            "ollama": "🦙",
            "local": "💻",
            "default": "⚙️"
        }
        emoji = mode_emojis.get(config.execution_mode, mode_emojis["default"])
        logger.info(f"Execution Mode: {emoji} {config.execution_mode}")
        logger.info("")

        # Print models
        logger.info(f"Number of models configured: {len(config.models)}")
        logger.info("")

        if not config.models:
            logger.warning("WARNING: No models configured!")
            logger.info("   Using default models as fallback.")
            logger.info("")

        # Print model details
        logger.info("Models:")
        logger.info("-" * 60)
        for i, (name, model_config) in enumerate(config.models.items(), 1):
            logger.info(f"{i}. {name}")
            logger.info(f"   Display Name:  {model_config.display_name}")
            logger.info(f"   OpenRouter:    {model_config.openrouter_id or '(not set)'}")
            logger.info(f"   Ollama:        {model_config.ollama_id or '(not set)'}")
            logger.info("")

        # Print model list order
        logger.info("Model execution order: " + ", ".join(config.get_model_list()))
        logger.info("")

        # Print block configurations
        logger.info("Block Configurations:")
        logger.info("-" * 60)
        for block_name, block_config in config.blocks.items():
            logger.info(f"Block {block_name}:")
            logger.info(f"   Round 1 max tokens: {block_config.round1_max_tokens}")
            if block_config.round2_max_tokens > 0:
                logger.info(f"   Round 2 max tokens: {block_config.round2_max_tokens}")
            if block_config.round3_max_tokens > 0:
                logger.info(f"   Round 3 max tokens: {block_config.round3_max_tokens}")
            logger.info("")

        # Verify provider-specific configuration
        logger.info("Provider Configuration:")
        logger.info("-" * 60)
        if config.execution_mode == "openrouter":
            if config.openrouter_api_key:
                masked_key = config.openrouter_api_key[:10] + "..." + config.openrouter_api_key[-4:]
                logger.success(f"OpenRouter API key: {masked_key}")
            else:
                logger.error("OpenRouter API key: NOT SET")
                logger.info("   Please set OPENROUTER_API_KEY in .env")

            # Check if models have OpenRouter IDs
            missing = [name for name, m in config.models.items() if not m.openrouter_id]
            if missing:
                logger.warning(f"Models missing OpenRouter ID: {', '.join(missing)}")

        elif config.execution_mode == "ollama":
            logger.success(f"Ollama URL: {config.ollama_base_url}")

            # Check if models have Ollama IDs
            missing = [name for name, m in config.models.items() if not m.ollama_id]
            if missing:
                logger.warning(f"Models missing Ollama ID: {', '.join(missing)}")

            logger.info("")
            logger.info("To pull Ollama models, run:")
            for name, model_config in config.models.items():
                if model_config.ollama_id:
                    logger.info(f"   ollama pull {model_config.ollama_id}")

        logger.info("")
        logger.info("=" * 60)
        logger.success("Configuration test complete!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.info("")
        logger.info("=" * 60)
        logger.error("Configuration test FAILED!")
        logger.info("=" * 60)
        logger.info("")
        logger.error(f"Error: {e}")
        logger.info("")
        logger.info("Please check:")
        logger.info("1. .env file exists (copy from .env.example)")
        logger.info("2. Required variables are set")
        logger.info("3. Model configuration follows MODEL_N_* format")
        logger.info("")
        return False


if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
