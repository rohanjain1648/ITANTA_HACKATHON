"""Coder Agent — Generates production code to make failing tests pass.

Satisfies FR-08: Invoke LLM to generate code with spec + project state context.
Satisfies FR-09: Present code as diff/summary before applying.
"""

import json
from typing import Optional

from forgeai.agents.base_agent import BaseAgent
from forgeai.core.activity_logger import ActivityLogger
from forgeai.models.agent_state import AgentContext, AgentResult, AgentRole
from forgeai.tools.llm_gateway import LLMGateway

# Packages known to be installed in the ForgeAI runtime environment.
_SAFE_PACKAGES = (
    "fastapi, uvicorn, pydantic (v2 — use `from pydantic import BaseModel, Field`; "
    "for settings use `from pydantic_settings import BaseSettings`), "
    "sqlalchemy, aiosqlite, httpx, pytest, pytest-asyncio, "
    "python-dotenv, aiofiles, passlib[bcrypt], python-jose[cryptography], "
    "python-multipart, email-validator"
)

_PYDANTIC_V2_NOTES = (
    "Pydantic v2 patterns:\n"
    "  - Use `model_config = ConfigDict(...)` NOT `class Config`\n"
    "  - Use `@field_validator` NOT `@validator`\n"
    "  - Use `model_dump()` NOT `dict()`\n"
    "  - Use `model_validate()` NOT `parse_obj()`\n"
    "  - For settings: `from pydantic_settings import BaseSettings`\n"
    "  - SQLAlchemy 2.x: use `mapped_column`, `Mapped[T]` type annotations\n"
)


class CoderAgent(BaseAgent):
    """Generates production code that satisfies the failing tests written by QA."""

    def __init__(self, llm: LLMGateway, logger: Optional[ActivityLogger] = None):
        super().__init__(AgentRole.CODER, llm, logger)

    def build_system_prompt(self) -> str:
        return (
            "You are an expert Python Software Engineer. Your job is to write "
            "production-quality code that makes the provided failing tests PASS.\n\n"
            "RULES:\n"
            "1. Read the failing tests CAREFULLY — they define exact imports, class names,\n"
            "   method signatures, and expected behaviour.\n"
            "2. Match import paths EXACTLY as written in the tests.\n"
            "3. Write COMPLETE file contents — never truncate or use '...' placeholders.\n"
            "4. Use ONLY packages from the safe list below.\n"
            "5. Never hardcode secrets, API keys, or credentials.\n"
            "6. Use proper HTTP status codes for API responses.\n"
            "7. Handle validation errors and return meaningful error messages.\n"
            "8. If a RECOVERY FIX is provided in the error context, follow it precisely.\n\n"
            f"SAFE PACKAGES (pre-installed, safe to import):\n  {_SAFE_PACKAGES}\n\n"
            f"{_PYDANTIC_V2_NOTES}"
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        spec = context.specification
        spec_text = spec.to_prompt_context() if spec else ""
        task = context.current_task

        # Gather test files (written by QA agent) — primary source of truth
        test_code = ""
        for fname, content in context.existing_files.items():
            if "test" in fname.lower() or fname.startswith("tests/"):
                test_code += f"\n### {fname}\n```python\n{content}\n```\n"

        # Gather existing production code (context for what's already built)
        prod_code = ""
        for fname, content in context.existing_files.items():
            if "test" not in fname.lower() and not fname.startswith("tests/"):
                prod_code += f"\n### {fname}\n```python\n{content[:600]}\n```\n"

        task_info = ""
        if task:
            task_info = (
                f"\n## Current Task (#{task.id}): {task.title}\n"
                f"Description: {task.description}\n"
                f"Target files to create/update: {', '.join(task.target_files)}\n"
            )

        # Separate recovery fix from raw test-failure output for clarity
        recovery_fix = ""
        raw_errors = []
        for entry in context.previous_attempts:
            if "[RECOVERY FIX" in entry:
                recovery_fix = entry
            else:
                raw_errors.append(entry)

        error_context = ""
        if context.error_message or recovery_fix:
            error_context = "\n## ⚠️ Previous Attempt Failed — Fix Required\n"
            if recovery_fix:
                error_context += (
                    f"\n### Recovery Agent Analysis (FOLLOW THIS EXACTLY):\n"
                    f"```\n{recovery_fix}\n```\n"
                )
            if context.error_message:
                error_context += (
                    f"\n### Test Output (last failure):\n"
                    f"```\n{context.error_message[-1500:]}\n```\n"
                )
            if raw_errors:
                error_context += f"\n### Prior attempts summary:\n"
                for i, e in enumerate(raw_errors[-2:], 1):
                    error_context += f"{i}. {e[:300]}\n"

        return (
            f"Write production Python code so that ALL the tests below PASS.\n\n"
            f"## Project Specification\n{spec_text}\n"
            f"{task_info}\n"
            f"## Failing Tests (match these imports & signatures EXACTLY):\n{test_code}\n"
            f"## Existing Production Code (do not break these):\n{prod_code}\n"
            f"{error_context}\n"
            f"Respond with ONLY this JSON (no markdown, no explanation):\n"
            f'{{\n'
            f'  "files": {{\n'
            f'    "src/module.py": "# complete file content",\n'
            f'    "requirements.txt": "fastapi\\nuvicorn\\n..."\n'
            f'  }},\n'
            f'  "explanation": "what was implemented",\n'
            f'  "dependencies_added": []\n'
            f'}}\n\n'
            f"CRITICAL: Include COMPLETE file contents. The code MUST make all tests pass."
        )

    def parse_response(self, raw_response: str, _context: AgentContext) -> AgentResult:
        data = self._parse_json_safe(raw_response)
        if data is None:
            return AgentResult(
                success=False, role=self.role,
                error="Failed to parse coder response as JSON",
            )

        files = data.get("files", {})
        if not files:
            return AgentResult(
                success=False, role=self.role,
                error="No files generated by coder agent",
            )

        return AgentResult(
            success=True,
            role=self.role,
            generated_files=files,
            message=f"Generated {len(files)} file(s): {data.get('explanation', '')}",
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
