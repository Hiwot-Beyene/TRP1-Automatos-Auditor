# VisionInspector tool contract

**Detective:** VisionInspector (diagram / multimodal detective)  
**Target artifact:** Extracted images from PDF (`target_artifact: pdf_images`)

## Capabilities

| Function | Input | Output | Constraints |
|----------|--------|--------|-------------|
| extract_images_from_pdf | pdf_path: str | List of image bytes or paths | Implementation required; execution optional for interim |
| image_analysis | images from above | Classification + structural description | Vision model (e.g. Gemini Pro Vision / GPT-4o); optional at run time for interim |

## Evidence mapping (rubric dimensions)

- **swarm_visual:** Analyze diagrams: type (LangGraph State Machine, sequence diagram, flowchart); arrow flow (Detectives parallel → Evidence Aggregation → Judges parallel → Synthesis vs linear). Return Evidence with content = classification string and flow description.

## Error handling

- No images in PDF or extract fails: return Evidence with found=False.
- Vision call skipped (interim): return Evidence with found=False or placeholder rationale "Vision analysis not run (interim)."

## Contract summary

- **Inputs:** pdf_path from state.
- **Outputs:** List[Evidence] or updates to state.evidences for swarm_visual.
- **Interim:** Implement extract_images_from_pdf and node; vision call optional so graph runs without vision API.
