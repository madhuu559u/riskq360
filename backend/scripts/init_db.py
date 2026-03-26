"""Create all database tables from SQLAlchemy models."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

console = Console()


def init_database() -> None:
    """Create all tables defined in database.models."""
    from database.connection import sync_engine
    from database.models import Base

    console.print("[bold blue]MedInsight 360 — Database Initialization[/bold blue]\n")

    try:
        console.print("Creating all tables...")
        Base.metadata.create_all(bind=sync_engine)
        console.print("[green]All tables created successfully![/green]\n")

        # List created tables
        for table_name in sorted(Base.metadata.tables.keys()):
            console.print(f"  [green]+[/green] {table_name}")

        console.print(f"\nTotal tables: {len(Base.metadata.tables)}")

    except Exception as e:
        console.print(f"[red]Database initialization failed: {e}[/red]")
        console.print("[dim]Make sure PostgreSQL is running and .env is configured.[/dim]")
        raise


if __name__ == "__main__":
    init_database()
