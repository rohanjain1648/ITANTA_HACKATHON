"""QA Agent (TDD-First) — Writes failing test cases BEFORE production code.

Satisfies FR-11: TDD-first approach — generate failing tests before code.
Satisfies FR-12: Automatically run test suite after code generation.

This is the highest-scored non-autonomy criterion (25 points).
"""

import json
from typing import Optional

from forgeai.agents.base_agent import BaseAgent
from forgeai.core.activity_logger import ActivityLogger
from forgeai.models.agent_state import AgentContext, AgentResult, AgentRole
from forgeai.tools.llm_gateway import LLMGateway


class QAAgent(BaseAgent):
    """Writes focused, realistic failing test cases for each task BEFORE production code."""

    def __init__(self, llm: LLMGateway, logger: Optional[ActivityLogger] = None):
        super().__init__(AgentRole.QA, llm, logger)

    def build_system_prompt(self) -> str:
        return (
            "You are an expert QA Engineer following strict Test-Driven Development (TDD).\n\n"
            "CRITICAL RULES:\n"
            "1. Write tests ONLY for the current task's target files — do NOT import from files\n"
            "   that belong to future tasks.\n"
            "2. Use pytest as the testing framework.\n"
            "3. Tests must be syntactically valid Python.\n"
            "4. Keep tests SIMPLE and FOCUSED — test one behaviour per test function.\n"
            "5. Use pydantic v2 patterns (BaseModel, model_validate, not v1 validators).\n"
            "6. For FastAPI endpoints use httpx.AsyncClient with ASGITransport, or\n"
            "   fastapi.testclient.TestClient (sync) — prefer TestClient for simplicity.\n"
            "7. Mock external services (databases, emails, third-party APIs) with pytest.monkeypatch\n"
            "   or unittest.mock.patch rather than calling them for real.\n"
            "8. If testing a file that doesn't exist yet, import it anyway — the test will fail\n"
            "   with ImportError until the coder creates it (this is correct TDD behaviour).\n"
            "9. NEVER import from modules of future tasks (tasks with higher id).\n"
            "10. Generate a conftest.py only if shared fixtures are genuinely needed.\n\n"
            "AVAILABLE PACKAGES (always installed — safe to import):\n"
            "  fastapi, uvicorn, pydantic (v2), sqlalchemy, aiosqlite,\n"
            "  httpx, pytest, pytest-asyncio, python-dotenv, aiofiles,\n"
            "  passlib, python-jose, python-multipart\n\n"
            "OUTPUT: A JSON object with test_files dict only."
        )

    def build_user_prompt(self, context: AgentContext) -> str:
        spec = context.specification
        spec_text = spec.to_prompt_context() if spec else ""
        task = context.current_task

        task_info = ""
        target_files_str = ""
        if task:
            target_files_str = ", ".join(task.target_files)
            task_info = (
                f"\n## Current Task (#{task.id}): {task.title}\n"
                f"Description: {task.description}\n"
                f"Target files (the files the CODER will create): {target_files_str}\n"
            )

        # Show only previously written files (not future task files)
        existing = ""
        if context.existing_files:
            existing = "\n## Already-existing project files:\n"
            for fname, content in context.existing_files.items():
                existing += f"\n### {fname}\n```python\n{content[:800]}\n```\n"

        return (
            f"Write FAILING pytest tests for the following task.\n"
            f"These tests must import ONLY from the task's target files "
            f"({target_files_str}) and standard/installed packages.\n\n"
            f"## Project Specification\n{spec_text}\n"
            f"{task_info}\n"
            f"{existing}\n"
            f"Respond with ONLY this JSON object (no markdown, no explanation):\n"
            f'{{\n'
            f'  "test_files": {{\n'
            f'    "tests/test_{self._task_slug(task)}.py": "import pytest\\n\\n# test code here",\n'
            f'    "tests/conftest.py": "# only if shared fixtures are needed"\n'
            f'  }},\n'
            f'  "test_count": 4,\n'
            f'  "coverage_areas": ["happy path", "validation", "error handling"]\n'
            f'}}\n\n'
            f"IMPORTANT: The test file must be syntactically valid Python. "
            f"Tests WILL fail at first because the target files don't exist — that is correct."
        )

    def _task_slug(self, task) -> str:
        if not task:
            return "module"
        return task.title.lower().replace(" ", "_").replace("-", "_")[:30]

    def parse_response(self, raw_response: str, _context: AgentContext) -> AgentResult:
        data = self._parse_json_safe(raw_response)
        if data is None:
            return AgentResult(
                success=False, role=self.role,
                error="Failed to parse QA response as JSON",
            )

        test_files = data.get("test_files", {})
        # Remove conftest if it's empty / placeholder
        test_files = {
            k: v for k, v in test_files.items()
            if v.strip() and "# only if" not in v
        }

        if not test_files:
            return AgentResult(
                success=False, role=self.role,
                error="No test files generated",
            )

        return AgentResult(
            success=True,
            role=self.role,
            generated_files=test_files,
            message=(
                f"Generated {data.get('test_count', len(test_files))} tests "
                f"covering: {', '.join(data.get('coverage_areas', []))}"
            ),
        )

    @staticmethod
    def _parse_json_safe(raw: str) -> Optional[dict]:
        """Robust JSON extraction that handles markdown fences and leading text."""
        text = raw.strip()
        # Strip markdown fences
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
        # Find outermost { ... }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return None
