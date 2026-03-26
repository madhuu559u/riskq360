"""CLI: Process a single medical chart through the MedInsight 360 pipeline.

Usage:
    python scripts/run_chart.py --chart-path "/path/to/chart.pdf"
    python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode risk_only
    python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode hedis_only
    python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode hcc_pack
    python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --llm-provider azure --enable-ml true
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console
from rich.table import Table

from config.settings import PipelineMode
from core.orchestrator import Orchestrator

app = typer.Typer(name="medinsight360", help="MedInsight 360 CLI")
console = Console()


@app.command()
def process(
    chart_path: str = typer.Option(..., "--chart-path", "-c", help="Path to the PDF chart"),
    mode: str = typer.Option("full", "--mode", "-m", help="Pipeline mode: full|risk_only|hedis_only|hcc_pack"),
    llm_provider: str = typer.Option(None, "--llm-provider", help="LLM provider: openai|azure|gemini"),
    enable_ml: bool = typer.Option(None, "--enable-ml", help="Enable ML predictions"),
    enable_ocr: bool = typer.Option(None, "--enable-ocr", help="Enable OCR fallback"),
    tfidf_threshold: float = typer.Option(None, "--tfidf-threshold", help="TF-IDF similarity threshold"),
    measurement_year: int = typer.Option(None, "--measurement-year", help="HEDIS measurement year"),
) -> None:
    """Process a medical chart through the full MedInsight 360 pipeline."""
    chart_file = Path(chart_path)
    if not chart_file.exists():
        console.print(f"[red]Error: Chart file not found: {chart_path}[/red]")
        raise typer.Exit(1)

    # Parse mode
    try:
        pipeline_mode = PipelineMode(mode)
    except ValueError:
        console.print(f"[red]Invalid mode: {mode}. Use: full, risk_only, hedis_only, hcc_pack[/red]")
        raise typer.Exit(1)

    # Build overrides
    overrides = {}
    if enable_ml is not None:
        overrides["enable_ml"] = enable_ml
    if enable_ocr is not None:
        overrides["enable_ocr"] = enable_ocr
    if tfidf_threshold is not None:
        overrides["tfidf_threshold"] = tfidf_threshold
    if measurement_year is not None:
        overrides["measurement_year"] = measurement_year

    console.print(f"\n[bold blue]MedInsight 360[/bold blue] — Processing chart")
    console.print(f"  Chart: {chart_path}")
    console.print(f"  Mode:  {pipeline_mode.value}")
    if overrides:
        console.print(f"  Overrides: {overrides}")
    console.print()

    # Run pipeline
    orchestrator = Orchestrator(mode=pipeline_mode, config_overrides=overrides)

    try:
        result = asyncio.run(orchestrator.process_chart(chart_file))
    except Exception as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        raise typer.Exit(1)

    # Display results
    console.print(f"\n[green]Pipeline completed![/green]")
    console.print(f"  Status:  {result.status}")
    console.print(f"  Run ID:  {result.run_id}")

    if result.completed_at and result.started_at:
        elapsed = (result.completed_at - result.started_at).total_seconds()
        console.print(f"  Time:    {elapsed:.1f}s")

    # Extraction Summary
    meta = result.meta
    summary = result.summary
    if meta:
        console.print(f"\n[bold]Extraction:[/bold]")
        console.print(f"  Pages:      {meta.get('page_count', 0)}")
        console.print(f"  Assertions: {meta.get('assertions_total_audited', 0)} (raw: {meta.get('assertions_total_raw', 0)}, drops: {meta.get('drops_total', 0)})")
        console.print(f"  Model:      {meta.get('model', '')}")

    if summary:
        dx_count = len(summary.get("unique_diagnoses", []))
        icd_count = len(summary.get("icd10cm_codes_found", []))
        console.print(f"  Diagnoses:  {dx_count} unique active")
        console.print(f"  ICD-10 codes: {icd_count}")

    # RAF Summary
    raf = result.raf_summary
    if raf:
        console.print(f"\n[bold]HCC / RAF:[/bold]")
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total RAF Score", str(raf.get("total_raf_score", 0)))
        table.add_row("Demographic RAF", str(raf.get("demographic_raf", 0)))
        table.add_row("HCC RAF", str(raf.get("hcc_raf", 0)))
        table.add_row("Payable HCCs", str(raf.get("payable_hcc_count", 0)))
        table.add_row("Suppressed HCCs", str(raf.get("suppressed_hcc_count", 0)))
        console.print(table)

    # HEDIS Summary
    hedis = result.hedis_result
    if hedis and hedis.get("summary"):
        hs = hedis["summary"]
        console.print(f"\n[bold]HEDIS:[/bold]")
        console.print(f"  Measures: {hs.get('total_measures', 0)}")
        console.print(f"  Met:      {hs.get('met', 0)}")
        console.print(f"  Gap:      {hs.get('gap', 0)}")
        console.print(f"  N/A:      {hs.get('not_applicable', 0)}")

    # Output location
    from config.settings import get_settings
    output_dir = get_settings().paths.output_dir / result.chart_id
    console.print(f"\n[dim]Outputs saved to: {output_dir}[/dim]\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
