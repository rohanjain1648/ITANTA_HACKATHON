"""
ForgeAI Local Test Suite
Tests all core components without requiring a Gemini API key.
"""
import tempfile
import os
import sys

print("=" * 60)
print("ForgeAI Local Test Suite")
print("=" * 60)

# ── Test 1: ActivityLogger ────────────────────────────────────
print("\n--- Test 1: ActivityLogger ---")
from forgeai.core.activity_logger import ActivityLogger

logger = ActivityLogger("./test_run.log")
logger.info("Test", "Logger initialized")
logger.agent("intake", "Processing spec")
logger.error("coder", "Simulated error")
logger.api_call("llm_gateway", "gemini-2.5-flash call", {"tokens": 512, "model": "gemini-2.5-flash"})
entries = logger.get_entries()
assert len(entries) >= 4, f"Expected >=4 entries, got {len(entries)}"
print(f"  Log entries recorded: {len(entries)}")
print("  PASS ✓")

# ── Test 2: StructuredSpecification ──────────────────────────
print("\n--- Test 2: StructuredSpecification ---")
from forgeai.models.specification import StructuredSpecification, DataModel, APIEndpoint

spec = StructuredSpecification(
    project_name="Task API",
    summary="A simple task management REST API",
    tier=2,
    acceptance_criteria=["CRUD endpoints work", "Auth required", "Tests pass"],
    constraints=["Python backend only", "SQLite for storage"],
    tech_stack={"backend": "FastAPI", "db": "SQLite", "auth": "JWT"},
    data_models=[
        DataModel(
            name="Task",
            fields={"id": "int", "title": "str", "done": "bool", "due_date": "datetime"},
            validations=["title must not be empty", "due_date must be future"],
        )
    ],
    api_endpoints=[
        APIEndpoint(method="GET", path="/tasks", description="List all tasks"),
        APIEndpoint(method="POST", path="/tasks", description="Create task", auth_required=True),
        APIEndpoint(method="DELETE", path="/tasks/{id}", description="Delete task", auth_required=True),
    ],
)
ctx = spec.to_prompt_context()
assert spec.project_name == "Task API"
assert spec.tier == 2
assert len(spec.api_endpoints) == 3
assert len(ctx) > 100
print(f"  Project: {spec.project_name} (Tier {spec.tier})")
print(f"  Data models: {len(spec.data_models)}, API endpoints: {len(spec.api_endpoints)}")
print(f"  Prompt context: {len(ctx)} chars")
print("  PASS ✓")

# ── Test 3: AtomicTask + ImplementationPlan ───────────────────
print("\n--- Test 3: ImplementationPlan + dependency resolution ---")
from forgeai.models.task import AtomicTask, ImplementationPlan, TaskStatus, RiskLevel

plan = ImplementationPlan(
    project_name="Task API",
    tasks=[
        AtomicTask(id=1, title="Setup project structure", status=TaskStatus.PASSED, dependencies=[], risk_level=RiskLevel.LOW),
        AtomicTask(id=2, title="Create Pydantic models", status=TaskStatus.PASSED, dependencies=[1], risk_level=RiskLevel.LOW),
        AtomicTask(id=3, title="Implement database layer", status=TaskStatus.PENDING, dependencies=[1, 2], risk_level=RiskLevel.MEDIUM),
        AtomicTask(id=4, title="Implement API routes", status=TaskStatus.PENDING, dependencies=[3], risk_level=RiskLevel.MEDIUM),
        AtomicTask(id=5, title="Add JWT authentication", status=TaskStatus.PENDING, dependencies=[3], risk_level=RiskLevel.HIGH, is_checkpoint=True),
    ],
)
next_task = plan.get_next_task()
assert next_task is not None
assert next_task.id == 3, f"Expected task 3, got {next_task.id}"
progress = plan.get_progress()
assert progress["passed"] == 2
assert progress["total"] == 5
print(f"  Next task: #{next_task.id} - {next_task.title}")
print(f"  Progress: {progress['passed']}/{progress['total']} passed ({progress['percent_complete']}%)")
print(f"  Checkpoint tasks: {sum(1 for t in plan.tasks if t.is_checkpoint)}")
print("  PASS ✓")

# ── Test 4: AgentContext + AgentResult ────────────────────────
print("\n--- Test 4: AgentContext / AgentResult ---")
from forgeai.models.agent_state import AgentContext, AgentResult, AgentRole

ctx = AgentContext(
    role=AgentRole.INTAKE,
    specification=spec,
    user_input="Build a task management API with JWT auth",
    project_dir="./generated_project",
)
assert ctx.role == AgentRole.INTAKE
assert ctx.specification.project_name == "Task API"

result = AgentResult(
    success=True,
    role=AgentRole.INTAKE,
    specification=spec,
    message="Specification produced successfully",
    api_calls_made=2,
    duration_seconds=1.4,
)
assert result.success is True
assert result.api_calls_made == 2
print(f"  Context role: {ctx.role.value}")
print(f"  Result: success={result.success}, calls={result.api_calls_made}, duration={result.duration_seconds}s")
print("  PASS ✓")

# ── Test 5: WorkflowState FSM ─────────────────────────────────
print("\n--- Test 5: WorkflowState FSM transitions ---")
from forgeai.models.workflow_state import WorkflowPhase, WorkflowState

state = WorkflowState()
assert state.phase == WorkflowPhase.IDLE

state.transition_to(WorkflowPhase.INTAKE)
assert state.phase == WorkflowPhase.INTAKE

state.transition_to(WorkflowPhase.CLARIFICATION)
assert state.phase == WorkflowPhase.CLARIFICATION

state.transition_to(WorkflowPhase.SPECIFICATION)
assert state.phase == WorkflowPhase.SPECIFICATION

# Test invalid transition is blocked (returns False, does not raise)
result_invalid = state.transition_to(WorkflowPhase.DONE)
assert result_invalid is False, "Invalid transition should return False"
assert state.phase == WorkflowPhase.SPECIFICATION, "Phase should not have changed"
print(f"  Blocked invalid transition (SPECIFICATION → DONE): returned False, phase unchanged")

print(f"  Current phase: {state.phase.value}")
print("  PASS ✓")

# ── Test 6: FileManager sandbox ───────────────────────────────
print("\n--- Test 6: FileManager path-safety sandbox ---")
from forgeai.tools.file_manager import FileManager

with tempfile.TemporaryDirectory() as tmpdir:
    fm = FileManager(tmpdir, logger)
    fm.initialize_project()

    # Write and read back
    fm.write_file("src/main.py", 'print("hello forgeai")')
    fm.write_file("src/models/task.py", "class Task:\n    pass\n")
    fm.write_file("tests/test_main.py", "def test_placeholder(): pass\n")

    content = fm.read_file("src/main.py")
    assert 'print("hello forgeai")' in content

    # List files
    files = fm.list_files()
    assert len(files) == 3, f"Expected 3 files, got {len(files)}"

    # Path traversal must be blocked
    try:
        fm._validate_path("../../etc/passwd")
        print("  FAIL - path traversal should have raised ValueError")
        sys.exit(1)
    except ValueError:
        print("  Blocked path traversal (../../etc/passwd): OK")

    try:
        fm._validate_path("../outside_project.py")
        print("  FAIL - path traversal should have raised ValueError")
        sys.exit(1)
    except ValueError:
        print("  Blocked path traversal (../outside_project.py): OK")

    print(f"  Files written: {len(files)}")
    print(f"  Content verified: {content.strip()}")
print("  PASS ✓")

# ── Test 7: ConfigManager ─────────────────────────────────────
print("\n--- Test 7: ConfigManager defaults ---")
from forgeai.config.config_manager import ConfigManager

# Reset singleton for clean test
ConfigManager._instance = None
cfg = ConfigManager.get_instance()

assert cfg.llm.provider == "google"
assert cfg.llm.model == "gemini-2.5-flash"
assert cfg.llm.temperature == 0.2
assert cfg.workflow.max_retries == 3
assert cfg.guardrails.max_files_per_task == 8
assert cfg.testing.framework == "pytest"
assert cfg.testing.coverage_threshold == 70
assert "rm -rf /" in cfg.guardrails.blocked_commands

print(f"  LLM: {cfg.llm.provider}/{cfg.llm.model} (temp={cfg.llm.temperature})")
print(f"  Workflow: max_retries={cfg.workflow.max_retries}, checkpoints={cfg.workflow.checkpoints}")
print(f"  Guardrails: max_files={cfg.guardrails.max_files_per_task}, blocked_cmds={len(cfg.guardrails.blocked_commands)}")
print("  PASS ✓")

# ── Test 8: TestRunner (syntax check + real pytest run) ───────
print("\n--- Test 8: TestRunner syntax check + pytest execution ---")
from forgeai.tools.test_runner import TestRunner

with tempfile.TemporaryDirectory() as tmpdir:
    runner = TestRunner(tmpdir, timeout=30, logger=logger)

    # Write a valid Python file and check syntax via absolute path
    valid_py = os.path.join(tmpdir, "valid.py")
    with open(valid_py, "w") as f:
        f.write("def add(a, b):\n    return a + b\n")

    res = runner.check_syntax("valid.py")
    assert res["valid"] is True, f"Valid file failed syntax check: {res['error']}"
    print(f"  Valid file syntax check: OK")

    # Write an invalid Python file
    invalid_py = os.path.join(tmpdir, "invalid.py")
    with open(invalid_py, "w") as f:
        f.write("def broken(\n    return 42\n")

    res = runner.check_syntax("invalid.py")
    assert res["valid"] is False, "Invalid file should have failed syntax check"
    print(f"  Invalid file correctly caught: {res['error'].strip()[:60]}...")

    # Write a real passing pytest test and run it
    test_py = os.path.join(tmpdir, "test_sample.py")
    with open(test_py, "w") as f:
        f.write(
            "def add(a, b):\n    return a + b\n\n"
            "def test_add_positive():\n    assert add(2, 3) == 5\n\n"
            "def test_add_zero():\n    assert add(0, 0) == 0\n\n"
            "def test_add_negative():\n    assert add(-1, 1) == 0\n"
        )

    test_result = runner.run_tests()
    assert test_result.passed == 3, f"Expected 3 passed, got {test_result.passed}"
    assert test_result.failed == 0
    print(f"  pytest run: {test_result.passed} passed, {test_result.failed} failed in {test_result.duration_seconds:.2f}s")
print("  PASS ✓")

# ── Summary ───────────────────────────────────────────────────
print()
print("=" * 60)
print("  ALL 8 TESTS PASSED")
print("=" * 60)

# Clean up log file
if os.path.exists("./test_run.log"):
    os.remove("./test_run.log")
