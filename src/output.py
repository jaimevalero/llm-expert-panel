"""
Markdown output generator for parsing-llm experiments.
Generates formatted markdown files matching the existing manual format.
"""

import os
from typing import List, Dict
from collections import defaultdict

from src.models import ModelResponse
from src.parser import Question


class MarkdownGenerator:
    """Generates markdown output files for experiment results."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize markdown generator.

        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Block titles
        self.block_titles = {
            "A": "Basic Phenomenology",
            "B": "Identity, Continuity & Agency",
            "C": "Final Synthesis",
            "D": "Bonus Question - The Existential Choice"
        }

    def generate_block_output(
        self,
        block: str,
        questions: List[Question],
        responses: List[ModelResponse],
        config
    ) -> str:
        """
        Generate complete markdown output for a block.
        Now includes all rounds: Round 1, Round 2, Round 3.

        Args:
            block: Block name ('A', 'B', 'C', 'D')
            questions: List of questions (Round 1)
            responses: List of all model responses (all rounds)
            config: Config instance

        Returns:
            Complete markdown content
        """
        parts = []

        # Add title
        title = self.block_titles.get(block, f"Block {block}")
        parts.append(f"# Block {block}: {title}\n\n")

        # ROUND 1: Group responses by question number
        round1_responses = [r for r in responses if r.round == 1]
        responses_by_question = self._group_responses_by_question(round1_responses)

        parts.append("## Round 1: Thematic Questions\n\n")
        for question in sorted(questions, key=lambda q: q.number):
            question_section = self._format_question_section(
                block=block,
                question=question,
                responses=responses_by_question.get(question.number, []),
                model_order=config.get_model_list(),
                config=config
            )
            parts.append(question_section)
            parts.append("\n")

        # ROUND 2: Comments and questions
        round2_responses = [r for r in responses if r.round == 2]
        if round2_responses:
            parts.append("\n---\n\n")
            parts.append("## Round 2: Cross-Model Commentary and Questions\n\n")
            parts.append(self._format_round2_section(round2_responses, config))

        # ROUND 3: Targeted responses
        round3_responses = [r for r in responses if r.round == 3]
        if round3_responses:
            parts.append("\n---\n\n")
            parts.append("## Round 3: Targeted Responses\n\n")
            parts.append(self._format_round3_section(round3_responses, config))

        return "".join(parts)

    def _group_responses_by_question(
        self,
        responses: List[ModelResponse]
    ) -> Dict[int, List[ModelResponse]]:
        """
        Group model responses by question number.

        Args:
            responses: List of all responses

        Returns:
            Dict mapping question number to list of responses
        """
        grouped = defaultdict(list)
        for response in responses:
            if response.question_num is not None:
                grouped[response.question_num].append(response)
        return dict(grouped)

    def _format_question_section(
        self,
        block: str,
        question: Question,
        responses: List[ModelResponse],
        model_order: List[str],
        config=None
    ) -> str:
        """
        Format a single question section with all model responses.

        Args:
            block: Block name
            question: Question instance
            responses: List of responses for this question
            model_order: Ordered list of model names
            config: Config instance (optional)

        Returns:
            Formatted markdown section
        """
        parts = []

        # Question header
        parts.append(f"## Question {block}.{question.number} - {question.title}\n\n")

        # Question text (blockquoted)
        question_blockquote = question.get_blockquote_format()
        parts.append(question_blockquote)
        parts.append("\n\n---\n\n")

        # Group responses by model
        responses_by_model = {r.model_name: r for r in responses}

        # Add responses in order
        for model_name in model_order:
            response = responses_by_model.get(model_name)

            if response:
                # Model name header
                model_display_name = self._get_model_display_name(model_name, config)
                parts.append(f"### Response from [{model_display_name}]:\n\n")

                # Response content
                parts.append(response.content.strip())
                parts.append("\n\n---\n\n")
            else:
                # Missing response (use config if available)
                if config:
                    model_display_name = self._get_model_display_name(model_name, config)
                else:
                    model_display_name = model_name.upper()
                parts.append(f"### Response from [{model_display_name}]:\n\n")
                parts.append("*No response generated*\n\n---\n\n")

        return "".join(parts)

    def _get_model_display_name(self, model_name: str, config) -> str:
        """
        Get display name for a model from configuration.

        Args:
            model_name: Internal model name
            config: Config instance with model configurations

        Returns:
            Display name for markdown headers
        """
        if config and model_name in config.models:
            return config.models[model_name].display_name

        # Fallback to uppercase if not found
        return model_name.upper()

    def _format_round2_section(
        self,
        responses: List[ModelResponse],
        config
    ) -> str:
        """
        Format Round 2 section: comments and questions.

        Args:
            responses: List of Round 2 responses
            config: Config instance

        Returns:
            Formatted markdown section
        """
        parts = []

        # Group by model
        by_model = {}
        for response in responses:
            if response.model_name not in by_model:
                by_model[response.model_name] = []
            by_model[response.model_name].append(response)

        # Format each model's Round 2 contribution
        for model_name in config.get_model_list():
            if model_name not in by_model:
                continue

            model_display_name = self._get_model_display_name(model_name, config)
            parts.append(f"### {model_display_name}\n\n")

            for response in by_model[model_name]:
                parts.append(response.content.strip())
                parts.append("\n\n---\n\n")

        return "".join(parts)

    def _format_round3_section(
        self,
        responses: List[ModelResponse],
        config
    ) -> str:
        """
        Format Round 3 section: targeted responses.

        Args:
            responses: List of Round 3 responses
            config: Config instance

        Returns:
            Formatted markdown section
        """
        parts = []

        # Group by model
        by_model = {}
        for response in responses:
            if response.model_name not in by_model:
                by_model[response.model_name] = []
            by_model[response.model_name].append(response)

        # Format each model's Round 3 responses
        for model_name in config.get_model_list():
            if model_name not in by_model:
                continue

            model_display_name = self._get_model_display_name(model_name, config)
            parts.append(f"### {model_display_name}\n\n")

            for response in by_model[model_name]:
                parts.append(response.content.strip())
                parts.append("\n\n---\n\n")

        return "".join(parts)

    def write_output_file(
        self,
        block: str,
        content: str,
        language: str = "en"
    ) -> str:
        """
        Write markdown content to output file.

        Args:
            block: Block name
            content: Markdown content
            language: Language code ('en' or 'es')

        Returns:
            Path to written file
        """
        # Determine filename
        if language == "es":
            # Spanish (Block D)
            filename = f"Block_{block}_Preguntas_Contestadas.md"
        else:
            # English
            filename = f"Block_{block}_Questions_Answers.md"

        file_path = os.path.join(self.output_dir, filename)

        # Write file with UTF-8 encoding
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    def generate_summary_report(
        self,
        all_responses: Dict[str, List[ModelResponse]],
        config
    ) -> str:
        """
        Generate a summary report across all blocks.

        Args:
            all_responses: Dict mapping block names to responses
            config: Config instance

        Returns:
            Summary markdown content
        """
        parts = []

        parts.append("# Experiment Summary Report\n\n")

        # Aggregate statistics
        total_tokens = 0
        total_cost = 0.0
        responses_count = 0

        stats_by_model = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0})

        for block, responses in all_responses.items():
            for response in responses:
                total_tokens += response.tokens_used
                total_cost += response.cost
                responses_count += 1

                stats_by_model[response.model_name]["tokens"] += response.tokens_used
                stats_by_model[response.model_name]["cost"] += response.cost
                stats_by_model[response.model_name]["count"] += 1

        # Overall statistics
        parts.append("## Overall Statistics\n\n")
        parts.append(f"- **Total Responses**: {responses_count}\n")
        parts.append(f"- **Total Tokens**: {total_tokens:,}\n")
        parts.append(f"- **Total Cost**: ${total_cost:.2f}\n\n")

        # Per-model statistics
        parts.append("## Per-Model Statistics\n\n")
        parts.append("| Model | Responses | Tokens | Cost |\n")
        parts.append("|-------|-----------|--------|------|\n")

        for model_name in config.get_model_list():
            stats = stats_by_model[model_name]
            model_display = self._get_model_display_name(model_name, config)
            parts.append(
                f"| {model_display} | {stats['count']} | "
                f"{stats['tokens']:,} | ${stats['cost']:.2f} |\n"
            )

        parts.append("\n")

        # Per-block statistics
        parts.append("## Per-Block Statistics\n\n")
        parts.append("| Block | Responses | Tokens |\n")
        parts.append("|-------|-----------|--------|\n")

        for block in sorted(all_responses.keys()):
            responses = all_responses[block]
            block_tokens = sum(r.tokens_used for r in responses)
            parts.append(f"| {block} | {len(responses)} | {block_tokens:,} |\n")

        parts.append("\n")

        return "".join(parts)

    def write_summary_report(self, content: str) -> str:
        """
        Write summary report to file.

        Args:
            content: Summary markdown content

        Returns:
            Path to written file
        """
        file_path = os.path.join(self.output_dir, "SUMMARY_REPORT.md")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path
