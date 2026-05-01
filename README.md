---
title: ForgeAI
emoji: 🔨
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
short_description: Turn plain English ideas into production-ready code
---

<div align="center">

```
       
 
         
          
         
             
```

### *From Idea to Production-Ready Code — Autonomously*

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-1M_Context-4285F4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Itlanta_Hackathon-2026-FF6B35?style=for-the-badge)
![TDD](https://img.shields.io/badge/TDD-First-red?style=for-the-badge)
![Agents](https://img.shields.io/badge/Agents-7_Specialized-purple?style=for-the-badge)

**ForgeAI** is an autonomous multi-agent system that transforms a natural-language project idea into a fully functional, tested, and production-ready software application — without you writing a single line of code.

Built for the **Itlanta Hackathon 2026** | Powered by **Google Gemini 2.5 Flash** | Orchestrated by a **16-state FSM**

</div>

---

## Table of Contents

1. [The Problem](#-the-problem)
2. [The Solution](#-the-solution)
3. [Features](#-features)
4. [User Journey](#-user-journey)
5. [Architecture](#-architecture)
6. [Workflow — The 16-State FSM](#-workflow--the-16-state-fsm)
7. [Tech Stack](#-tech-stack)
8. [AI Deep Dive — Gemini 2.5 Flash](#-ai-deep-dive--gemini-25-flash)
9. [Impact](#-impact)
10. [Real-World Use Cases](#-real-world-use-cases)
11. [Comparison](#-comparison)
12. [Scalability](#-scalability)
13. [Security & Ethics](#-security--ethics)
14. [Trade-offs](#-trade-offs)
15. [Project Complexity Tiers](#-project-complexity-tiers)
16. [Installation & Setup](#-installation--setup)
17. [Why This Will Win](#-why-this-will-win)
18. [Future Scope](#-future-scope)
19. [FAQ](#-faq)
20. [Lessons Learned](#-lessons-learned)

---

##  The Problem

Modern software development is still fundamentally **reactive**. AI tools like GitHub Copilot and Cursor are powerful autocomplete engines — they respond to what you type, line by line. But they don't *think* about your project. They don't plan. They don't test. They don't recover from their own mistakes.

The result? Developers still spend the majority of their time on **boilerplate, scaffolding, wiring, and debugging** — the mechanical work that doesn't require human creativity.

### The Gap in AI-Assisted Development

```
What AI tools do today:          What developers actually need:
      
  You type  AI suggests   vs    You describe  AI delivers     
  Line-by-line autocomplete      Full project, tested & working 
  No planning                    Upfront architecture design    
  No testing                     TDD-first verification         
  No error recovery              Self-healing on failure        
  No security audit              Built-in security scanning     
  You debug everything           Autonomous debugging           
      
```

### Why Reactive Tools Don't Scale

- **Context blindness** — Copilot doesn't know your full architecture. It suggests code that conflicts with decisions made 10 files ago.
- **No verification loop** — Generated code is never automatically tested. Bugs ship silently.
- **No recovery mechanism** — When generated code fails, you're on your own.
- **Cognitive overhead** — You still have to hold the entire project in your head, decompose tasks, manage dependencies, and orchestrate the build.
- **Security blind spots** — No tool automatically audits generated code for injection vulnerabilities, hardcoded secrets, or auth bypasses.

The gap isn't in code generation quality. It's in **autonomous orchestration** — the ability to plan, execute, verify, recover, and deliver end-to-end without constant human intervention.

---

##  The Solution

ForgeAI is not a code assistant. It's an **autonomous software factory**.

You describe what you want to build in plain English. ForgeAI handles everything else: clarifying ambiguities, designing the architecture, planning the implementation, writing tests first, generating production code, running the tests, recovering from failures, auditing for security vulnerabilities, and delivering a complete, working project.

### What Makes ForgeAI Different

| Dimension | Traditional AI Tools | ForgeAI |
|-----------|---------------------|---------|
| **Input** | Code context / cursor position | Natural language project description |
| **Output** | Code suggestions | Complete, tested, working project |
| **Planning** | None | 8-15 atomic tasks with dependency graph |
| **Testing** | None | TDD-first: tests written before code |
| **Recovery** | None | 4-tier cascade with error context accumulation |
| **Security** | None | Post-completion vulnerability audit |
| **Orchestration** | None | 16-state validated FSM |
| **Human control** | Always required | Configurable checkpoints or fully autonomous |

### The Core Insight

> **A single monolithic LLM prompt cannot handle the full complexity of software development.**

By decomposing the problem into 7 specialized agents — each with a focused system prompt, receiving only the context it needs, producing a well-defined output — ForgeAI achieves a level of reliability and correctness that no single-prompt approach can match.

Each agent follows the **Single Responsibility Principle**: one job, one output, no side effects. The Orchestrator coordinates them through a validated state machine, ensuring the pipeline always follows the correct sequence.

---

##  Features

### Core Pipeline
-  **7 Specialized AI Agents** — Intake, Architect, Planner, QA, Coder, Security, Recovery, each with a focused role
-  **16-State Validated FSM** — Every state transition is checked; invalid transitions are rejected and logged
-  **TDD-First by Design** — QA Agent writes failing pytest tests *before* the Coder Agent writes a single line of production code
-  **Atomic Task Decomposition** — Projects broken into 8-15 independent, verifiable tasks with dependency graphs
-  **4-Tier Recovery Cascade** — RETRY_WITH_FIX  MODIFY_APPROACH  SKIP_TASK  ESCALATE

### Intelligence & Context
-  **1M Token Context Window** — Full project state (spec + architecture + all files + error history) fits in a single prompt
-  **Progressive Error Context Enrichment** — Each retry attempt receives richer error context than the last
-  **Architecture-First** — Architect Agent designs directory layout, data models, and API contracts before any code is written
-  **Ambiguity Detection** — Intake Agent identifies vague requirements and generates 5-7 targeted clarifying questions

### Safety & Control
-  **Sandboxed FileManager** — Agents cannot write outside `./generated_project/`; path validation enforced at the tool layer
-  **Human-in-the-Loop Checkpoints** — 4 configurable pause points for human review (spec, architecture, plan, per-diff)
-  **Auto-Approve Mode** — Zero-touch demo mode: spec to deliverable with no human intervention
-  **Security Audit** — Post-completion scan for SQL injection, hardcoded secrets, path traversal, auth bypass, command injection
-  **YAML Guardrails** — Configurable limits: max files per task, max lines per file, blocked shell commands

### Developer Experience
-  **Rich CLI** — Animated progress, colored output, live status panels powered by the Rich library
-  **Web Dashboard** — Real-time observability via FastAPI + WebSockets; watch the pipeline execute live
-  **Docker Support** — Optional `docker-compose.yml` generation for containerized deployment
-  **Workflow Summary Report** — Complete audit trail: tasks completed, files generated, tests passed, API calls made
-  **Activity Log** — Timestamped, append-only log of every agent action and state transition
-  **Rollback Support** — Roll back to the last passing checkpoint if a task fails unrecoverably

### Output Artifacts
- `structured_specification.yaml` — Machine-readable project spec
- `architecture.json` — Complete architecture design decisions
- `implementation_plan.json` — Ordered task list with dependencies and risk levels
- Generated project source code with full directory structure
- TDD test suite (written before production code)
- `security_report.json` — Vulnerability scan results
- `workflow_summary.json` — Complete execution report
- `forgeai_activity.log` — Full audit trail
- `docker-compose.yml` — Container orchestration (optional)

---

##  User Journey

Here's what a developer experiences when using ForgeAI from start to finish:

### Step 1 — Describe Your Idea
```bash
python -m forgeai.main --spec "Build a Task Management REST API with user authentication, 
due date logic, priority levels, and email notifications"
```

### Step 2 — Answer Clarifying Questions
ForgeAI's Intake Agent detects ambiguities and asks targeted questions:
```
ForgeAI detected 6 ambiguities in your specification. Please answer:

  1. Authentication method: JWT tokens, OAuth2, or API keys?
  2. Database: PostgreSQL, SQLite, or MongoDB?
  3. Email provider: SendGrid, SMTP, or mock for testing?
  4. Should tasks support subtasks/nesting?
  5. Priority levels: numeric (1-5) or named (Low/Medium/High/Critical)?
  6. Should overdue tasks trigger automatic notifications?

> Your answers: JWT, PostgreSQL, SendGrid, No, Named, Yes
```

### Step 3 — Review the Structured Specification
```
 Specification Generated
   Project: task-management-api
   Tier: 3 (Live Bridge — async 3rd-party API integration)
   Functional Requirements: 12 items
   API Endpoints: 8 endpoints
   Data Models: User, Task, Notification
   Tech Stack: FastAPI, PostgreSQL, SQLAlchemy, JWT, SendGrid

   [APPROVE] [REQUEST CHANGES]
```

### Step 4 — Review the Architecture
```
 Architecture Designed
   Directory Layout: src/, tests/, models/, routes/, config/
   Data Models: User (id, email, hashed_password), Task (id, title, due_date, priority, owner_id)
   API Contracts: POST /auth/register, POST /auth/login, GET/POST/PUT/DELETE /tasks
   Technology Choices: FastAPI, SQLAlchemy ORM, Alembic migrations, python-jose JWT

   [APPROVE] [REQUEST REDESIGN]
```

### Step 5 — Review the Implementation Plan
```
 Implementation Plan (12 tasks)

   Task 1  [LOW]      Database models and migrations
   Task 2  [LOW]      Password hashing utilities
   Task 3  [MEDIUM]   JWT authentication service
   Task 4  [HIGH]   User registration and login endpoints
   Task 5  [MEDIUM]   Task CRUD endpoints
   Task 6  [MEDIUM]   Due date validation logic
   Task 7  [HIGH]     Priority level business rules
   Task 8  [HIGH]   SendGrid email integration
   Task 9  [LOW]      Overdue task detection scheduler
   Task 10 [MEDIUM]   Notification trigger logic
   Task 11 [LOW]      Error handling middleware
   Task 12 [LOW]      API documentation and health check

    = Human checkpoint required
   [APPROVE AND START] [REQUEST MODIFICATIONS]
```

### Step 6 — Watch the TDD Loop Execute
```
[TASK 1/12] Database models and migrations
   QA Agent writing tests...      tests/test_models.py (4 tests)
    Coder Agent generating code...  src/models/user.py, src/models/task.py
   Running pytest...               4/4 tests passed

[TASK 3/12] JWT authentication service
   QA Agent writing tests...      tests/test_auth.py (5 tests)
    Coder Agent generating code...  2/5 tests failed
   Recovery Agent diagnosing...    RETRY_WITH_FIX: "Use HS256 algorithm, not RS256"
    Coder Agent retry (2/3)...     5/5 tests passed
```

### Step 7 — Security Audit
```
 Security Audit Complete
   Scanned: 23 files, 1,847 lines
    No SQL injection vulnerabilities
    No hardcoded secrets detected
    No path traversal vulnerabilities
     WARNING: JWT expiry not configured (recommended: 3600s)
    No command injection patterns
```

### Step 8 — Receive Your Project
```
 ForgeAI Complete!

   Generated: task-management-api/
    src/
       models/        (user.py, task.py)
       routes/        (auth.py, tasks.py, notifications.py)
       services/      (auth_service.py, email_service.py, scheduler.py)
       config/        (database.py, settings.py)
    tests/             (12 test files, 47 test functions)
    alembic/           (database migrations)
    docker-compose.yml
    README.md

    Summary: 12/12 tasks passed | 47/47 tests green | 0 security issues
     Total time: 4m 23s | LLM calls: 38 | Tokens used: ~180,000
```

---
