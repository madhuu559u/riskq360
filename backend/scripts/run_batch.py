"""CLI: Batch process multiple charts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console
from rich.progress import Progress

from config.settings import PipelineMode, get_settings
from core.orchestrator import Orchestrator

app = typer.Typer()
console = Console()


@app.command()
def batch(
    input_dir: str = typer.Option(..., "--input-dir", "-i", help="Directory containing PDF charts"),
    mode: str = typer.Option("full", "--mode", "-m", help="Pipeline mode"),
    max_concurrent: int = typer.Option(3, "--max-concurrent", help="Max charts to process in parallel"),
) -> None:
    """Batch process all PDF charts in a directory."""
    input_path = Path(input_dir)
    if not input_path.exists():
        console.print(f"[red]Directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    pdfs = list(input_path.glob("*.pdf"))
    if not pdfs:
        console.print(f"[yellow]No PDF files found in {input_dir}[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold blue]MedInsight 360 — Batch Processing[/bold blue]")
    console.print(f"  Charts found: {len(pdfs)}")
    console.print(f"  Mode: {mode}")
    console.print(f"  Concurrency: {max_concurrent}")

    pipeline_mode = PipelineMode(mode)

    async def process_all():
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_one(pdf: Path):
            async with semaphore:
                orch = Orchestrator(mode=pipeline_mode)
                return await orch.process_chart(pdf)

        tasks = [process_one(pdf) for pdf in pdfs]
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                console.print(f"  [green]✓[/green] {result.chart_id}: {result.status}")
            except Exception as e:
                console.print(f"  [red]✗[/red] Error: {e}")

        return results

    results = asyncio.run(process_all())

    completed = sum(1 for r in results if r.status == "completed")
    console.print(f"\n[bold]Done:[/bold] {completed}/{len(pdfs)} charts processed successfully.\n")


if __name__ == "__main__":
    app()
