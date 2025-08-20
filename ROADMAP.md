CanvasAgent Roadmap
====================

Purpose: Evolve CanvasAgent from a prototype (assignments/modules + heuristic NL) into a comprehensive teacher co-pilot with robust API coverage, safer execution, testing, and autonomous planning.

Current State (Baseline)
------------------------
Implemented:
- Streamlit chat UI packaged under `python/canvas_agent/apps/streamlit_app.py`.
- Enhanced Canvas client: courses, assignments, modules, module items, files (list only), announcements, students, user profile.
- Natural language dispatcher: hybrid fast heuristics + LLM (Ollama) fallback; quiz = assignment surrogate.
- Fast heuristics: create quiz/assignment name/points/question/answers, topic extraction ("about inertia"), simple due date phrases (tomorrow, next Friday), follow-up add to module.
- MCP server (TypeScript) with initial tools: `create_assignment`, `attach_rubric_to_assignment`.

Gaps / Missing Teacher Capabilities
-----------------------------------
- Real quizzes (Canvas Quizzes API & question bank management).
- Pages (wiki pages) create/list/update.
- File upload (current client only lists files).
- Discussions (full threads, replies) distinct from announcements.
- Rubric CRUD & association (Python layer parity with MCP partial tool).
- Assignment updates (edit description, points, due dates) & deletion.
- Rich date/time parsing ("next Monday 5pm", "in 2 weeks", natural language ranges).
- Bulk operations (e.g., generate weekly modules with assignments & pages).
- Grading workflows (list submissions, grade, comment, rubric assessment).
- Messaging / announcements improvements (send message to all students / sections).
- Analytics & progress summaries (late submissions, average scores).
- Outcome/objective alignment, mastery paths (advanced).
- Autonomy / multi-step planning (plan-execute-confirm loops) beyond single intent turn.
- Safety / confirmation for destructive or bulk actions.
- Comprehensive test suite (unit + integration + mock Canvas fixtures).
- Structured action metadata, validation & clarification prompts.

Strategic Phases
----------------
Phase 1 (Foundational Expansion) [IN PROGRESS]
- Add Pages support: list/create simple HTML page.
- Add File upload abstraction (two-step Canvas upload) + keep existing list_files.
- Add Assignment update action (change description, due date).
- Extend heuristic & date parsing (next weekday, in N days/weeks, simple "on Sept 5").
- Introduce ROADMAP (this file) & starter tests for heuristics.

Phase 2 (Assessment Depth)
- Implement real Quiz creation (Classic Quizzes API) with MC question creation.
- Migrate heuristic: if user explicitly wants "quiz" use real quiz endpoint.
- Add rubric CRUD (create_rubric, list_rubrics) & attach rubric (Python parity with MCP).
- Support attaching rubric during assignment/quiz creation via heuristic fields.

Phase 3 (Content & Communication)
- Discussions: list/create topic, reply, close.
- Pages: update, publish toggle, link insertion helper.
- Announcements enhancements (scheduling if available, filtering).
- Messaging: send conversation messages to students (batch + rate limit safety).

Phase 4 (Grading & Feedback)
- List submissions, pull submission details & comments.
- Grade submission (points, comments, rubric associations).
- Bulk grading suggestions (LLM summarization of common feedback).
- Late / missing work report generation.

Phase 5 (Bulk Operations & Planning)
- Generate full module structure for a week/unit (pages, assignment shells, discussions) from a single instruction.
- Multi-step plan graph: plan -> confirm -> execute sequence.
- Template library (JSON / YAML patterns) & cloning.

Phase 6 (Advanced Intelligence / Autonomy)
- Calendar-aware scheduling (avoid weekends, set due times at 11:59 local, skip holidays via config).
- Learning analytics summarization & adaptive suggestions.
- Outcome alignment suggestions (map tasks to outcomes).
- Multi-turn goal pursuit with rollback on failure.

Cross-Cutting Concerns (All Phases)
- Testing: Expand `tests/` with deterministic mocks for Canvas endpoints.
- Error handling & resilience: typed exceptions, clearer user feedback.
- Action schema & validation: central registry describing required & optional params.
- Security & Safety: confirmation prompts for publish/unpublish, bulk deletions.
- Caching & rate limit strategy tuning.
- Telemetry / instrumentation hooks (opt-in).
- Documentation: user guides for each new capability.

MCP Integration Roadmap
-----------------------
- Mirror Python client coverage with MCP tools for environments that only use MCP.
- Add tool metadata (input schemas) enabling external orchestrators.
- Streaming progress events (start/success/failure) for long-running bulk ops.
-
Why It Can't Do "Full Teacher" Yet
----------------------------------
1. API Coverage Gaps: Core endpoints (quizzes, pages CRUD, discussions, submissions, rubrics) not yet implemented in Python client or dispatcher.
2. Heuristic Scope: Fast parser only understands quiz/assignment creation & simple module linking; lacks pattern library for pages, uploads, grading.
3. LLM Delegation Limits: The LLM layer still constrained by missing downstream actions— even if it interprets an intent, there is no registered action to execute.
4. Absence of Multi-Step Planning: Complex tasks ("build week 2 with readings, a quiz Friday, forum Monday") require orchestrated sequence & confirmations; current architecture executes one action per turn.
5. Safety & Validation: Without structured schema validation and confirmation, expanding to powerful destructive actions is risky; intentionally omitted so far.
6. Incomplete MCP Tooling: MCP server only exposes a tiny subset; orchestrators cannot call broader functions.
7. Date/Time Semantics: Limited phrase parsing leads to frequent clarifications or incorrect scheduling for natural teacher phrasing.
8. Testing & Reliability Gaps: Lack of tests for new actions would make rapid expansion brittle; deferred until after initial refactor.

Phase 1 Detailed Task List (Current Focus)
-----------------------------------------
- [x] Roadmap file.
- [ ] Pages: list_pages, create_page (client + dispatcher).
- [ ] File upload: upload_file (client + dispatcher) basic path.
- [ ] Assignment update: update_assignment (due date, description) minimal.
- [ ] Heuristic extensions: detect page creation & file upload phrasing; improved due date phrases.
- [ ] Date parsing helper `_parse_due_date` centralizing logic.
- [ ] Tests: heuristic parser (quiz, page, date phrases) baseline.
- [ ] Action registry documentation update.

Success Criteria for Phase 1
----------------------------
- User can say: "Create a page titled Class Policies about late work in course 123" -> page created.
- User can say: "Upload file syllabus.pdf to course 123" -> file appears in Files.
- User can say: "Update assignment 456 set due next Monday 5pm" -> due date updated.
- User can say: "Create a quiz about mitosis due in 2 weeks" -> assignment surrogate with correct due date.

Testing Strategy (Incremental)
------------------------------
- Mock Canvas responses with fixture JSON (no real network) for parser tests.
- Unit tests for `_fast_intent_parse` & `_parse_due_date` edge cases.
- Smoke integration (optionally, behind env var) hitting a test Canvas instance.

Risks & Mitigations
-------------------
- API Rate Limits: Add adaptive backoff (already partial) + caching for list endpoints.
- Ambiguous NL Intents: Provide clarification prompts referencing required params.
- Data Loss / Destructive Actions: Add confirmation or dry-run preview before deletes or mass updates (future phases).
- Time Zone Issues: Store / display timezone assumption; later add configuration & conversion.

Next Immediate Steps
--------------------
1. Finalize Phase 1 checkboxes (mark implemented features as done).
2. Implement Phase 2 (real quizzes + rubric CRUD + attach).
3. Add/update tests focusing on quiz/rubric creation heuristics.
4. Document new actions in README.
5. Prepare issue labels for future phases.

--
Maintained: auto-generated initial version (Phase 1 start). Update as tasks complete.
