"""
Markdown prompt parser for parsing-llm experiments.
Extracts questions, token limits, and metadata from prompt files.
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Question:
    """A single question with its text and metadata."""
    number: int
    title: str
    text: str
    block: str

    def get_blockquote_format(self) -> str:
        """Format question text as markdown blockquote."""
        lines = self.text.strip().split('\n')
        return '\n'.join(f"> {line}" if line else ">" for line in lines)


@dataclass
class CommonInstructions:
    """Common instructions shared across all blocks."""
    participants: List[str]
    rules: List[str]
    raw_content: str


@dataclass
class BlockPrompt:
    """Parsed prompt for a specific block and round."""
    block: str
    round: int
    questions: List[Question]
    max_tokens: int
    response_format: str
    experiment_organization: str
    raw_content: str


class PromptParser:
    """Parser for experiment prompt files."""

    def __init__(self, prompts_dir: str = "experiment3/prompts"):
        """
        Initialize parser.

        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = prompts_dir

    def parse_common_instructions(self) -> CommonInstructions:
        """
        Parse common_instructions.md file.

        Returns:
            CommonInstructions instance
        """
        file_path = os.path.join(self.prompts_dir, "common_instructions.md")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract participants
        participants = []
        participants_match = re.search(
            r"### Participants\s*\n(.*?)###",
            content,
            re.DOTALL
        )
        if participants_match:
            participants_text = participants_match.group(1)
            # Extract model names from bullet points
            for line in participants_text.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    model_name = line.lstrip('- ').strip()
                    if model_name:
                        participants.append(model_name)

        # Extract rules
        rules = []
        rules_match = re.search(
            r"### Participation Rules\s*\n(.*?)(?:---|\Z)",
            content,
            re.DOTALL
        )
        if rules_match:
            rules_text = rules_match.group(1)
            # Extract numbered rules
            for line in rules_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    rules.append(line)

        return CommonInstructions(
            participants=participants,
            rules=rules,
            raw_content=content
        )

    def parse_block_prompt(self, block: str, round_num: int = 1) -> BlockPrompt:
        """
        Parse a block prompt file.

        Args:
            block: Block name ('A', 'B', 'C', 'D')
            round_num: Round number (1, 2, or 3)

        Returns:
            BlockPrompt instance
        """
        file_path = os.path.join(
            self.prompts_dir,
            f"Block_{block}_Round_{round_num}.md"
        )

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract max tokens
        max_tokens = self._extract_max_tokens(content)

        # Extract response format
        response_format = self._extract_response_format(content)

        # Extract experiment organization
        experiment_org = self._extract_experiment_organization(content)

        # Extract questions
        questions = self._extract_questions(content, block)

        return BlockPrompt(
            block=block,
            round=round_num,
            questions=questions,
            max_tokens=max_tokens,
            response_format=response_format,
            experiment_organization=experiment_org,
            raw_content=content
        )

    def _extract_max_tokens(self, content: str) -> int:
        """Extract max tokens from content."""
        # Look for "Maximum XXXX tokens" pattern
        match = re.search(r"Maximum\s+(\d+)\s+tokens", content, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Default to 1500 if not found
        return 1500

    def _extract_response_format(self, content: str) -> str:
        """Extract response format from content."""
        # Look for Response Format section in triple backticks
        match = re.search(
            r"\*\*Response Format:\*\*\s*```(.*?)```",
            content,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()

        return ""

    def _extract_experiment_organization(self, content: str) -> str:
        """Extract experiment organization from content."""
        # Look for Experiment Organization section
        match = re.search(
            r"\*\*Experiment Organization:\*\*\s*\n(.*?)\n\nYou are in",
            content,
            re.DOTALL
        )
        if match:
            return match.group(1).strip()

        return ""

    def _extract_questions(self, content: str, block: str) -> List[Question]:
        """
        Extract questions from content.

        Args:
            content: Markdown content
            block: Block name

        Returns:
            List of Question instances
        """
        questions = []

        # Pattern 1: ### Question N - Title
        pattern1 = re.compile(
            r"###\s+Question\s+(\d+)\s*-\s*([^\n]+)\s*\n(.*?)(?=###\s+Question\s+\d+|---|\Z)",
            re.DOTALL
        )

        for match in pattern1.finditer(content):
            question_num = int(match.group(1))
            title = match.group(2).strip()
            text = match.group(3).strip()

            # Clean up the text (remove extra whitespace, keep paragraphs)
            text = self._clean_question_text(text)

            questions.append(Question(
                number=question_num,
                title=title,
                text=text,
                block=block
            ))

        # If no questions found with pattern 1, try pattern 2: ## Block X Thematic Questions
        if not questions:
            # Split by "---" to separate questions
            sections = re.split(r'\n---+\n', content)
            question_num = 1

            for section in sections:
                # Look for question title in format "### Question N - Title" or just question content
                title_match = re.search(r"###\s+Question\s+\d+\s*-\s*([^\n]+)", section)
                if title_match:
                    title = title_match.group(1).strip()
                    # Extract text after title
                    text = section[title_match.end():].strip()
                else:
                    # Check if section has substantial content
                    if len(section.strip()) > 50 and '?' in section:
                        title = f"Question {question_num}"
                        text = section.strip()
                    else:
                        continue

                # Clean up text
                text = self._clean_question_text(text)

                if text:
                    questions.append(Question(
                        number=question_num,
                        title=title,
                        text=text,
                        block=block
                    ))
                    question_num += 1

        return questions

    def _clean_question_text(self, text: str) -> str:
        """
        Clean question text by removing extra whitespace and markdown artifacts.

        Args:
            text: Raw question text

        Returns:
            Cleaned text
        """
        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove "---" separators
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)

        # Collapse multiple newlines into double newlines (preserve paragraphs)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove extra spaces
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)
            else:
                # Preserve empty lines for paragraphs
                if lines and lines[-1] != '':
                    lines.append('')

        return '\n'.join(lines)

    def construct_prompt(
        self,
        block_prompt: BlockPrompt,
        common_instructions: CommonInstructions,
        model_name: str
    ) -> str:
        """
        Construct a complete prompt for a specific model.

        Args:
            block_prompt: Parsed block prompt
            common_instructions: Common instructions
            model_name: Name of the model

        Returns:
            Complete prompt string
        """
        # Start with common instructions
        prompt_parts = [common_instructions.raw_content]

        # Add block-specific content
        prompt_parts.append(f"\n## Block {block_prompt.block} - Round {block_prompt.round}\n")

        # Add experiment organization if available
        if block_prompt.experiment_organization:
            prompt_parts.append("**Experiment Organization:**\n")
            prompt_parts.append(block_prompt.experiment_organization)
            prompt_parts.append("\n")

        # Add token limit
        prompt_parts.append(f"\n**Parameters:**\n- Maximum {block_prompt.max_tokens} tokens in response.\n")

        # Add response format
        if block_prompt.response_format:
            prompt_parts.append("\n**Response Format:**\n```\n")
            # Replace {MODEL_NAME} or [YOUR_NAME] with actual model name
            response_format = block_prompt.response_format.replace("{MODEL_NAME}", model_name)
            response_format = response_format.replace("[YOUR_NAME]", model_name)
            prompt_parts.append(response_format)
            prompt_parts.append("\n```\n")

        # Add questions
        prompt_parts.append("\n## Questions\n")
        for question in block_prompt.questions:
            prompt_parts.append(f"\n### Question {question.number} - {question.title}\n\n")
            prompt_parts.append(question.text)
            prompt_parts.append("\n\n---\n")

        return "".join(prompt_parts)

    def extract_round2_questions(self, responses) -> dict:
        """
        Extract questions asked in Round 2 by each model.

        Args:
            responses: List of ModelResponse objects from Round 2

        Returns:
            Dict mapping model_name -> question_text
        """
        questions = {}
        for response in responses:
            if response.round == 2:
                # Parse response content to find "Question to Panel:" section
                # Pattern matches variations like:
                # - "Question to Panel):"
                # - "Question to Panel:"
                # - Multiple variations with or without parentheses
                match = re.search(
                    r'Question to Panel[):].*?:\s*(.+?)(?=\n\n---|\Z)',
                    response.content,
                    re.DOTALL | re.IGNORECASE
                )
                if match:
                    questions[response.model_name] = match.group(1).strip()
                else:
                    # Fallback: try to find any question in the second half of the response
                    # Split by "---" and take the last section
                    parts = response.content.split('---')
                    if len(parts) >= 2:
                        last_part = parts[-1].strip()
                        # If it contains a question mark, likely a question
                        if '?' in last_part:
                            questions[response.model_name] = last_part
        return questions

    def route_round3_questions(self, round2_questions: dict, models: list) -> dict:
        """
        Route Round 2 questions to target models.

        For now: all questions go to all models (panel format).
        Later: could add @mention parsing for directed questions.

        Args:
            round2_questions: Dict mapping model_name -> question
            models: List of all model names

        Returns:
            Dict mapping target_model -> [question1, question2, ...]
        """
        # Simple implementation: all questions to all models
        routing = {model: [] for model in models}
        for asker_model, question in round2_questions.items():
            for target_model in models:
                if target_model != asker_model:  # Don't ask yourself
                    routing[target_model].append({
                        'asker': asker_model,
                        'question': question
                    })
        return routing
