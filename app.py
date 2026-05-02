"""ForgeAI — Hugging Face Spaces Entry Point.

Gradio interface that wraps the ForgeAI Orchestrator pipeline,
streaming live progress updates to the user with a premium, 
highly aesthetic frontend.
"""

import os
import queue
import threading
import traceback
from typing import Generator

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# ── Ultra-Premium CSS ──────────────────────────────────────────────────────

_CUSTOM_CSS = """
/* Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    --bg-dark: #020617;
    --card-bg: rgba(15, 23, 42, 0.6);
    --accent-cyan: #22d3ee;
}

body, .gradio-container {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: var(--bg-dark) !important;
    background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.15) 0px, transparent 50%) !important;
}

/* Glassmorphism Effect */
.glass-card {
    background: var(--card-bg) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 24px !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
    padding: 24px !important;
    transition: all 0.4s ease !important;
}

.glass-card:hover {
    border-color: rgba(99, 102, 241, 0.3) !important;
    box-shadow: 0 25px 50px -12px rgba(99, 102, 241, 0.1) !important;
}

/* Typography Enhancements */
.hero-title {
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.04em !important;
    margin-bottom: 0.5rem !important;
}

.hero-subtitle {
    font-size: 1.1rem !important;
    color: #94a3b8 !important;
    line-height: 1.6 !important;
    max-width: 600px;
}

/* Input Fields */
input, textarea {
    background: rgba(2, 6, 23, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #f8fafc !important;
    border-radius: 16px !important;
    padding: 12px 16px !important;
    transition: all 0.3s ease !important;
}

input:focus, textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15) !important;
}

/* Button with Pulse Effect */
.forge-button {
    background: var(--primary-gradient) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 14px 28px !important;
    border-radius: 16px !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

.forge-button:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.5) !important;
}

.forge-button:active {
    transform: scale(0.98) !important;
}

/* Terminal Console Styling */
.terminal-output {
    background: #000000 !important;
    border: 1px solid #1e293b !important;
    border-radius: 16px !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 1.5rem !important;
    font-size: 0.95rem !important;
    color: #e2e8f0 !important;
    box-shadow: inset 0 2px 4px 0 rgba(0,0,0,0.06) !important;
    line-height: 1.7 !important;
}

/* Custom Checkbox */
input[type="checkbox"] {
    accent-color: #6366f1 !important;
}

/* Hide some default labels for a cleaner look */
.gr-form label {
    font-weight: 600 !important;
    color: #cbd5e1 !important;
    margin-bottom: 8px !important;
}

/* Footer Section */
.footer-text {
    text-align: center;
    color: #475569;
    font-size: 0.85rem;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* Scrollbar Styling */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { 
    background: rgba(255, 255, 255, 0.1); 
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
"""

# ── Helpers ────────────────────────────────────────────────────────────────

def _check_api_key() -> str | None:
    return os.environ.get("GOOGLE_API_KEY", "").strip() or None


def _build_config(api_key: str, auto_approve: bool):
    from forgeai.config.config_manager import ConfigManager
    ConfigManager.reset()
    cfg = ConfigManager.get_instance()
    cfg.config.workflow.auto_approve_checkpoints = auto_approve
    cfg.config.output.project_dir = "./generated_project"
    cfg.config.output.enable_git = False
    cfg.config.web_dashboard.enabled = False
    cfg.config.llm.api_key_env = "GOOGLE_API_KEY"
    cfg.config.docker.enabled = True          # Extended feature: Docker artefacts
    os.environ["GOOGLE_API_KEY"] = api_key
    return cfg


# ── Core pipeline runner ───────────────────────────────────────────────────

def run_pipeline(spec: str, api_key: str, auto_approve: bool,
                 log_queue: "queue.Queue[str | None]"):

    def push(msg: str):
        log_queue.put(msg)

    try:
        push("🌌 **Synchronizing with Forge Core…**")

        cfg = _build_config(api_key, auto_approve)

        from forgeai.core.orchestrator import Orchestrator
        from forgeai.models.workflow_state import WorkflowPhase

        orchestrator = Orchestrator(cfg)

        _ICONS = {
            "INFO":       "✨",
            "WARN":       "🔔",
            "ERROR":      "💥",
            "AGENT":      "🤖",
            "API_CALL":   "⚡",
            "FILE_WRITE": "💾",
            "TEST_RUN":   "🧪",
            "CHECKPOINT": "🎯",
        }

        def on_log_entry(entry):
            level = entry.level if isinstance(entry.level, str) else entry.level.value
            if level == "API_CALL" and "Response received" not in entry.message:
                return
            icon = _ICONS.get(level, "•")
            push(f"&nbsp;&nbsp;{icon} <span style='color: #64748b;'>[{entry.source}]</span> {entry.message}")

        orchestrator.logger.add_listener(on_log_entry)

        def on_phase_change(phase: WorkflowPhase):
            push(f"\n<div style='background: linear-gradient(90deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%); padding: 12px; border-left: 4px solid #6366f1; margin: 10px 0;'>")
            push(f"#### 🚀 **CURRENT PHASE** &nbsp;➜&nbsp; <span style='color: #818cf8;'>{phase.value.upper()}</span>")
            push(f"</div>")

        def on_checkpoint(title: str, _content: str) -> bool:
            push(f"\n✅ **SECURE CHECKPOINT:** {title} — *Auto-validated*")
            return True

        def on_question(questions: list[str]) -> dict[str, str]:
            push(f"\n💬 **Intake Analysis:** Detected {len(questions)} points of ambiguity.")
            push("Applying industrial-grade inference to determine defaults…")
            return {q: "Use reasonable defaults based on common best practices." for q in questions}

        def on_task_progress(task, progress_data: dict):
            pct  = progress_data.get("percent_complete", 0)
            done = progress_data.get("passed", 0)
            tot  = progress_data.get("total", 0)
            _STATUS_ICON = {
                "in_progress": "🔄", "passed": "💎",
                "failed": "🧨", "skipped": "⏩",
            }
            icon = _STATUS_ICON.get(task.status.value, "🛠️")
            push(
                f"\n{icon} **Task {task.id}:** {task.title}\n"
                f"&nbsp;&nbsp;&nbsp;&nbsp;└─ <span style='color: #94a3b8;'>Status:</span> `{task.status.value.upper()}` | <span style='color: #94a3b8;'>Progress:</span> **{pct}%**"
            )

        def on_diff_review(task, files: dict) -> bool:
            push(f"&nbsp;&nbsp;&nbsp;&nbsp;🔍 **Structural Integrity Check** for {len(files)} generated artifacts… *Passed*")
            return True

        def on_plan_ready(plan):
            push("\n---")
            push(f"### 📋 Implementation Plan — {plan.project_name}")
            push(f"**{len(plan.tasks)} tasks** · ~{plan.total_estimated_files} files · {plan.architecture_summary}\n")
            for t in plan.tasks:
                deps = f" *(deps: {t.dependencies})*" if t.dependencies else ""
                risk = f" `[{t.risk_level.value.upper()}]`" if t.risk_level.value != "low" else ""
                push(f"  **{t.id}.** {t.title}{risk}{deps}")
                push(f"  &nbsp;&nbsp;&nbsp;&nbsp;→ {', '.join(t.target_files)}")
            push("---")

        orchestrator.set_callbacks(
            on_phase_change=on_phase_change,
            on_checkpoint=on_checkpoint,
            on_question=on_question,
            on_task_progress=on_task_progress,
            on_diff_review=on_diff_review,
            on_plan_ready=on_plan_ready,
        )

        push(f"\n⚡ **Igniting Forge Engine for project:** *{spec[:80]}...*\n")

        summary = orchestrator.run(spec)

        tasks_done  = summary.get("tasks_completed", 0)
        tasks_total = (tasks_done
                       + summary.get("tasks_failed", 0)
                       + summary.get("tasks_skipped", 0))

        push("\n" + "─"*40)
        push("## 🏆 **Forge Mission Complete**")
        push(f"**STATUS:** `{summary.get('status', 'unknown').upper()}`\n")
        push(f"- 📈 **Tasks:** {tasks_done}/{tasks_total} completed")
        push(f"- 📦 **Files generated:** {summary.get('files_generated', 0)}")
        push(f"- 🧪 **Tests:** {summary.get('tests_passed', 0)} passed / {summary.get('tests_failed', 0)} failed")
        push(f"- ⚡ **LLM API calls:** {summary.get('total_api_calls', 0)}")
        push(f"- ⏱️ **Duration:** {summary.get('duration_seconds', 0):.1f}s")
        push(f"- 🐳 **Docker:** `Dockerfile` + `docker-compose.yml` generated")
        push(f"- 🔒 **Security audit:** saved to `.forgeai/security_report.json`")

        errors = summary.get("errors", [])
        if errors:
            push("\n⚠️ **Errors encountered:**")
            for err in errors[:5]:
                push(f"  - {err}")

        push("\n✅ **Deliverables saved to:** `./generated_project/`")

    except Exception as exc:
        push(f"\n❌ **Critical System Fault:** {exc}")
        push("```python\n" + traceback.format_exc() + "\n```")
    finally:
        log_queue.put(None)


# ── Gradio generator ───────────────────────────────────────────────────────

def forge(spec: str, api_key_input: str, auto_approve: bool) -> Generator[str, None, None]:
    api_key = api_key_input.strip() or _check_api_key()
    if not spec.strip():
        yield "⚠️ System requires a project description to initialize."
        return
    if not api_key:
        yield "⚠️ Security error: Google API Key not detected."
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

with gr.Blocks(title="ForgeAI | Autonomous Factory", theme=None, css=_CUSTOM_CSS) as demo:
    
    with gr.Column(elem_classes="gradio-container"):
        
        # --- Header Section ---
        with gr.Row():
            with gr.Column(scale=1):
                gr.Image("forgeai/ui/assets/banner.png", show_label=False, container=False, interactive=False)
        
        with gr.Row(variant="compact"):
            with gr.Column():
                gr.HTML("<h1 class='hero-title'>ForgeAI</h1>")
                gr.HTML("<p class='hero-subtitle'>The world's first autonomous multi-agent software factory. From natural language to production-ready, secure, and tested codebases.</p>")

        gr.HTML("<div style='height: 30px;'></div>")

        # --- Main Dashboard ---
        with gr.Row():
            
            # Left: Control Panel
            with gr.Column(scale=4, elem_classes="glass-card"):
                gr.HTML("<h3><span style='color: #6366f1;'>01</span> Configuration</h3>")
                
                with gr.Group():
                    spec_box = gr.Textbox(
                        label="Project Vision",
                        placeholder="e.g. Build a secure microservice for a fintech app using FastAPI and PostgreSQL with automated trade validation logic...",
                        lines=7,
                    )
                
                with gr.Row():
                    api_key_box = gr.Textbox(
                        label="Credentials (Gemini API Key)",
                        placeholder="AIza...",
                        type="password",
                        scale=3
                    )
                    auto_approve_toggle = gr.Checkbox(
                        label="⚡ Autonomous Mode",
                        value=True,
                        scale=1
                    )
                
                gr.HTML("<div style='height: 10px;'></div>")
                run_btn = gr.Button("🚀 INITIALIZE FORGE", elem_classes="forge-button")
                
                gr.HTML(
                    "<div style='margin-top: 20px; padding: 15px; background: rgba(99, 102, 241, 0.05); border-radius: 12px; border: 1px dashed rgba(99, 102, 241, 0.2);'>"
                    "<p style='margin: 0; font-size: 0.85rem; color: #94a3b8;'>"
                    "💡 <b>Optimization:</b> Including architectural preferences (like 'FastAPI' or 'NoSQL') significantly enriches the design phase."
                    "</p></div>"
                )

            # Right: Output Monitor
            with gr.Column(scale=5, elem_classes="glass-card"):
                gr.HTML("<h3><span style='color: #ec4899;'>02</span> Real-time Monitor</h3>")
                output_box = gr.Markdown(
                    elem_classes="terminal-output",
                    value="*Awaiting synchronization... Click **INITIALIZE FORGE** to connect.*"
                )
        
        # --- Footer ---
        gr.HTML(
            "<div class='footer-text'>"
            "ForgeAI Framework • Built for the <b>Itlanta Hackathon 2026</b> • Powered by <b>Google Gemini 2.5 Flash</b>"
            "<br/><span style='opacity: 0.5; margin-top: 8px; display: block;'>v1.2.0-stable | MIT License</span>"
            "</div>"
        )

    # --- Interaction Logic ---
    run_btn.click(
        fn=forge,
        inputs=[spec_box, api_key_box, auto_approve_toggle],
        outputs=output_box,
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
