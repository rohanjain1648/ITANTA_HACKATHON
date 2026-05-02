"""Recovery Agent — Diagnoses failures and orchestrates recovery strategies.

Satisfies FR-15: Auto-retry with error context on failure.
Satisfies FR-17: Rollback to last checkpoint on abort.
"""

import json
from typing import Optional

from forgeai.agents.base_agent import BaseAgent
from forgeai.core.activity_logger import ActivityLogger
from forgeai.models.agent_state import AgentContext, AgentResult, AgentRole
from forgeai.tools.llm_gateway import LLMGateway


class RecoveryAgent(BaseAgent):
    """Diagnoses failures and decides recovery strategy: retry, modify, rollback, or escalate."""

    def __init__(self, llm: LLMGateway, logger: Optional[ActivityLogger] = None):
        super().__init__(AgentRole.RECOVERY, llm, logger)

    def build_system_prompt(self) -> str:
        return (
            "You are an expert Python Debugging AI. When generated code or tests fail, "
            "you diagnose the ROOT CAUSE and provide SPECIFIC, ACTIONABLE fix instructions.\n\n"
            "Recovery strategies:\n"
            "  RETRY_WITH_FIX    — You know exactly what to change; give line-level instructions.\n"
            "  MODIFY_APPROACH   — The design is wrong; suggest a completely different approach.\n"
            "  SKIP_TASK         — The task is non-critical and blocking progress; skip it.\n"
            "  ESCALATE          — Unrecoverable without human intervention.\n\n"
            "DIAGNOSIS CHECKLIST:\n"
            "  1. ImportError / ModuleNotFoundError → which file is missing or misnamed?\n"
            "  2. AttributeError → which attribute is missing from which class?\n"
            "  3. AssertionError → what value did the test expect vs. what was returned?\n"
            "  4. TypeError → wrong function signature, missing args, or wrong type?\n"
            "  5. SyntaxError → exact line and file with the syntax problem?\n"
            "  6. Pydantic ValidationError → which field failed, what type was expected?\n\n"
            "Fix instructions MUST be file-specific:\n"
            "  'In src/models.py, change class User to add field `email: str`'\n"
            "  'In src/api.py line ~20, change return type from dict to UserResponse'\n\n"
            "Prefer RETRY_WITH_FIX — only use SKIP_TASK or ESCALATE as a last resort."
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        task = context.current_task
        task_info = (
            f"Task #{task.id}: {task.title}\n{task.description}"
            if task else "Unknown task"
        )
        target_files = ", ".join(task.target_files) if task else "unknown"

        # Show full current code (truncated per file to keep prompt manageable)
        code_context = ""
        for fname, content in context.existing_files.items():
            snippet = content[:1200] if len(content) > 1200 else content
            code_context += f"\n### {fname}\n```python\n{snippet}\n```\n"

        # Format previous attempts concisely
        prev = ""
        for i, attempt in enumerate(context.previous_attempts[-3:], 1):
            prev += f"\nAttempt {i}:\n{attempt[:400]}\n"

        return (
            f"A code generation task FAILED. Diagnose and provide a fix.\n\n"
            f"## Task\n{task_info}\n"
            f"Target files: {target_files}\n\n"
            f"## Test Failure Output\n```\n{context.error_message[-2500:]}\n```\n\n"
            f"## Stderr / Traceback\n```\n{context.error_traceback[-800:]}\n```\n\n"
            f"## Attempt #{context.retry_count + 1} of 3\n{prev}\n\n"
            f"## Current Code\n{code_context}\n\n"
            f"Respond with ONLY this JSON (no markdown):\n"
            f'{{\n'
            f'  "diagnosis": {{\n'
            f'    "root_cause": "Precise description of what went wrong",\n'
            f'    "error_type": "ImportError|AttributeError|AssertionError|TypeError|SyntaxError|ValidationError|other",\n'
            f'    "error_in": "test_code|production_code|both|configuration",\n'
            f'    "affected_files": ["src/models.py"]\n'
            f'  }},\n'
            f'  "strategy": "RETRY_WITH_FIX",\n'
            f'  "fix_instructions": "Specific file-by-file instructions for the Coder Agent",\n'
            f'  "modified_test_code": {{}},\n'
            f'  "confidence": 0.9\n'
            f'}}\n\n'
            f"IMPORTANT: Respond ONLY with valid JSON. Be specific — vague instructions cause more failures."
        )

    def parse_response(self, raw_response: str, _context: AgentContext) -> AgentResult:
        data = self._parse_json_safe(raw_response)
        if data is None:
            return AgentResult(
                success=False, role=self.role,
                error="Failed to parse recovery response as JSON",
            )

        strategy = data.get("strategy", "ESCALATE")
        if strategy not in ("RETRY_WITH_FIX", "MODIFY_APPROACH", "SKIP_TASK", "ESCALATE"):
            strategy = "RETRY_WITH_FIX"

        diagnosis = data.get("diagnosis", {})
        fix_instructions = data.get("fix_instructions", "")
        modified_tests = data.get("modified_test_code", {})

        return AgentResult(
            success=True,
            role=self.role,
            message=(
                f"Recovery: {strategy} | "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')} | "
                f"Fix: {fix_instructions[:200]}"
            ),
            requires_human_input=(strategy == "ESCALATE"),
            generated_files=modified_tests if modified_tests else {},
            architecture={
                "strategy": strategy,
                "diagnosis": diagnosis,
                "fix_instructions": fix_instructions,
                "confidence": data.get("confidence", 0.0),
            },
        )

    @staticmethod
    def _parse_json_safe(raw: str) -> Optional[dict]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.rstrip().endswith("```"):
                text = "\n".join(text.rstrip().split("\n")[:-1])
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return None
