# DocAnalyst tool contract

**Detective:** DocAnalyst (context / paperwork detective)  
**Target artifact:** PDF report (`target_artifact: pdf_report`)

## Capabilities

| Function | Input | Output | Constraints |
|----------|--------|--------|-------------|
| ingest_pdf | pdf_path: str | Chunked representation (e.g. list of text chunks + optional metadata) | PDF parse; chunking for RAG-lite; no requirement for full vector DB |
| cross_reference | file paths from report, repo evidence from state | Verified paths vs hallucinated paths | Compare paths mentioned in PDF to RepoInvestigator evidence; flag "Hallucination" when report cites non-existent file |

## Evidence mapping (rubric dimensions)

- **theoretical_depth:** Search chunks for "Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"; return Evidence with content = sentences and whether terms appear in detailed explanation vs buzzword-only.
- **report_accuracy:** Extract paths from report; cross_reference with repo evidence; return Evidence with verified_paths and hallucinated_paths (or found=False if hallucination detected).

## Error handling

- Missing or unreadable PDF: return Evidence with found=False, rationale with error.
- No chunks extracted: found=False.

## Contract summary

- **Inputs:** pdf_path from state; optional repo evidences from state for cross_reference.
- **Outputs:** List[Evidence] or updates to state.evidences keyed by dimension id.
- **RAG-lite:** Chunked ingest + query over chunks; full vector DB optional.
