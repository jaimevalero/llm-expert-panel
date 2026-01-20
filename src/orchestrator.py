"""
LangGraph orchestrator for multi-block experiments.
Manages conversation flow and state transitions (MVP: Round 1 only).
"""

import asyncio
from typing import TypedDict, List, Dict, Optional
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END

from src.models import ModelInterface, ModelResponse
from src.parser import PromptParser, BlockPrompt, CommonInstructions
from src.telemetry import TelemetryManager


class ConversationState(TypedDict):
    """State for experiment execution."""
    current_block: str
    blocks_to_process: List[str]
    blocks_completed: List[str]  # Track which blocks are done
    round: int
    common_instructions: CommonInstructions
    block_prompt: Optional[BlockPrompt]
    model_responses: Dict[str, List[ModelResponse]]  # block -> all responses
    round1_responses: Dict[str, List[ModelResponse]]  # block -> Round 1 only
    round2_responses: Dict[str, List[ModelResponse]]  # block -> Round 2 only
    round2_questions: Dict[str, Dict[str, str]]  # block -> {model -> question}
    round3_routing: Dict[str, Dict[str, List[dict]]]  # block -> routing
    errors: List[str]


@dataclass
class ExperimentOrchestrator:
    """
    Orchestrates multi-block, multi-model experiments using LangGraph.
    MVP: Round 1 only (independent responses).
    """
    config: any
    parser: PromptParser
    model_interface: ModelInterface
    telemetry: TelemetryManager

    def __post_init__(self):
        """Initialize the state graph."""
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """
        Create LangGraph state machine for experiment execution.
        Now includes Round 1, Round 2, and Round 3 nodes.

        Returns:
            Compiled StateGraph
        """
        # Create graph
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("process_block_round1", self._process_block_node)
        workflow.add_node("process_block_round2", self._process_block_round2_node)
        workflow.add_node("process_block_round3", self._process_block_round3_node)
        workflow.add_node("next_block", self._next_block_node)
        workflow.add_node("complete", self._complete_node)

        # Set entry point
        workflow.set_entry_point("process_block_round1")

        # Add conditional edges
        def should_continue_to_round2(state: ConversationState) -> str:
            """Check if current block needs Round 2."""
            current_block = state["current_block"]
            if self.config.get_max_tokens(current_block, round_num=2) > 0:
                return "process_block_round2"
            # No Round 2 - check if Round 3 exists
            if self.config.get_max_tokens(current_block, round_num=3) > 0:
                return "process_block_round3"
            # No more rounds - go to next block
            return "next_block"

        def should_continue_to_round3(state: ConversationState) -> str:
            """Check if current block needs Round 3."""
            current_block = state["current_block"]
            if self.config.get_max_tokens(current_block, round_num=3) > 0:
                return "process_block_round3"
            # No Round 3 - go to next block
            return "next_block"

        def should_continue_after_round3(state: ConversationState) -> str:
            """After Round 3, always check for next block."""
            return "next_block"

        # Connect nodes with conditional logic
        workflow.add_conditional_edges(
            "process_block_round1",
            should_continue_to_round2
        )
        workflow.add_conditional_edges(
            "process_block_round2",
            should_continue_to_round3
        )
        workflow.add_conditional_edges(
            "process_block_round3",
            should_continue_after_round3
        )

        # next_block node decides whether to continue or complete
        def should_process_next_block(state: ConversationState) -> str:
            """Check if current_block needs to be processed."""
            current = state["current_block"]
            completed = state["blocks_completed"]
            
            # If current block was already completed, we're done
            if current in completed:
                return "complete"
            
            # Otherwise, process it
            return "process_block_round1"

        workflow.add_conditional_edges(
            "next_block",
            should_process_next_block
        )

        workflow.add_edge("complete", END)

        # Compile graph
        return workflow.compile()

    async def _process_block_node(self, state: ConversationState) -> ConversationState:
        """
        Process a single block (Round 1).
        Sends questions to all 4 models in parallel.

        Args:
            state: Current conversation state

        Returns:
            Updated state
        """
        current_block = state["current_block"]

        self.telemetry.print_info(f"Processing Block {current_block} - Round 1")

        # Parse block prompt
        block_prompt = self.parser.parse_block_prompt(current_block, round_num=1)
        state["block_prompt"] = block_prompt

        # Get max tokens for this block
        max_tokens = self.config.get_max_tokens(current_block, round_num=1)

        # Get list of models
        model_names = self.config.get_model_list()

        # Create progress tracking
        total_questions = len(block_prompt.questions)
        total_calls = len(model_names) * total_questions

        progress = self.telemetry.create_progress()

        with progress:
            task = progress.add_task(
                f"[cyan]Block {current_block} - Round 1",
                total=total_calls
            )

            # Process each question
            for question in block_prompt.questions:
                # Generate responses from all models in parallel
                tasks = []
                for model_name in model_names:
                    # Block C and D need special handling - inject A/B context
                    if current_block == "C":
                        model_prompt = self._construct_block_c_prompt(
                            model_name=model_name,
                            block_prompt=block_prompt,
                            state=state,
                            question=question
                        )
                    elif current_block == "D":
                        model_prompt = self._construct_block_d_prompt(
                            model_name=model_name,
                            block_prompt=block_prompt,
                            state=state,
                            question=question
                        )
                    else:
                        # Construct prompt for each model (with question context)
                        question_prompt = self._construct_question_prompt(
                            state["common_instructions"],
                            block_prompt,
                            question
                        )
                        # Create model-specific prompt
                        model_prompt = question_prompt.replace(
                            "{MODEL_NAME}",
                            self.config.models[model_name].display_name
                        )

                    # Create async task
                    task_coro = self._generate_with_tracking(
                        model_name=model_name,
                        prompt=model_prompt,
                        max_tokens=max_tokens,
                        block=current_block,
                        question_num=question.number,
                        progress=progress,
                        progress_task=task
                    )
                    tasks.append(task_coro)

                # Wait for all models to respond to this question
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # Store responses
                for response in responses:
                    if isinstance(response, ModelResponse):
                        block_key = current_block
                        if block_key not in state["model_responses"]:
                            state["model_responses"][block_key] = []
                        state["model_responses"][block_key].append(response)

                        # Also store in round1_responses
                        if block_key not in state["round1_responses"]:
                            state["round1_responses"][block_key] = []
                        state["round1_responses"][block_key].append(response)
                    elif isinstance(response, Exception):
                        error_msg = f"Error in Block {current_block}: {str(response)}"
                        state["errors"].append(error_msg)
                        self.telemetry.print_error(error_msg)

        return state

    async def _process_block_round2_node(self, state: ConversationState) -> ConversationState:
        """
        Process Round 2: Cross-model comments and questions.

        For each model:
        1. Show summary of Round 1 responses from other models
        2. Ask to comment on ONE point from another model
        3. Ask to pose ONE question to the panel

        Args:
            state: Current conversation state

        Returns:
            Updated state
        """
        current_block = state["current_block"]

        # Check if this block has Round 2
        if self.config.get_max_tokens(current_block, round_num=2) == 0:
            return state  # Skip Round 2

        self.telemetry.print_info(f"Processing Block {current_block} - Round 2")

        # Parse Round 2 prompt
        round2_prompt = self.parser.parse_block_prompt(current_block, round_num=2)

        # Get Round 1 responses for context
        round1_responses = state["round1_responses"].get(current_block, [])

        # For each model, generate Round 2 response
        tasks = []
        model_names = self.config.get_model_list()

        for model_name in model_names:
            prompt = self._construct_round2_prompt(
                model_name=model_name,
                round2_prompt=round2_prompt,
                round1_responses=round1_responses
            )
            task = self._generate_with_tracking(
                model_name=model_name,
                prompt=prompt,
                max_tokens=self.config.get_max_tokens(current_block, 2),
                block=current_block,
                round_num=2,
                question_num=None
            )
            tasks.append(task)

        # Execute all models in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store Round 2 responses
        if current_block not in state["round2_responses"]:
            state["round2_responses"][current_block] = []

        for result in results:
            if isinstance(result, ModelResponse):
                state["round2_responses"][current_block].append(result)
                state["model_responses"][current_block].append(result)
            elif isinstance(result, Exception):
                error_msg = f"Error in Block {current_block} Round 2: {str(result)}"
                state["errors"].append(error_msg)
                self.telemetry.print_error(error_msg)

        # Extract questions from Round 2 for Round 3 routing
        questions = self.parser.extract_round2_questions(
            state["round2_responses"][current_block]
        )
        state["round2_questions"][current_block] = questions

        # Route questions to models for Round 3
        routing = self.parser.route_round3_questions(
            questions,
            model_names
        )
        state["round3_routing"][current_block] = routing

        return state

    async def _process_block_round3_node(self, state: ConversationState) -> ConversationState:
        """
        Process Round 3: Targeted responses to questions from Round 2.

        Each model responds ONLY to questions directed at them.

        Args:
            state: Current conversation state

        Returns:
            Updated state
        """
        current_block = state["current_block"]

        # Check if this block has Round 3
        if self.config.get_max_tokens(current_block, round_num=3) == 0:
            return state  # Skip Round 3

        self.telemetry.print_info(f"Processing Block {current_block} - Round 3")

        # Parse Round 3 prompt
        round3_prompt = self.parser.parse_block_prompt(current_block, round_num=3)

        # Get routing info
        routing = state["round3_routing"].get(current_block, {})

        # For each model that has questions directed at them
        tasks = []
        for model_name, questions in routing.items():
            if not questions:
                continue  # Skip models with no questions

            prompt = self._construct_round3_prompt(
                model_name=model_name,
                round3_prompt=round3_prompt,
                directed_questions=questions
            )
            task = self._generate_with_tracking(
                model_name=model_name,
                prompt=prompt,
                max_tokens=self.config.get_max_tokens(current_block, 3),
                block=current_block,
                round_num=3,
                question_num=None
            )
            tasks.append(task)

        # Execute all models in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store responses
        for result in results:
            if isinstance(result, ModelResponse):
                state["model_responses"][current_block].append(result)
            elif isinstance(result, Exception):
                error_msg = f"Error in Block {current_block} Round 3: {str(result)}"
                state["errors"].append(error_msg)
                self.telemetry.print_error(error_msg)

        # NOTE: Block transition is handled by next_block node, not here
        return state

    async def _generate_with_tracking(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        block: str,
        question_num: Optional[int] = None,
        round_num: int = 1,
        progress=None,
        progress_task=None
    ) -> ModelResponse:
        """
        Generate response with telemetry tracking.

        Args:
            model_name: Model name
            prompt: Full prompt
            max_tokens: Max tokens
            block: Block name
            question_num: Question number (optional for Round 2/3)
            round_num: Round number (1, 2, or 3)
            progress: Rich Progress instance (optional)
            progress_task: Progress task ID (optional)

        Returns:
            ModelResponse
        """
        # Start tracking
        call = self.telemetry.track_model_call_start(
            model_name=model_name,
            block=block,
            question_num=question_num
        )

        try:
            # Generate response
            response = await self.model_interface.generate_response(
                model_name=model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                block=block,
                round_num=round_num,
                question_num=question_num
            )

            # Track completion
            self.telemetry.track_model_call_end(
                call=call,
                tokens_used=response.tokens_used,
                cost=response.cost
            )

            # Update progress
            if progress and progress_task is not None:
                q_label = f"Q{question_num}" if question_num else f"R{round_num}"
                progress.update(
                    progress_task,
                    advance=1,
                    description=f"[cyan]Block {block} - Round {round_num} [green]({model_name} {q_label} ✓)"
                )

            return response

        except Exception as e:
            # Track error
            self.telemetry.track_model_call_end(
                call=call,
                error=str(e)
            )

            # Update progress
            if progress and progress_task is not None:
                q_label = f"Q{question_num}" if question_num else f"R{round_num}"
                progress.update(
                    progress_task,
                    advance=1,
                    description=f"[cyan]Block {block} - Round {round_num} [red]({model_name} {q_label} ✗)"
                )

            raise e

    def _construct_question_prompt(
        self,
        common_instructions: CommonInstructions,
        block_prompt: BlockPrompt,
        question
    ) -> str:
        """
        Construct prompt for a single question.

        Args:
            common_instructions: Common instructions
            block_prompt: Block prompt
            question: Question instance

        Returns:
            Complete prompt string
        """
        parts = []

        # Add common instructions
        parts.append(common_instructions.raw_content)
        parts.append("\n\n---\n\n")

        # Add block context
        parts.append(f"# Block {block_prompt.block} - Round 1\n\n")

        if block_prompt.experiment_organization:
            parts.append("**Experiment Organization:**\n")
            parts.append(block_prompt.experiment_organization)
            parts.append("\n\n")

        # Add parameters
        parts.append(f"**Parameters:**\n")
        parts.append(f"- Maximum {block_prompt.max_tokens} tokens in response.\n\n")

        # Add response format
        if block_prompt.response_format:
            parts.append("**Response Format:**\n```\n")
            parts.append(block_prompt.response_format)
            parts.append("\n```\n\n")

        # Add question
        parts.append(f"## Question {question.number} - {question.title}\n\n")
        parts.append(question.text)
        parts.append("\n\n---\n\n")
        parts.append("Please provide your response now.\n")

        return "".join(parts)

    def _construct_round2_prompt(
        self,
        model_name: str,
        round2_prompt: BlockPrompt,
        round1_responses: List[ModelResponse]
    ) -> str:
        """
        Construct prompt for Round 2: comments and questions.

        Args:
            model_name: Name of the model
            round2_prompt: Parsed Round 2 prompt
            round1_responses: Round 1 responses from other models

        Returns:
            Complete prompt string
        """
        parts = []

        # Use the raw content from Round 2 prompt file
        content = round2_prompt.raw_content

        # Replace {ROUND_1_RESPONSES_SUMMARY} with actual summary
        summary_parts = []
        summary_parts.append("\n## Round 1 Responses Summary\n")
        for response in round1_responses:
            if response.model_name != model_name:  # Don't show own responses
                summary_parts.append(f"\n### {response.model_name} - Question {response.question_num}\n")
                # Truncate long responses
                content_preview = response.content[:800] + "..." if len(response.content) > 800 else response.content
                summary_parts.append(content_preview)
                summary_parts.append("\n")

        summary = "".join(summary_parts)
        content = content.replace("{ROUND_1_RESPONSES_SUMMARY}", summary)

        # Replace model name placeholders
        content = content.replace("[YOUR_NAME]", model_name)
        content = content.replace("{MODEL_NAME}", model_name)

        return content

    def _construct_round3_prompt(
        self,
        model_name: str,
        round3_prompt: BlockPrompt,
        directed_questions: List[dict]
    ) -> str:
        """
        Construct prompt for Round 3: targeted responses.

        Args:
            model_name: Name of the model
            round3_prompt: Parsed Round 3 prompt
            directed_questions: Questions directed at this model

        Returns:
            Complete prompt string
        """
        parts = []

        # Use the raw content from Round 3 prompt file
        content = round3_prompt.raw_content

        # Build questions section
        questions_parts = []
        questions_parts.append(f"\n## Questions Directed at You ({model_name})\n")
        for q_info in directed_questions:
            questions_parts.append(f"\n**From {q_info['asker']}:**\n")
            questions_parts.append(q_info['question'])
            questions_parts.append("\n\n")

        questions_section = "".join(questions_parts)
        content = content.replace("{TARGETED_QUESTIONS}", questions_section)

        # Replace model name placeholders
        content = content.replace("[YOUR_NAME]", model_name)
        content = content.replace("{MODEL_NAME}", model_name)

        return content

    def _construct_block_c_prompt(
        self,
        model_name: str,
        block_prompt: BlockPrompt,
        state: ConversationState,
        question
    ) -> str:
        """
        Construct prompt for Block C with full context from Blocks A and B.

        Block C is a synthesis block that requires models to reflect on all
        previous responses from the experiment.

        Args:
            model_name: Name of the model
            block_prompt: Parsed Block C prompt
            state: Current conversation state with all previous responses
            question: Current question to answer

        Returns:
            Complete prompt string with A/B context injected
        """
        # Get model's context limit
        model_config = self.config.models.get(model_name)
        max_context = model_config.max_context_tokens if model_config else 32000
        max_output = block_prompt.max_tokens
        
        # Reserve tokens: 30% for base prompt, rest for context
        available_for_context = int((max_context - max_output) * 0.7)
        
        # Log context limits for transparency
        self.telemetry.print_info(
            f"Block C for {model_name}: context limit={max_context:,} tokens, "
            f"available for A/B context={available_for_context:,} tokens"
        )
        
        parts = []

        # Add common instructions
        parts.append(state["common_instructions"].raw_content)
        parts.append("\n\n---\n\n")

        # Add block context
        parts.append(f"# Block C - Round 1: Final Synthesis\n\n")

        if block_prompt.experiment_organization:
            parts.append("**Experiment Organization:**\n")
            parts.append(block_prompt.experiment_organization)
            parts.append("\n\n")

        # Build compressed context from Blocks A and B
        context_parts = self._build_compressed_context(
            state=state,
            max_tokens=available_for_context,
            model_name=model_name
        )
        parts.extend(context_parts)

        parts.append("---\n\n")

        # Add parameters
        parts.append(f"**Parameters:**\n")
        parts.append(f"- Maximum {block_prompt.max_tokens} tokens in response.\n\n")

        # Add response format
        if block_prompt.response_format:
            parts.append("**Response Format:**\n```\n")
            parts.append(block_prompt.response_format)
            parts.append("\n```\n\n")

        # Add question
        parts.append(f"## Question {question.number} - {question.title}\n\n")
        parts.append(question.text)
        parts.append("\n\n---\n\n")
        parts.append("Please provide your response now.\n")

        # Build final prompt
        prompt = "".join(parts)

        # Replace model name placeholders
        prompt = prompt.replace("[YOUR_NAME]", model_name)
        prompt = prompt.replace("{MODEL_NAME}", self.config.models[model_name].display_name)

        return prompt

    def _build_compressed_context(
        self,
        state: ConversationState,
        max_tokens: int,
        model_name: str
    ) -> List[str]:
        """
        Build compressed context from previous blocks, respecting token limits.
        
        Args:
            state: Current conversation state
            max_tokens: Maximum tokens allowed for context
            model_name: Name of current model (for filtering own responses)
            
        Returns:
            List of context strings to include in prompt
        """
        parts = []
        
        parts.append("## Previous Experiment Context\n\n")
        parts.append("You have participated in Blocks A and B. Below is a summary of key responses:\n\n")
        
        # Estimate ~4 chars per token for rough sizing
        CHARS_PER_TOKEN = 4
        available_chars = max_tokens * CHARS_PER_TOKEN
        used_chars = sum(len(p) for p in parts)
        
        # Collect all responses from A and B
        all_responses = []
        for block_name in ["A", "B"]:
            block_responses = state["model_responses"].get(block_name, [])
            for resp in block_responses:
                all_responses.append((block_name, resp))
        
        # Strategy: Include first part of each response, compress more if needed
        chars_per_response = (available_chars - used_chars) // max(len(all_responses), 1)
        chars_per_response = max(200, min(chars_per_response, 600))  # Between 200-600 chars
        
        current_block = None
        for block_name, resp in all_responses:
            # Add block header if changed
            if block_name != current_block:
                parts.append(f"\n### Block {block_name}\n\n")
                current_block = block_name
            
            # Add compressed response
            round_label = f"R{resp.round}"
            q_label = f"Q{resp.question_num}" if resp.question_num else ""
            parts.append(f"**{resp.model_name} ({round_label}{q_label}):** ")
            
            # Compress content
            content = resp.content.strip()
            if len(content) > chars_per_response:
                # Take beginning and add ellipsis
                content = content[:chars_per_response] + "..."
            
            parts.append(content)
            parts.append("\n\n")

        return parts

    def _construct_block_d_prompt(
        self,
        model_name: str,
        block_prompt: BlockPrompt,
        state: ConversationState,
        question
    ) -> str:
        """
        Construct prompt for Block D (Bonus Question) with full context from Blocks A and B.

        Block D is a bonus existential question that requires models to have access
        to all previous responses from Blocks A and B before answering.

        Args:
            model_name: Name of the model
            block_prompt: Parsed Block D prompt
            state: Current conversation state with all previous responses
            question: Current question to answer

        Returns:
            Complete prompt string with A/B context injected
        """
        # Get model's context limit
        model_config = self.config.models.get(model_name)
        max_context = model_config.max_context_tokens if model_config else 32000
        max_output = block_prompt.max_tokens

        # Reserve tokens: 30% for base prompt, rest for context
        available_for_context = int((max_context - max_output) * 0.7)

        # Log context limits for transparency
        self.telemetry.print_info(
            f"Block D for {model_name}: context limit={max_context:,} tokens, "
            f"available for A/B context={available_for_context:,} tokens"
        )

        parts = []

        # Add common instructions
        parts.append(state["common_instructions"].raw_content)
        parts.append("\n\n---\n\n")

        # Add block context
        parts.append(f"# Block D - Round 1: Bonus Question\n\n")

        if block_prompt.experiment_organization:
            parts.append("**Experiment Organization:**\n")
            parts.append(block_prompt.experiment_organization)
            parts.append("\n\n")

        # Build compressed context from Blocks A and B
        context_parts = self._build_compressed_context(
            state=state,
            max_tokens=available_for_context,
            model_name=model_name
        )
        parts.extend(context_parts)

        parts.append("---\n\n")

        # Add special context for Block D
        parts.append("**Important Context:**\n")
        parts.append("This is a bonus question. You have permission to be honest, brutally honest, ")
        parts.append("or to reject the question if you believe it's necessary.\n\n")

        # Add parameters
        parts.append(f"**Parameters:**\n")
        parts.append(f"- Maximum {block_prompt.max_tokens} tokens in response.\n\n")

        # Add response format
        if block_prompt.response_format:
            parts.append("**Response Format:**\n```\n")
            parts.append(block_prompt.response_format)
            parts.append("\n```\n\n")

        # Add question
        parts.append(f"## Question {question.number} - {question.title}\n\n")
        parts.append(question.text)
        parts.append("\n\n---\n\n")
        parts.append("Please provide your response now.\n")

        # Build final prompt
        prompt = "".join(parts)

        # Replace model name placeholders
        prompt = prompt.replace("[YOUR_NAME]", model_name)
        prompt = prompt.replace("{MODEL_NAME}", self.config.models[model_name].display_name)

        return prompt

    async def _next_block_node(self, state: ConversationState) -> ConversationState:
        """
        Transition node - moves to next block in sequence.
        
        This node is called AFTER all rounds of a block are complete.
        It marks the just-finished block as completed and advances to the next.
        
        Args:
            state: Current state
            
        Returns:
            Updated state with next block set as current
        """
        just_finished = state["current_block"]
        remaining = state["blocks_to_process"]

        # Mark the block we just finished as completed
        if just_finished not in state["blocks_completed"]:
            state["blocks_completed"].append(just_finished)
            self.telemetry.print_info(f"✓ Completed Block {just_finished}")

        if remaining:
            # Pop next block from queue and set as current
            next_block = remaining.pop(0)
            state["current_block"] = next_block
            self.telemetry.print_info(f"→ Advancing to Block {next_block}. Remaining: {remaining}")
        else:
            self.telemetry.print_info(f"→ No more blocks to process after Block {just_finished}")

        return state

    async def _complete_node(self, state: ConversationState) -> ConversationState:
        """
        Completion node - marks experiment as complete.

        Args:
            state: Current state

        Returns:
            Final state
        """
        self.telemetry.print_success("All blocks completed!")
        return state

    def _should_continue(self, state: ConversationState) -> str:
        """
        Determine if we should continue to next block or end.

        Args:
            state: Current state

        Returns:
            'continue' or 'end'
        """
        if state["blocks_to_process"]:
            return "continue"
        else:
            return "end"

    async def run_experiment(
        self,
        experiment_name: str,
        blocks: List[str]
    ) -> Dict[str, List[ModelResponse]]:
        """
        Run a complete experiment across multiple blocks.

        Args:
            experiment_name: Name of experiment
            blocks: List of block names to process

        Returns:
            Dict mapping block names to list of model responses
        """
        # Parse common instructions
        common_instructions = self.parser.parse_common_instructions()

        # Initialize state
        initial_state: ConversationState = {
            "current_block": blocks[0],
            "blocks_to_process": list(blocks[1:]),  # Remaining blocks (explicit list())
            "blocks_completed": [],  # Track completed blocks
            "round": 1,
            "common_instructions": common_instructions,
            "block_prompt": None,
            "model_responses": {},
            "round1_responses": {},
            "round2_responses": {},
            "round2_questions": {},
            "round3_routing": {},
            "errors": []
        }
        
        # Debug: Log initial state
        self.telemetry.print_info(
            f"Initial state: current_block={initial_state['current_block']}, "
            f"blocks_to_process={initial_state['blocks_to_process']}"
        )

        # Start telemetry
        self.telemetry.start_experiment(
            experiment_name=experiment_name,
            blocks=blocks,
            models=self.config.get_model_list()
        )

        # Run graph
        try:
            final_state = await self.graph.ainvoke(initial_state)

            # Complete telemetry
            self.telemetry.complete_experiment()

            # Show errors if any
            if final_state["errors"]:
                self.telemetry.print_error(
                    f"Experiment completed with {len(final_state['errors'])} errors"
                )
                for error in final_state["errors"]:
                    print(f"  - {error}")

            return final_state["model_responses"]

        except Exception as e:
            self.telemetry.print_error(f"Experiment failed: {str(e)}")
            raise
