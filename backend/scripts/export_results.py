"""Export chart results to CSV/JSON."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console

from config.settings import get_settings

app = typer.Typer()
console = Console()


@app.command()
def export(
    chart_id: str = typer.Option(None, "--chart-id", "-c", help="Export specific chart"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json|csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export chart processing results."""
    settings = get_settings()
    output_dir = settings.paths.output_dir

    if chart_id:
        chart_dir = output_dir / chart_id
        if not chart_dir.exists():
            console.print(f"[red]No results for chart: {chart_id}[/red]")
            raise typer.Exit(1)

        # Load HCC pack
        hcc_pack = chart_dir / "8_payable_hcc_pack.json"
        if hcc_pack.exists():
            data = json.loads(hcc_pack.read_text(encoding="utf-8"))
        else:
            data = {}

        if output_format == "csv" and output_file:
            _export_hcc_csv(data, output_file)
        else:
            out = output_file or f"{chart_id}_export.json"
            Path(out).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        console.print(f"[green]Exported to {output_file or out}[/green]")
    else:
        console.print("[yellow]Specify --chart-id to export[/yellow]")


def _export_hcc_csv(data: dict, output_path: str) -> None:
    """Export HCC pack to CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["HCC Code", "Description", "RAF Weight", "ICD Codes", "Audit Risk"])
        for hcc in data.get("payable_hccs", []):
            icds = ", ".join(
                icd.get("icd10_code", "") for icd in hcc.get("supported_icds", [])
            )
            writer.writerow([
                hcc.get("hcc_code"),
                hcc.get("hcc_description"),
                hcc.get("raf_weight"),
                icds,
                hcc.get("audit_risk"),
            ])


if __name__ == "__main__":
    app()
