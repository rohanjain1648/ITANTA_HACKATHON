"""ForgeAI — Hugging Face Spaces Entry Point.

Gradio interface that wraps the ForgeAI Orchestrator pipeline,
streaming live progress updates to the user.
"""

import os
import sys
import queue
import threading
import traceback
from pathlib import Path
from typing import Generator

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# ── Helpers ────────────────────────────────────────────────────────────────

def _check_api_key() -> str | None:
    """Return the API key or None if missing."""
    return os.environ.get("GOOGLE_API_KEY", "").strip() or None


def _build_config(api_key: str, auto_approve: bool):
    """Build a ConfigManager with auto-approve and sandboxed output dir."""
    from forgeai.config.config_manager import ConfigManager

    # Reset singleton so each run gets a fresh config
    ConfigManager.reset()
    cfg = ConfigManager.get_instance()

    # Override settings for the web environment
    cfg.config.workflow.auto_approve_checkpoints = auto_approve
    cfg.config.output.project_dir = "./generated_project"
    cfg.config.output.enable_git = False          # No git in sandbox
    cfg.config.web_dashboard.enabled = False      # No nested web server
    cfg.config.llm.api_key_env = "GOOGLE_API_KEY"

    # Inject the key directly into the environment so get_api_key() finds it
    os.environ["GOOGLE_API_KEY"] = api_key

    return cfg


# ── Core pipeline runner ───────────────────────────────────────────────────

def run_pipeline(spec: str, api_key: str, auto_approve: bool,
                 log_queue: "queue.Queue[str]"):
    """Run the ForgeAI pipeline in a background thread, pushing log lines."""

    def push(msg: str):
        log_queue.put(msg)

    try:
        push("🔧 Initialising ForgeAI…")

        cfg = _build_config(api_key, auto_approve)

        from forgeai.core.orchestrator import Orchestrator
        from forgeai.models.workflow_state import WorkflowPhase

        orchestrator = Orchestrator(cfg)

        # ── UI callbacks ──────────────────────────────────────────────────

        def on_phase_change(phase: WorkflowPhase):
            push(f"\n▶ **Phase → {phase.value.upper()}**")

        def on_checkpoint(title: str, content: str) -> bool:
            push(f"\n✅ **Checkpoint: {title}** — auto-approved")
            return True  # Always approve in web mode

        def on_question(questions: list[str]) -> dict[str, str]:
            push("\n💬 **Clarifying questions detected — using smart defaults**")
            return {q: "Use reasonable defaults based on common best practices." for q in questions}

        def on_task_progress(task, progress_data: dict):
            pct = progress_data.get("percent_complete", 0)
            push(f"  📋 Task #{task.id}: **{task.title}** — {task.status.value} ({pct}%)")

        def on_diff_review(task, files: dict) -> bool:
            push(f"  📝 Diff review for Task #{task.id} — auto-approved ({len(files)} file(s))")
            return True

        orchestrator.set_callbacks(
            on_phase_change=on_phase_change,
            on_checkpoint=on_checkpoint,
            on_question=on_question,
            on_task_progress=on_task_progress,
            on_diff_review=on_diff_review,
        )

        push(f"\n🚀 Starting pipeline for: *{spec[:120]}{'…' if len(spec) > 120 else ''}*\n")

        summary = orchestrator.run(spec)

        # ── Final summary ─────────────────────────────────────────────────
        push("\n---")
        push("## 🎉 Pipeline Complete!")
        push(f"- **Status:** {summary.get('status', 'unknown')}")
        push(f"- **Tasks completed:** {summary.get('tasks_completed', 0)}")
        push(f"- **Files generated:** {summary.get('files_generated', 0)}")
        push(f"- **Tests passed:** {summary.get('tests_passed', 0)}")
        push(f"- **Tests failed:** {summary.get('tests_failed', 0)}")
        push(f"- **LLM API calls:** {summary.get('total_api_calls', 0)}")
        push(f"- **Duration:** {summary.get('duration_seconds', 0):.1f}s")

        errors = summary.get("errors", [])
        if errors:
            push("\n⚠️ **Errors encountered:**")
            for err in errors:
                push(f"  - {err}")

        push("\n✅ Output saved to `./generated_project/`")

    except Exception as exc:
        push(f"\n❌ **Pipeline error:** {exc}")
        push("```")
        push(traceback.format_exc())
        push("```")
    finally:
        log_queue.put(None)  # Sentinel — signals stream end


# ── Gradio streaming wrapper ───────────────────────────────────────────────

def forge(spec: str, api_key_input: str, auto_approve: bool) -> Generator[str, None, None]:
    """Gradio generator — yields accumulated log text for the output box."""

    # Resolve API key: prefer the text box, fall back to env var
    api_key = api_key_input.strip() or _check_api_key()

    if not spec.strip():
        yield "⚠️ Please enter a project description."
        return

    if not api_key:
        yield (
            "⚠️ No Google API key found.\n\n"
            "Either paste your key in the **API Key** box above, "
            "or set the `GOOGLE_API_KEY` Space secret."
        )
        return

    log_q: queue.Queue[str] = queue.Queue()

    thread = threading.Thread(
        target=run_pipeline,
        args=(spec, api_key, auto_approve, log_q),
        daemon=True,
    )
    thread.start()

    accumulated = ""
    while True:
        item = log_q.get()
        if item is None:
            break
        accumulated += item + "\n"
        yield accumulated

    thread.join()


# ── Gradio UI ──────────────────────────────────────────────────────────────

_DESCRIPTION = """
# 🔨 ForgeAI — Autonomous Software Factory

Describe any software project in plain English and ForgeAI will:

1. **Clarify** ambiguities with targeted questions  
2. **Design** the architecture  
3. **Plan** atomic implementation tasks  
4. **Write tests first** (TDD), then generate production code  
5. **Run tests** and self-heal on failures  
6. **Audit** the output for security vulnerabilities  

Powered by **Google Gemini 2.5 Flash** · Built for the **Itlanta Hackathon 2026**
"""

_PLACEHOLDER = (
    "e.g. Build a REST API for a task management app with user authentication, "
    "due dates, priority levels, and email notifications using FastAPI and PostgreSQL."
)

with gr.Blocks(title="ForgeAI", theme=gr.themes.Soft()) as demo:
    gr.Markdown(_DESCRIPTION)

    with gr.Row():
        with gr.Column(scale=2):
            spec_box = gr.Textbox(
                label="📝 Project Description",
                placeholder=_PLACEHOLDER,
                lines=5,
            )
            api_key_box = gr.Textbox(
                label="🔑 Google API Key (optional if set as Space secret)",
                placeholder="AIza…",
                type="password",
                lines=1,
            )
            auto_approve_toggle = gr.Checkbox(
                label="⚡ Auto-approve all checkpoints (fully autonomous mode)",
                value=True,
            )
            run_btn = gr.Button("🚀 Forge It!", variant="primary")

        with gr.Column(scale=3):
            output_box = gr.Markdown(
                label="Live Pipeline Output",
                value="*Output will appear here once you click **Forge It!***",
            )

    run_btn.click(
        fn=forge,
        inputs=[spec_box, api_key_box, auto_approve_toggle],
        outputs=output_box,
    )

    gr.Markdown(
        "---\n"
        "💡 **Tip:** Get a free Gemini API key at "
        "[aistudio.google.com](https://aistudio.google.com/app/apikey) · "
        "Source code on [GitHub](https://github.com)"
    )

if __name__ == "__main__":
    # HF Spaces requires the app to bind to 0.0.0.0:7860
    demo.launch(server_name="0.0.0.0", server_port=7860)
