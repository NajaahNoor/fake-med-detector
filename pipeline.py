"""
agents/pipeline.py
------------------
LangGraph-based multi-agent pipeline.

Graph nodes
-----------
1. intake      — parse user input → IntakeData
2. ocr         — if image_path present, run PP-OCRv5 → fill registration_number
3. verification — query DB + risk score → VerificationResult
4. router      — decide action → RouterOutput

State is a plain dict passed between nodes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Optional, Any

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from .intake_agent         import parse_input, IntakeData
from .verification_agent   import verify_drug, VerificationResult
from .router_agent         import route, RouterOutput
from complaint_drafter import draft_complaint


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------
class PipelineState(TypedDict, total=False):
    raw_input:           Any
    intake:              Optional[IntakeData]
    registration_number: Optional[str]
    ocr_raw_text:        Optional[str]
    ocr_confidence:      Optional[float]
    verification:        Optional[VerificationResult]
    output:              Optional[RouterOutput]
    errors:              list
    reporter:            str
    batch_no:            str


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------
def node_intake(state: PipelineState) -> PipelineState:
    intake = parse_input(state.get("raw_input", ""))
    state["intake"] = intake
    state["errors"] = intake.errors.copy()
    if intake.registration_number:
        state["registration_number"] = intake.registration_number
    return state


def node_ocr(state: PipelineState) -> PipelineState:
    intake = state.get("intake")
    if not intake or not intake.image_path:
        return state

    try:
        from .ocr_agent import extract_registration_number
        result = extract_registration_number(intake.image_path)
        state["ocr_raw_text"]   = result.raw_text
        state["ocr_confidence"] = result.confidence
        if result.registration_number:
            state["registration_number"] = result.registration_number
        else:
            state.setdefault("errors", []).append(
                "OCR could not extract a registration number from the image."
            )
    except Exception as e:
        state.setdefault("errors", []).append(f"OCR error: {e}")

    return state


def node_verification(state: PipelineState) -> PipelineState:
    reg_no = state.get("registration_number")
    if not reg_no:
        state.setdefault("errors", []).append(
            "Cannot verify: no registration number available."
        )
        return state

    intake           = state.get("intake")
    company_supplied = intake.company_name if intake else None
    result           = verify_drug(reg_no, supplied_company_name=company_supplied)
    state["verification"] = result
    return state


def node_router(state: PipelineState) -> PipelineState:
    verification = state.get("verification")
    if not verification:
        return state

    intake    = state.get("intake")
    drug_name = (intake.product_name or "") if intake else ""
    batch_no  = state.get("batch_no") or (intake.batch_number if intake else "") or ""
    reporter  = state.get("reporter", "")

    output = route(
        verification=verification,
        draft_complaint_fn=draft_complaint,
        drug_name=drug_name,
        batch_no=batch_no,
        reporter=reporter,
    )
    state["output"] = output
    return state


# ---------------------------------------------------------------------------
# Conditional edge: skip OCR if no image
# ---------------------------------------------------------------------------
def should_run_ocr(state: PipelineState) -> str:
    intake = state.get("intake")
    if intake and intake.image_path:
        return "ocr"
    return "verification"


# ---------------------------------------------------------------------------
# Build the LangGraph (with fallback for missing langgraph)
# ---------------------------------------------------------------------------
def build_graph():
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(PipelineState)
    graph.add_node("intake",       node_intake)
    graph.add_node("ocr",          node_ocr)
    graph.add_node("verification", node_verification)
    graph.add_node("router",       node_router)

    graph.set_entry_point("intake")
    graph.add_conditional_edges("intake", should_run_ocr, {
        "ocr":          "ocr",
        "verification": "verification",
    })
    graph.add_edge("ocr",          "verification")
    graph.add_edge("verification", "router")
    graph.add_edge("router",       END)

    return graph.compile()


_COMPILED_GRAPH = None


def get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph()
    return _COMPILED_GRAPH


# ---------------------------------------------------------------------------
# Public API — works with or without LangGraph
# ---------------------------------------------------------------------------
def run_pipeline(
    raw_input,
    reporter: str = "",
    batch_no: str = "",
) -> RouterOutput:
    """
    Run the full 4-agent pipeline on *raw_input*.

    Parameters
    ----------
    raw_input : str | dict
        Free text, dict with keys, or image file path.
    reporter  : str
        Name or organisation filing the complaint.
    batch_no  : str
        Batch / lot number of the drug under investigation.

    Returns
    -------
    RouterOutput
        .action             — "CLEAR" | "FLAG" | "COMPLAINT"
        .message            — human-readable verdict message (Markdown)
        .verification       — full VerificationResult
        .complaint_doc_path — path to .docx complaint, if drafted
    """
    state: PipelineState = {
        "raw_input": raw_input,
        "reporter":  reporter,
        "batch_no":  batch_no,
        "errors":    [],
    }

    graph = get_graph()
    if graph:
        final_state = graph.invoke(state)
    else:
        # Fallback: run nodes sequentially without LangGraph
        state = node_intake(state)
        state = node_ocr(state)
        state = node_verification(state)
        state = node_router(state)
        final_state = state

    output = final_state.get("output")
    if output is None:
        errors = final_state.get("errors", ["Unknown pipeline error."])
        dummy_vr = VerificationResult(
            registration_number=str(raw_input)[:20],
            score=0,
            verdict="Verified",
            reasons=errors,
        )
        output = RouterOutput("CLEAR", "\n".join(errors), dummy_vr)

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "134108"
    print(f"\n[pipeline] Running query: {query!r}\n")
    out = run_pipeline(query)
    print(out.message)
    if out.complaint_doc_path:
        print(f"\nComplaint draft saved to: {out.complaint_doc_path}")