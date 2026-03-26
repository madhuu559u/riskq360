r"""Self-contained LangExtract test -- PDF in, JSON out.

Takes a PDF medical chart, extracts text, chunks it, sends to GPT-4o
with the selected prompt pipeline(s), and writes structured JSON files.

Usage:
    cd C:\Next-Era\ClaudeProjects\medinsight360

    # Run ALL 5 pipelines on a PDF:
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf

    # Run only one pipeline:
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline sentences
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline risk_dx
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline demographics
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline hedis
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline encounters

    # Run multiple pipelines:
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --pipeline sentences risk_dx

    # Custom output directory:
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf -o my_output

    # Adjust chunk size or model:
    .\venv\Scripts\python.exe tests\test_langextract_live.py uploads\1_RET235214388.pdf --chunk-size 8000 --model gpt-4o-mini

Output:
    outputs/<pdf_stem>/
        sentences.json
        risk_diagnoses.json
        demographics.json
        hedis_evidence.json
        encounters.json
        _extraction_meta.json   (timing, token counts, chunk info)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Pipeline registry -- maps name -> (PipelineClass, output_filename)
# ---------------------------------------------------------------------------
PIPELINE_REGISTRY = {
    "sentences": {
        "module": "extraction.sentence_pipeline",
        "class": "SentencePipeline",
        "output_file": "sentences.json",
        "description": "Clinical sentence categorization with 22 categories + 6 negation statuses",
    },
    "risk_dx": {
        "module": "extraction.risk_dx_pipeline",
        "class": "RiskDxPipeline",
        "output_file": "risk_diagnoses.json",
        "description": "Risk adjustment diagnoses with ICD-10 codes, negation, MEAT evidence",
    },
    "demographics": {
        "module": "extraction.demographics_pipeline",
        "class": "DemographicsPipeline",
        "output_file": "demographics.json",
        "description": "Patient demographics (name, DOB, gender, MBI, vitals, allergies)",
    },
    "hedis": {
        "module": "extraction.hedis_pipeline",
        "class": "HEDISPipeline",
        "output_file": "hedis_evidence.json",
        "description": "HEDIS quality measure evidence (BP, A1C, screenings, labs)",
    },
    "encounters": {
        "module": "extraction.encounter_pipeline",
        "class": "EncounterPipeline",
        "output_file": "encounters.json",
        "description": "Encounter timeline (DOS, provider, CPTs, meds, referrals)",
    },
}

ALL_PIPELINE_NAMES = list(PIPELINE_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def print_header(title: str) -> None:
    width = 70
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def print_section(title: str) -> None:
    print(f"\n--- {title} ---")


def load_pipeline_class(name: str):
    """Dynamically import and return a pipeline class."""
    import importlib
    info = PIPELINE_REGISTRY[name]
    mod = importlib.import_module(info["module"])
    return getattr(mod, info["class"])


# ---------------------------------------------------------------------------
# Step 1: PDF -> Text
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract text from a PDF and return page-level + full text."""
    import fitz  # PyMuPDF

    from ingestion.quality_scorer import QualityScorer

    scorer = QualityScorer()
    doc = fitz.open(str(pdf_path))

    pages = []
    for i in range(len(doc)):
        raw_text = doc[i].get_text("text")
        quality = scorer.score(raw_text)
        pages.append({
            "page_number": i + 1,
            "text": raw_text,
            "chars": len(raw_text),
            "quality_score": round(quality, 1),
        })

    doc.close()

    full_text = "\n\n".join(p["text"] for p in pages)

    return {
        "full_text": full_text,
        "pages": pages,
        "page_count": len(pages),
        "total_chars": len(full_text),
        "file_name": pdf_path.name,
        "file_size_kb": round(pdf_path.stat().st_size / 1024, 1),
    }


# ---------------------------------------------------------------------------
# Step 2: Text -> Chunks
# ---------------------------------------------------------------------------
def chunk_document(full_text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into chunks for LLM processing."""
    from config.pipeline_config import ChunkingConfig
    from extraction.chunk_manager import chunk_text

    config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        split_on_paragraphs=True,
        min_chunk_size=200,
    )
    return chunk_text(full_text, config)


# ---------------------------------------------------------------------------
# Step 3: Run a single pipeline (chunk -> LLM -> merge)
# ---------------------------------------------------------------------------
async def run_pipeline(
    pipeline_name: str,
    full_text: str,
    llm_client: Any,
    run_config: Any,
) -> Dict[str, Any]:
    """Run one extraction pipeline on the full text. Returns merged JSON."""
    PipelineClass = load_pipeline_class(pipeline_name)
    pipeline = PipelineClass(llm_client, run_config)

    print(f"  Prompt      : config/prompts/{pipeline.prompt_file}")
    print(f"  Prompt len  : {len(pipeline.system_prompt):,} chars")
    print(f"  Sending to LLM...")

    t0 = time.time()
    result = await pipeline.run(full_text)
    elapsed = time.time() - t0

    print(f"  Done in {elapsed:.1f}s")
    return result


# ---------------------------------------------------------------------------
# Step 4: Print summaries per pipeline type
# ---------------------------------------------------------------------------
def summarize_sentences(result: Dict[str, Any]) -> None:
    sentences = result.get("sentences", [])
    print(f"  Total sentences: {len(sentences)}")

    # By category
    cats: Dict[str, int] = {}
    negs: Dict[str, int] = {}
    for s in sentences:
        cat = s.get("category", "?")
        neg = s.get("negation_status", "?")
        cats[cat] = cats.get(cat, 0) + 1
        negs[neg] = negs.get(neg, 0) + 1

    print("\n  By Category:")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:30s}: {n}")

    print("\n  By Negation Status:")
    for neg, n in sorted(negs.items(), key=lambda x: -x[1]):
        print(f"    {neg:20s}: {n}")

    # Show one sample per negation status
    print("\n  Samples:")
    shown = set()
    for s in sentences:
        neg = s.get("negation_status", "?")
        if neg not in shown:
            shown.add(neg)
            txt = s.get("text", "")[:100]
            print(f"    [{neg:15s}] [{s.get('category','?'):20s}] {txt}")


def summarize_risk_dx(result: Dict[str, Any]) -> None:
    diagnoses = result.get("diagnoses", [])
    print(f"  Total diagnoses: {len(diagnoses)}")

    status_map = {
        "active": "ACTIVE", "negated": "NEGATED", "historical": "HISTORICAL",
        "family_history": "FAMILY", "uncertain": "UNCERTAIN", "resolved": "RESOLVED",
    }
    for dx in diagnoses:
        code = dx.get("icd10_code", "???")
        desc = dx.get("description", "")
        neg = dx.get("negation_status", "?")
        section = dx.get("source_section", "?")
        marker = status_map.get(neg, neg)
        supp = (dx.get("supporting_text") or "")[:80]
        print(f"    [{marker:12s}] {code:10s} {desc}")
        if supp:
            print(f"{'':28s} evidence: {supp}")


def summarize_demographics(result: Dict[str, Any]) -> None:
    print(f"    Patient  : {result.get('patient_name', 'N/A')}")
    print(f"    DOB      : {result.get('date_of_birth', 'N/A')}")
    print(f"    Gender   : {result.get('gender', 'N/A')}")
    print(f"    Age      : {result.get('age', 'N/A')}")
    ids = result.get("member_ids", [])
    if ids:
        print(f"    MBI/IDs  : {', '.join(m.get('id','') for m in ids if m.get('id'))}")
    providers = result.get("providers", [])
    if providers:
        for p in providers[:5]:
            print(f"    Provider : {p.get('name','')} ({p.get('role','')})")
    vitals = result.get("vitals", [])
    if vitals:
        for v in vitals[:3]:
            bp = f"{v.get('bp_systolic','?')}/{v.get('bp_diastolic','?')}"
            print(f"    Vitals   : BP {bp}, weight {v.get('weight','?')}, BMI {v.get('bmi','?')} ({v.get('date','?')})")
    allergies = result.get("allergies", [])
    if allergies:
        print(f"    Allergies: {', '.join(str(a) for a in allergies[:5])}")
    family = result.get("family_history", [])
    if family:
        for fh in family[:5]:
            print(f"    Family Hx: {fh.get('relation','')} - {fh.get('condition','')}")


def summarize_hedis(result: Dict[str, Any]) -> None:
    bp = result.get("blood_pressure_readings", [])
    labs = result.get("lab_results", [])
    screens = result.get("screenings", [])
    conds = result.get("eligibility_conditions", [])
    meds = result.get("medications_for_measures", [])
    prev = result.get("preventive_care", [])
    depression = result.get("depression_screening", {})

    print(f"  BP readings       : {len(bp)}")
    for b in bp[:3]:
        print(f"    {b.get('date','?')}: {b.get('systolic','?')}/{b.get('diastolic','?')} ({b.get('location','?')})")
    print(f"  Lab results       : {len(labs)}")
    for l in labs[:5]:
        print(f"    {l.get('test_name','?')}: {l.get('result_value','?')} ({l.get('result_date','?')}) -> {l.get('hedis_measure','?')}")
    print(f"  Screenings        : {len(screens)}")
    for s in screens[:5]:
        print(f"    {s.get('screening_type','?')}: {s.get('result','?')} ({s.get('date','?')}) [{s.get('status','?')}]")
    print(f"  Conditions        : {len(conds)}")
    for c in conds[:5]:
        print(f"    {c.get('condition','?')}: present={c.get('is_present','?')}")
    print(f"  Medications       : {len(meds)}")
    print(f"  Preventive care   : {len(prev)}")
    if depression:
        print(f"  Depression PHQ-9  : {depression.get('phq9_score','N/A')}")


def summarize_encounters(result: Dict[str, Any]) -> None:
    encounters = result.get("encounters", [])
    print(f"  Total encounters: {len(encounters)}")
    for enc in encounters[:10]:
        date = enc.get("date", "?")
        provider = enc.get("provider", "?")
        etype = enc.get("encounter_type", "?")
        chief = (enc.get("chief_complaint") or "")[:60]
        dx_count = len(enc.get("diagnoses_this_visit", []))
        med_count = len(enc.get("medications", []))
        ref_count = len(enc.get("referrals", []))
        print(f"    {date} | {etype:12s} | {provider}")
        if chief:
            print(f"{'':6s}CC: {chief}")
        print(f"{'':6s}Dx: {dx_count}, Meds: {med_count}, Referrals: {ref_count}")


SUMMARIZERS = {
    "sentences": summarize_sentences,
    "risk_dx": summarize_risk_dx,
    "demographics": summarize_demographics,
    "hedis": summarize_hedis,
    "encounters": summarize_encounters,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(
        description="LangExtract: PDF -> LLM Extraction -> JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/test_langextract_live.py uploads/1_RET235214388.pdf
  python tests/test_langextract_live.py uploads/1_RET235214388.pdf --pipeline sentences
  python tests/test_langextract_live.py uploads/1_RET235214388.pdf --pipeline risk_dx sentences
  python tests/test_langextract_live.py uploads/1_RET235214388.pdf --chunk-size 8000
  python tests/test_langextract_live.py uploads/1_RET235214388.pdf --model gpt-4o-mini
        """,
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to a medical chart PDF file",
    )
    parser.add_argument(
        "--pipeline", "-p",
        nargs="+",
        choices=ALL_PIPELINE_NAMES,
        default=None,
        help="Which pipeline(s) to run. Default: all 5",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory (default: outputs/<pdf_stem>)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10000,
        help="Max chars per chunk (default: 10000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=500,
        help="Overlap chars between chunks (default: 500)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override LLM model (e.g. gpt-4o-mini)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Override LLM temperature",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=16384,
        help="Max output tokens for LLM (default: 16384)",
    )

    args = parser.parse_args()

    # Resolve PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.is_absolute():
        pdf_path = PROJECT_ROOT / pdf_path
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Resolve output dir
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / "outputs" / output_dir
    else:
        output_dir = PROJECT_ROOT / "outputs" / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # Pipelines to run
    pipelines_to_run = args.pipeline or ALL_PIPELINE_NAMES

    # =====================================================================
    # START
    # =====================================================================
    print_header("MedInsight 360 -- LangExtract")
    print(f"  PDF          : {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f} KB)")
    print(f"  Pipelines    : {', '.join(pipelines_to_run)}")
    print(f"  Output       : {output_dir}")
    print(f"  Chunk Size   : {args.chunk_size:,} chars")
    print(f"  Chunk Overlap: {args.chunk_overlap} chars")
    print(f"  Max Tokens   : {args.max_tokens:,}")

    total_start = time.time()

    # ── STEP 1: Extract text from PDF ────────────────────────────────
    print_section("Step 1: PDF Text Extraction")
    t0 = time.time()
    extraction = extract_text_from_pdf(pdf_path)
    t_extract = time.time() - t0

    full_text = extraction["full_text"]
    pages = extraction["pages"]
    print(f"  Pages        : {extraction['page_count']}")
    print(f"  Total chars  : {extraction['total_chars']:,}")
    print(f"  Time         : {t_extract:.2f}s")

    # Show per-page quality
    print(f"\n  Page Quality Scores:")
    for p in pages:
        bar = "#" * int(p["quality_score"] / 5)
        flag = " LOW" if p["quality_score"] < 60 else ""
        print(f"    Page {p['page_number']:3d}: {p['quality_score']:5.1f}  {bar}{flag}")

    # Save raw text
    raw_text_file = output_dir / "_raw_text.txt"
    raw_text_file.write_text(full_text, encoding="utf-8")
    print(f"\n  Saved raw text: {raw_text_file.name}")

    # ── STEP 2: Chunk the text ───────────────────────────────────────
    print_section("Step 2: Chunking")
    chunks = chunk_document(full_text, args.chunk_size, args.chunk_overlap)
    print(f"  Chunks       : {len(chunks)}")
    for i, chunk in enumerate(chunks):
        preview = chunk[:80].replace("\n", " ").strip()
        print(f"    Chunk {i}: {len(chunk):,} chars | {preview!r}...")

    # ── STEP 3: Init LLM Client ─────────────────────────────────────
    print_section("Step 3: LLM Client")
    from config.pipeline_config import PipelineRunConfig
    from config.settings import get_settings
    from extraction.llm_client import UnifiedLLMClient

    settings = get_settings()

    # Apply overrides
    settings.llm.llm_max_tokens = args.max_tokens
    if args.model:
        settings.llm.active_llm_model = args.model
    if args.temperature is not None:
        settings.llm.llm_temperature = args.temperature

    llm_client = UnifiedLLMClient(settings.llm)
    run_config = PipelineRunConfig(
        chunking__chunk_size=args.chunk_size,
        chunking__chunk_overlap=args.chunk_overlap,
    ) if False else PipelineRunConfig()  # use default, we already chunked in step 2
    # Update chunk config to match CLI args
    run_config.chunking.chunk_size = args.chunk_size
    run_config.chunking.chunk_overlap = args.chunk_overlap

    print(f"  Provider     : {llm_client.provider.value}")
    print(f"  Model        : {llm_client.model}")
    print(f"  Temperature  : {settings.llm.llm_temperature}")
    print(f"  Max Tokens   : {settings.llm.llm_max_tokens:,}")

    # ── STEP 4: Run selected pipelines ───────────────────────────────
    all_results: Dict[str, Dict[str, Any]] = {}
    pipeline_timings: Dict[str, float] = {}

    for pname in pipelines_to_run:
        info = PIPELINE_REGISTRY[pname]
        print_section(f"Pipeline: {pname} -- {info['description']}")

        t0 = time.time()
        result = await run_pipeline(pname, full_text, llm_client, run_config)
        elapsed = time.time() - t0
        pipeline_timings[pname] = elapsed
        all_results[pname] = result

        # Print summary
        summarizer = SUMMARIZERS.get(pname)
        if summarizer:
            print()
            summarizer(result)

        # Save JSON
        out_file = output_dir / info["output_file"]
        out_file.write_text(
            json.dumps(result, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n  -> Saved: {out_file.name}")

    # ── STEP 5: Save metadata ────────────────────────────────────────
    total_time = time.time() - total_start
    meta = {
        "pdf_file": pdf_path.name,
        "pdf_size_kb": extraction["file_size_kb"],
        "page_count": extraction["page_count"],
        "total_chars": extraction["total_chars"],
        "chunk_count": len(chunks),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "llm_provider": llm_client.provider.value,
        "llm_model": llm_client.model,
        "llm_temperature": settings.llm.llm_temperature,
        "llm_max_tokens": settings.llm.llm_max_tokens,
        "total_llm_calls": llm_client.total_calls,
        "total_tokens_used": llm_client.total_tokens,
        "pipelines_run": pipelines_to_run,
        "pipeline_timings": {k: round(v, 2) for k, v in pipeline_timings.items()},
        "total_time_seconds": round(total_time, 2),
        "page_quality_scores": [
            {"page": p["page_number"], "quality": p["quality_score"]}
            for p in pages
        ],
    }
    meta_file = output_dir / "_extraction_meta.json"
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ── Final Summary ────────────────────────────────────────────────
    print_header("Extraction Complete")
    print(f"  PDF            : {pdf_path.name}")
    print(f"  Pages          : {extraction['page_count']}")
    print(f"  Chunks         : {len(chunks)}")
    print(f"  LLM Calls      : {llm_client.total_calls}")
    print(f"  Tokens Used    : {llm_client.total_tokens:,}")
    print()
    for pname in pipelines_to_run:
        info = PIPELINE_REGISTRY[pname]
        t = pipeline_timings[pname]
        r = all_results[pname]
        # count main items
        count = "?"
        if pname == "sentences":
            count = str(len(r.get("sentences", [])))
        elif pname == "risk_dx":
            count = str(len(r.get("diagnoses", [])))
        elif pname == "demographics":
            count = r.get("patient_name") or "extracted"
        elif pname == "hedis":
            total = (len(r.get("blood_pressure_readings", []))
                     + len(r.get("lab_results", []))
                     + len(r.get("screenings", [])))
            count = f"{total} items"
        elif pname == "encounters":
            count = str(len(r.get("encounters", [])))
        print(f"  {pname:15s}: {count:>15s} | {t:5.1f}s | {info['output_file']}")

    print(f"\n  Total Time     : {total_time:.1f}s")
    print(f"  Output Dir     : {output_dir}")
    print(f"  Files created  :")
    for f in sorted(output_dir.iterdir()):
        if f.is_file():
            size = f.stat().st_size / 1024
            print(f"    {f.name:40s} {size:7.1f} KB")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
