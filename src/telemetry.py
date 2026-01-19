"""
Telemetry and observability for parsing-llm experiments.
Integrates LangSmith tracking and Rich CLI output.
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)
from rich.text import Text

# Optional LangSmith import
try:
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    LangSmithClient = None


@dataclass
class ModelCallMetrics:
    """Metrics for a single model API call."""
    model_name: str
    block: str
    question_num: int
    start_time: float
    end_time: Optional[float] = None
    tokens_used: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0

    @property
    def latency(self) -> float:
        """Calculate latency in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def success(self) -> bool:
        """Check if call was successful."""
        return self.error is None


@dataclass
class ExperimentMetrics:
    """Aggregated metrics for an entire experiment."""
    experiment_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    model_calls: List[ModelCallMetrics] = field(default_factory=list)

    def add_call(self, call: ModelCallMetrics):
        """Add a model call to metrics."""
        self.model_calls.append(call)

    def get_total_tokens(self) -> int:
        """Get total tokens used across all calls."""
        return sum(call.tokens_used for call in self.model_calls if call.success)

    def get_total_cost(self) -> float:
        """Get total cost across all calls."""
        return sum(call.cost for call in self.model_calls if call.success)

    def get_total_errors(self) -> int:
        """Get total number of errors."""
        return sum(1 for call in self.model_calls if not call.success)

    def get_model_stats(self) -> Dict[str, Dict]:
        """Get statistics per model."""
        stats: Dict[str, Dict] = {}
        for call in self.model_calls:
            if call.model_name not in stats:
                stats[call.model_name] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "calls": 0,
                    "errors": 0,
                    "avg_latency": 0.0,
                    "total_latency": 0.0
                }

            if call.success:
                stats[call.model_name]["tokens"] += call.tokens_used
                stats[call.model_name]["cost"] += call.cost
                stats[call.model_name]["total_latency"] += call.latency
            else:
                stats[call.model_name]["errors"] += 1

            stats[call.model_name]["calls"] += 1

        # Calculate average latencies
        for model_name in stats:
            calls = stats[model_name]["calls"] - stats[model_name]["errors"]
            if calls > 0:
                stats[model_name]["avg_latency"] = (
                    stats[model_name]["total_latency"] / calls
                )

        return stats


class TelemetryManager:
    """
    Manages telemetry, tracking, and CLI output for experiments.
    """

    def __init__(self, config):
        """
        Initialize telemetry manager.

        Args:
            config: Config instance with telemetry settings
        """
        self.config = config
        self.console = Console()
        self.metrics = None
        self.progress = None
        self.langsmith_client = None

        # Initialize LangSmith if enabled
        if config.langsmith_enabled and LANGSMITH_AVAILABLE:
            try:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = config.langsmith_api_key or ""
                os.environ["LANGCHAIN_PROJECT"] = config.langsmith_project
                os.environ["LANGCHAIN_ENDPOINT"] = config.langsmith_endpoint

                self.langsmith_client = LangSmithClient()
                self.console.print(
                    f"[green]✓[/green] LangSmith tracing enabled "
                    f"(project: {config.langsmith_project})"
                )
            except Exception as e:
                self.console.print(
                    f"[yellow]⚠[/yellow] Failed to initialize LangSmith: {e}"
                )
                self.langsmith_client = None

    def start_experiment(self, experiment_name: str, blocks: List[str], models: List[str]):
        """
        Start tracking an experiment.

        Args:
            experiment_name: Name of the experiment
            blocks: List of block names
            models: List of model names
        """
        self.metrics = ExperimentMetrics(experiment_name=experiment_name)

        # Display experiment start banner
        panel = Panel(
            f"[bold]Experiment:[/bold] {experiment_name}\n"
            f"[bold]Blocks:[/bold] {', '.join(blocks)}\n"
            f"[bold]Models:[/bold] {', '.join(models)} ({len(models)} total)\n"
            f"[bold]Mode:[/bold] {self.config.execution_mode}\n"
            f"[bold]Output:[/bold] {self.config.output_dir}/",
            title="[bold cyan]Parsing-LLM Experiment Runner[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(panel)
        self.console.print()

    def create_progress(self) -> Progress:
        """
        Create a Rich progress display.

        Returns:
            Progress instance
        """
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        return self.progress

    def track_model_call_start(
        self,
        model_name: str,
        block: str,
        question_num: int
    ) -> ModelCallMetrics:
        """
        Start tracking a model API call.

        Args:
            model_name: Name of the model
            block: Block name
            question_num: Question number

        Returns:
            ModelCallMetrics instance
        """
        return ModelCallMetrics(
            model_name=model_name,
            block=block,
            question_num=question_num,
            start_time=time.time()
        )

    def track_model_call_end(
        self,
        call: ModelCallMetrics,
        tokens_used: int = 0,
        cost: float = 0.0,
        error: Optional[str] = None
    ):
        """
        Complete tracking of a model API call.

        Args:
            call: ModelCallMetrics instance
            tokens_used: Number of tokens used
            cost: Cost in USD
            error: Error message if failed
        """
        call.end_time = time.time()
        call.tokens_used = tokens_used
        call.cost = cost
        call.error = error

        if self.metrics:
            self.metrics.add_call(call)

    def complete_experiment(self):
        """Mark experiment as complete."""
        if self.metrics:
            self.metrics.end_time = time.time()

    def generate_report(self) -> str:
        """
        Generate a formatted report of experiment metrics.

        Returns:
            Formatted report string
        """
        if not self.metrics:
            return "No metrics available"

        # Create performance table
        table = Table(title="Model Performance Summary", show_header=True, header_style="bold cyan")
        table.add_column("Model", style="cyan")
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost", justify="right", style="yellow")
        table.add_column("Avg Latency", justify="right", style="blue")
        table.add_column("Errors", justify="right", style="red")

        stats = self.metrics.get_model_stats()
        for model_name, model_stats in stats.items():
            table.add_row(
                model_name.capitalize(),
                f"{model_stats['tokens']:,}",
                f"${model_stats['cost']:.2f}",
                f"{model_stats['avg_latency']:.1f}s",
                str(model_stats['errors'])
            )

        # Add totals row
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{self.metrics.get_total_tokens():,}[/bold]",
            f"[bold]${self.metrics.get_total_cost():.2f}[/bold]",
            "-",
            f"[bold]{self.metrics.get_total_errors()}[/bold]"
        )

        # Print table
        self.console.print()
        self.console.print(table)
        self.console.print()

        # Experiment summary
        duration = (
            self.metrics.end_time - self.metrics.start_time
            if self.metrics.end_time
            else 0
        )

        summary_text = (
            f"[bold]Experiment:[/bold] {self.metrics.experiment_name}\n"
            f"[bold]Duration:[/bold] {duration:.1f}s\n"
            f"[bold]Total Calls:[/bold] {len(self.metrics.model_calls)}\n"
            f"[bold]Success Rate:[/bold] "
            f"{(len(self.metrics.model_calls) - self.metrics.get_total_errors()) / len(self.metrics.model_calls) * 100:.1f}%"
        )

        summary_panel = Panel(
            summary_text,
            title="[bold green]Experiment Complete[/bold green]",
            border_style="green"
        )
        self.console.print(summary_panel)

        # LangSmith link
        if self.langsmith_client:
            self.console.print(
                f"\n[cyan]→[/cyan] View detailed traces at: "
                f"[link=https://smith.langchain.com]https://smith.langchain.com[/link]"
            )

        return "Report generated"

    def print_error(self, message: str, model_name: Optional[str] = None):
        """
        Print an error message.

        Args:
            message: Error message
            model_name: Optional model name
        """
        prefix = f"[{model_name}] " if model_name else ""
        self.console.print(f"[red]✗[/red] {prefix}{message}")

    def print_success(self, message: str, model_name: Optional[str] = None):
        """
        Print a success message.

        Args:
            message: Success message
            model_name: Optional model name
        """
        prefix = f"[{model_name}] " if model_name else ""
        self.console.print(f"[green]✓[/green] {prefix}{message}")

    def print_info(self, message: str):
        """
        Print an info message.

        Args:
            message: Info message
        """
        self.console.print(f"[cyan]ℹ[/cyan] {message}")
