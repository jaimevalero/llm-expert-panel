"""
Main CLI runner for parsing-llm experiments.
Orchestrates the entire experiment execution pipeline.
"""

import asyncio
import argparse
import sys
import os
from typing import List, Optional

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config
from src.parser import PromptParser
from src.models import ModelInterface
from src.orchestrator import ExperimentOrchestrator
from src.telemetry import TelemetryManager
from src.output import MarkdownGenerator


def estimate_tokens(config: Config, blocks: List[str]) -> dict:
    """
    Estimate token usage for an experiment.

    Args:
        config: Config instance
        blocks: List of blocks to process

    Returns:
        Dict with estimation details
    """
    parser = PromptParser(config.prompts_dir)

    total_input_tokens = 0
    total_output_tokens = 0

    for block in blocks:
        # Parse block
        block_prompt = parser.parse_block_prompt(block, round_num=1)

        # Estimate input tokens (rough: 1 token ≈ 4 characters)
        for question in block_prompt.questions:
            prompt_chars = len(question.text)
            input_tokens_per_question = prompt_chars // 4
            total_input_tokens += input_tokens_per_question * len(config.get_model_list())

        # Estimate output tokens
        max_tokens = config.get_max_tokens(block, round_num=1)
        questions_count = len(block_prompt.questions)
        models_count = len(config.get_model_list())

        total_output_tokens += max_tokens * questions_count * models_count

    total_tokens = total_input_tokens + total_output_tokens

    # Estimate cost (rough average)
    avg_cost_per_1m_tokens = 1.5
    estimated_cost = (total_tokens / 1_000_000) * avg_cost_per_1m_tokens

    return {
        "blocks": blocks,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
        "models_count": models_count
    }


async def run_experiment_async(
    config: Config,
    blocks: List[str],
    experiment_name: str = "experiment3"
) -> bool:
    """
    Run experiment asynchronously.

    Args:
        config: Config instance
        blocks: List of blocks to process
        experiment_name: Name of experiment

    Returns:
        True if successful
    """
    # Initialize components
    parser = PromptParser(config.prompts_dir)
    model_interface = ModelInterface(config)
    telemetry = TelemetryManager(config)
    markdown_gen = MarkdownGenerator(config.output_dir)

    # Create orchestrator
    orchestrator = ExperimentOrchestrator(
        config=config,
        parser=parser,
        model_interface=model_interface,
        telemetry=telemetry
    )

    try:
        # Run experiment
        all_responses = await orchestrator.run_experiment(
            experiment_name=experiment_name,
            blocks=blocks
        )

        # Generate output files for each block
        telemetry.print_info("Generating output files...")

        files_generated = 0
        for block in blocks:
            if block not in all_responses or not all_responses[block]:
                telemetry.print_error(f"No responses for Block {block} - skipping file generation")
                continue

            try:
                # Parse block to get questions
                block_prompt = parser.parse_block_prompt(block, round_num=1)

                # Generate markdown
                content = markdown_gen.generate_block_output(
                    block=block,
                    questions=block_prompt.questions,
                    responses=all_responses[block],
                    config=config
                )

                # Determine language
                language = "es" if block == "D" else "en"

                # Write file
                output_path = markdown_gen.write_output_file(
                    block=block,
                    content=content,
                    language=language
                )

                telemetry.print_success(f"Generated: {output_path}")
                files_generated += 1
            except Exception as e:
                telemetry.print_error(f"Failed to generate output for Block {block}: {e}")

        # Report generation summary
        if files_generated > 0:
            telemetry.print_info(f"Successfully generated {files_generated}/{len(blocks)} block output files")
        else:
            telemetry.print_error("No output files were generated")

        # Generate summary report (even if some blocks failed)
        if all_responses:
            summary_content = markdown_gen.generate_summary_report(all_responses, config)
            summary_path = markdown_gen.write_summary_report(summary_content)
            telemetry.print_success(f"Generated: {summary_path}")

        # Show telemetry report
        telemetry.generate_report()

        return files_generated > 0

    except Exception as e:
        telemetry.print_error(f"Experiment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated multi-model experiment runner for parsing-llm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full experiment (all blocks)
  python src/main.py

  # Run single block
  python src/main.py --block A

  # Run specific blocks
  python src/main.py --blocks A B C

  # Estimate token usage only
  python src/main.py --estimate-only

  # Force provider
  python src/main.py --provider ollama
        """
    )

    parser.add_argument(
        "--block",
        type=str,
        choices=["A", "B", "C", "D"],
        help="Run a single block only"
    )

    parser.add_argument(
        "--blocks",
        type=str,
        nargs="+",
        choices=["A", "B", "C", "D"],
        help="Run specific blocks (space-separated)"
    )

    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Estimate token usage without running experiment"
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["openrouter", "ollama"],
        help="Force specific provider (overrides .env)"
    )

    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)"
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config.load(args.env_file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("\nPlease ensure:")
        print("1. You have a .env file (copy from .env.example)")
        print("2. Required API keys are set")
        print("3. prompts directory exists (experiment3/prompts/)")
        sys.exit(1)

    # Override provider if specified
    if args.provider:
        config.execution_mode = args.provider

    # Determine blocks to process
    if args.block:
        blocks = [args.block]
    elif args.blocks:
        blocks = args.blocks
    else:
        blocks = ["A", "B", "C", "D"]

    # Estimate tokens if requested
    if args.estimate_only:
        print("\n🔢 Estimating token usage...\n")
        estimate = estimate_tokens(config, blocks)

        print(f"Blocks to process: {', '.join(estimate['blocks'])}")
        print(f"Models: {estimate['models_count']}")
        print(f"Estimated input tokens: {estimate['input_tokens']:,}")
        print(f"Estimated output tokens: {estimate['output_tokens']:,}")
        print(f"Total tokens: {estimate['total_tokens']:,}")
        print(f"Estimated cost: ${estimate['estimated_cost']:.2f}")
        print("\nNote: This is a rough estimate. Actual usage may vary.")
        sys.exit(0)

    # Run experiment
    print(f"\n🚀 Starting experiment with {config.execution_mode}...\n")

    success = asyncio.run(run_experiment_async(config, blocks))

    if success:
        print("\n✅ Experiment completed successfully!\n")
        print(f"Output files available in: {config.output_dir}/\n")
        sys.exit(0)
    else:
        print("\n❌ Experiment failed. Check errors above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
