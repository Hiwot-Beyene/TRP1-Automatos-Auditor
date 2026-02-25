# Functional Specification: Automaton Auditor

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2 — The Automaton Auditor  
**Purpose**: Defines *what* the system does: inputs, outputs, behaviors, and rules. No implementation details.

---

## 1. System Purpose

The system is a **Digital Courtroom** implementing a **Hierarchical State Graph**. A single LLM cannot do this job; it requires specialized roles.

- **Input:** One GitHub repository URL and one PDF report path.
- **Process:** Detectives collect facts (no opinions) → Judges deliberate per rubric criterion (three distinct personas, same evidence) → Chief Justice synthesizes verdict via deterministic rules.
- **Output:** A production-grade Audit Report (Markdown) that stands up to scrutiny.

**Applicability:** Automated Security Audits, Compliance Governance, Architectural Review.

---

## 2. Inputs and Outputs

| Role | Input | Output |
|------|--------|--------|
| **System** | Repository URL (string), PDF report path (string), optional rubric path | Markdown Audit Report file |
| **Detectives** | Repo URL / PDF path / images; rubric dimensions filtered by `target_artifact` | Structured Evidence objects (facts only; untainted by bias) |
| **Judges** | Aggregated evidence for one criterion; rubric judicial logic | One JudicialOpinion per judge (Prosecutor, Defense, Tech Lead) |
| **Chief Justice** | All JudicialOpinions; synthesis rules | One AuditReport: verdict per criterion, dissent summary, file-level remediation plan |

---

## 3. Detective Layer (Forensic Sub-Agents)

Detectives **do not opinionate**. They only collect facts based on strict forensic protocols. Output is a structured JSON Evidence object.

### 3.1 RepoInvestigator (Code Detective) — Target: GitHub Repository

**Tools (capabilities):** git clone, git log, file_read, ast_parse (Python `ast` module or tree-sitter).

| Evidence Class | Instruction | Success Pattern | Failure Pattern | Capture |
|----------------|-------------|------------------|-----------------|---------|
| **Git Forensic Analysis** | Run `git log --oneline --reverse`. Count commits; check progression: Environment Setup → Tool Engineering → Graph Orchestration. Extract timestamps. | >3 commits; atomic, step-by-step history; meaningful messages. | Single "init" or "bulk upload"; timestamps clustered in minutes. | List of commit messages and timestamps. |
| **State Management Rigor** | Scan for `src/state.py` or equivalent in `src/graph.py`. AST (not regex): classes inheriting BaseModel (Pydantic) or TypedDict. Does state maintain Evidence collection and JudicialOpinion list? Reducers operator.add, operator.ior in Annotated? | Typed state with reducers. | Plain dicts; no Pydantic; no reducers (parallel overwrites). | Code snippet of core AgentState definition. |
| **Graph Orchestration** | Find StateGraph builder. **Do not just check for string "StateGraph".** AST on `builder.add_edge()` / `builder.add_conditional_edges()`: Do Detectives fan-out? Sync node (fan-in) before Judges? Judges fan-out and fan-in before ChiefJustice? Conditional edges for errors? | Two parallel fan-out/fan-in patterns; conditional edges. | Linear flow; no sync node; no conditional edges. | Python block defining graph nodes and edges. |
| **Safe Tool Engineering** | In `src/tools/`: clone uses `tempfile.TemporaryDirectory()`? No raw `os.system`; input sanitization; error handling stdout/stderr. | tempfile sandbox; subprocess with error handling; no os.system; auth errors handled. | Clone into live dir; no error handling; unsanitized URL. | Function that executes repository clone. |
| **Structured Output** | In `src/nodes/judges.py`: LLM using `.with_structured_output()` or `.bind_tools()` bound to JudicialOpinion? Retry on malformed output? | Structured output + retry/validation. | Freeform text; no Pydantic validation. | Code block querying Judge LLMs. |

### 3.2 DocAnalyst (Paperwork Detective) — Target: PDF Report

**Tools:** pdf_parse, markdown_read, cross_reference.

| Evidence Class | Instruction | Success Pattern | Failure Pattern | Capture |
|----------------|-------------|------------------|-----------------|---------|
| **Theoretical Depth** | Search: "Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization". Substantive architectural explanation or buzzword in exec summary only? | Terms in detailed architectural explanations; report explains *how* architecture executes them. | Terms only in exec summary; no link to implementation; "Keyword Dropping". | Sentences detailing orchestration concepts. |
| **Report Accuracy (Host Analysis)** | Extract file paths mentioned in report (e.g. "We implemented parallel Judges in `src/nodes/judges.py`"). Cross-reference with RepoInvestigator: do files exist? If report cites non-existent file → **flag "Hallucination."** | All mentioned paths exist; feature claims match code. | Report cites non-existent files; claims contradict evidence. | Verified Paths vs Hallucinated Paths. |

### 3.3 VisionInspector (Diagram Detective) — Target: Extracted Images

**Tools:** image_analysis (e.g. Gemini Pro Vision / GPT-4o).

| Evidence Class | Instruction | Success Pattern | Failure Pattern | Capture |
|----------------|-------------|------------------|-----------------|---------|
| **Swarm Visual** | Analyze diagrams. Type: LangGraph State Machine, sequence diagram, or generic flowchart boxes? Does arrow flow show: Detectives (Parallel) → Evidence Aggregation → Judges (Parallel) → Synthesis? Or simple linear pipeline? | Diagram shows parallel branches and fan-in/fan-out clearly. | Linear pipeline only; no parallelism; or no diagram. | Classification string and structural description of flow. |

---

## 4. Judicial Layer (The Dialectical Bench)

The Judicial Layer applies rubric point assignments by **criterion-by-criterion** analysis through **distinct persona lenses**. Dialectical model: Thesis–Antithesis–Synthesis. **Do not** feed evidence to a generic "Grader." Three distinct personas analyze the **same evidence** for **each rubric criterion** independently.

### 4.1 Judicial Workflow (per criterion)

1. **State Input:** Evidence object (e.g. "Graph builds linearly, no parallel branches detected").
2. **Parallel Execution:** Prosecutor, Defense, Tech Lead each submit one opinion (score + reasoning).
3. **Output:** A list of JudicialOpinion objects containing three conflicting views.

### 4.2 Prosecutor (Critical Lens)

- **Philosophy:** "Trust No One. Assume Vibe Coding."
- **Objective:** Scrutinize for gaps, security flaws, laziness.
- **Charges (Protocol B — Statute of Orchestration):**  
  - **Orchestration Fraud:** StateGraph purely linear (e.g. RepoInvestigator → DocAnalyst → Judge → End) instead of parallel fan-out → Max Score "LangGraph Architecture" = 1.  
  - **Hallucination Liability:** Judge nodes return freeform text, no Pydantic validation → Max Score "Judicial Nuance" = 2.
- **Prompting:** If rubric asks "Parallel Orchestration" and evidence shows "Linear pipeline," argue Score 1. Look for bypassed structure. Provide harsh score and list of specific missing elements.

### 4.3 Defense Attorney (Optimistic Lens)

- **Philosophy:** "Reward Effort and Intent. Spirit of the Law."
- **Objective:** Highlight creative workarounds, deep thought, effort even if implementation imperfect.
- **Mitigations (Protocol B — Statute of Effort):**  
  - StateGraph fails to compile (minor edge error) but AST parsing for Detectives is sophisticated → "Deep code comprehension, tripped on framework syntax" → Request boost Forensic Accuracy 1→3.  
  - Chief Justice is LLM prompt not hardcoded rules, but Judge personas distinct and actively disagree → "Role separation successful, dialectical tension" → Partial credit Judicial Nuance 3 or 4.
- **Prompting:** If code buggy but architecture report shows deep understanding of LangGraph state reducers, argue "Master Thinker" despite syntax errors. Use Git History: if commits tell story of struggle/iteration, argue "Engineering Process." Generous score; highlight strengths.

### 4.4 Tech Lead (Pragmatic Lens)

- **Philosophy:** "Does it actually work? Is it maintainable?"
- **Objective:** Architectural soundness, code cleanliness, practical viability.
- **Precedents (Protocol B — Statute of Engineering):**  
  - **Pydantic Rigor vs. Dict Soups:** State and JSON outputs must use typed structures (BaseModel). Plain dicts for complex nested state → "Technical Debt," Score = 3.  
  - **Sandboxed Tooling:** If `os.system('git clone <url>')` drops code into live working directory → "Security Negligence"; overrides all effort points for "Forensic Accuracy."
- **Prompting:** Ignore "Vibe" and "Struggle." Focus on artifacts: Is `operator.add` reducer used to prevent overwriting? Are tool calls isolated and safe? Tie-breaker between Prosecutor (e.g. 1) and Defense (e.g. 5). Realistic score (1, 3, or 5); technical remediation advice.

---

## 5. Chief Justice (Synthesis Engine)

**Input:** JudicialOpinion objects (Prosecutor, Defense, Tech Lead) for **every** criterion.  
**Role:** Resolve dialectical conflict; **do not** merely average scores. Produce final, actionable ruling.

### 5.1 Deliberation Protocol (Hardcoded Rules)

| Rule | Behavior |
|------|----------|
| **Rule of Security** | If Prosecutor identifies confirmed security vulnerability (e.g. `os.system` with unsanitized inputs), override any "Effort" points from Defense. Security flaws cap score at 3. |
| **Rule of Evidence** | If Defense claims "Deep Metacognition" but RepoInvestigator found no PDF report, overrule Defense for hallucination. |
| **Rule of Functionality** | If Tech Lead confirms architecture is modular and workable, that carries highest weight for "Architecture" criterion. |
| **Dissent Requirement** | When score variance > 2, final report must include explicit dissent summary for that criterion. |
| **Variance Re-Evaluation** | When variance > 2 (e.g. Prosecutor 1, Defense 5), trigger re-evaluation of evidence cited by each judge before rendering final score. |

### 5.2 Output Generation (Audit Report)

Structured Markdown report containing:

1. **The Verdict** — Final score (1–5) per criterion.
2. **The Dissent** — Summary of conflict (e.g. "Defense argued for code effort; Prosecutor correctly noted graph fails to compile due to missing state reducers").
3. **The Remediation Plan** — Specific, file-level instructions for the trainee.

---

## 6. Key Integration Steps (Constitution)

- **Rubric dimensions (10):** git_forensic_analysis, state_management_rigor, graph_orchestration, safe_tool_engineering, structured_output_enforcement, judicial_nuance, chief_justice_synthesis, theoretical_depth, report_accuracy, swarm_visual. Each has target_artifact (github_repo | pdf_report | pdf_images), forensic_instruction, success_pattern, failure_pattern.
- **Context Builder:** Iterate through rubric `dimensions` array.
- **Dispatcher:** Send `forensic_instruction` to detectives where `target_artifact` matches capability (Code Detective ≠ grep PDF; Document Detective ≠ look for Pydantic in report text). Send `judicial_logic` to judges as part of persona-specific system prompt.
- **Chief Justice:** Provide `synthesis_rules` to ChiefJusticeNode so final verdict respects priority of facts over opinions.
- Rubric is loadable (e.g. rubric.json) so "Constitution" can be updated centrally without redeploying agent code.

---

## 7. Audit Report Structure (Output)

Markdown serialization of AuditReport:

1. **Executive Summary** — Overall verdict and aggregate score.
2. **Criterion Breakdown** — One section per rubric dimension (10 total): final score, three judge opinions with cited evidence, dissent summary when variance > 2, remediation.
3. **Remediation Plan** — Specific, file-level instructions grouped by criterion.

Report is a **file**, not console print. Structure: **Executive Summary → Criterion Breakdown → Remediation Plan**.

---

## 8. Tenx Evaluation Rubric (Outcome Quality)

| Metric | Score 1 | Score 3 | Score 5 |
|--------|---------|---------|---------|
| **Forensic Accuracy** | Hallucination; generic text; no file paths. | Basic verification; file existence; regex/simple parsing. | Deep AST; full git history; irrefutable evidence. |
| **Judicial Nuance** | Single grader; random/praise-only scores. | Prosecutor/Defense roles; synthesis = average or LLM. | Dialectical synthesis; deterministic verdict; explains overrule. |
| **LangGraph Architecture** | Linear script; hardcoded paths; no error handling. | Typed state; basic error handling; structured Judge output. | Parallel Detectives/Judges; reducers; strict typing. |
| **Feedback Loop** | Ignored peer feedback. | Fixed bugs; reflection doc. | MinMax: peer agent found flaws; own agent updated to detect those in others. |
| **Report Quality** | Unusable; no paths; "Good/Bad job." | Missing files + score; basic advice. | Executive-grade; remediation with "why"; professional format. |

---

## 9. Deliverable Locations and Submission Behavior

- **Self-audit report:** `audit/report_onself_generated/`.
- **Peer-audit report (this agent):** `audit/report_onpeer_generated/`.
- **Peer-audit report (received):** `audit/report_bypeer_received/`.

**Interim submission:** Repository with state.py, repo_tools, doc_tools, detectives (RepoInvestigator + DocAnalyst), graph (detectives parallel + EvidenceAggregator; Judges not required yet), pyproject.toml, .env.example, README (setup, install, run detective graph vs target repo URL), reports/interim_report.pdf. Same repo is peer-gradable.

**Final submission:** All of the above refined; plus judges.py, justice.py, full graph (detectives + judges parallel, conditional edges, repo URL input to Markdown report); README (run swarm vs any target repo URL and PDF); optional Dockerfile; audit dirs populated as above; reports/final_report.pdf. LangSmith trace link showing full loop (detectives → judges → Chief Justice). Video: run agent vs repo+PDF, show Evidence output, judges parallel opinions, ChiefJustice verdict, rendered Markdown report.

---

## 10. References

- **Master spec:** [spec.md](spec.md)
- **Technical implementation:** [technical-spec.md](technical-spec.md)
- **Phase specs:** [phase1-production-environment/](phase1-production-environment/spec.md), [phase2-detective-layer/](phase2-detective-layer/spec.md), [phase3-judicial-layer/](phase3-judicial-layer/spec.md), [phase4-supreme-court-and-feedback-loop/](phase4-supreme-court-and-feedback-loop/spec.md)
- **Challenge document:** `TRP1 Challenge Week 2_ The Automaton Auditor.md`
