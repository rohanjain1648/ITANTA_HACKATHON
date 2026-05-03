"""ForgeAI — Main Entry Point.

Ties together the Orchestrator, CLI, and Web Dashboard.
"""

import os
import sys
import click
from pathlib import Path
from dotenv import load_dotenv

from forgeai.config.config_manager import ConfigManager
from forgeai.core.orchestrator import Orchestrator
from forgeai.ui.cli_interface import CLIInterface

# Load .env file if it exists
load_dotenv()

@click.command()
@click.option("--spec", "-s", help="Natural language project specification", required=False)
@click.option("--config", "-c", help="Path to YAML config file", default=None)
@click.option("--web", "-w", is_flag=True, help="Launch the web dashboard")
@click.option("--auto", "-a", is_flag=True, help="Auto-answer clarification questions (no interactive prompts)")
def main(spec: str, config: str, web: bool, auto: bool):
    """ForgeAI: Agentic Software Development Framework."""

    # 1. Initialize Configuration
    try:
        cfg_manager = ConfigManager.get_instance(config)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # 2. Initialize UI
    cli = CLIInterface()
    cli.clear()
    cli.print_banner()

    # 3. Launch Web Dashboard in background if requested
    if web or cfg_manager.web_dashboard.enabled:
        cli.console.print("[yellow]Web dashboard enabled. URL: http://127.0.0.1:8000[/yellow]")

    # 4. Initialize Orchestrator
    orchestrator = Orchestrator(cfg_manager)

    # 5. Connect UI to Orchestrator
    # When --spec is given on the CLI or --auto is set, skip interactive
    # question/checkpoint callbacks so the pipeline runs fully headless.
    headless = bool(spec) or auto or not sys.stdin.isatty()
    orchestrator.set_callbacks(
        on_phase_change=cli.show_phase_change,
        on_checkpoint=None if headless else cli.request_checkpoint,
        on_question=None if headless else cli.ask_questions,
        on_task_progress=cli.show_task_progress,
        on_diff_review=None if headless else cli.show_diff_review,
    )

    # 6. Get specification from user if not provided in CLI
    final_spec = spec
    if not final_spec:
        final_spec = click.prompt("\nWhat would you like to build?")

    # 7. Run Pipeline
    summary = orchestrator.run(final_spec)

    # 8. Show Results
    cli.show_summary(summary)

if __name__ == "__main__":
    main()
