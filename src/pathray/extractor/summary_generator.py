"""Summary report generator for extracted page data."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pathray.models.page_data import PageData


def generate_summary(pages: list[PageData], output_path: str) -> dict:
    """Generate a summary report from extracted page data and save to JSON.

    Args:
        pages: List of extracted PageData objects.
        output_path: File path to write the summary JSON.

    Returns:
        Summary dict with counts and unique field/header names.
    """
    total_tables = sum(len(p.tables) for p in pages)
    total_forms = sum(len(p.forms) for p in pages)
    total_images = sum(len(p.meta.images) for p in pages)

    unique_field_names: set[str] = set()
    for page in pages:
        for form in page.forms:
            for field in form.fields:
                if field.name:
                    unique_field_names.add(field.name)

    unique_table_headers: set[str] = set()
    for page in pages:
        for table in page.tables:
            unique_table_headers.update(table.headers)

    summary = {
        "total_pages": len(pages),
        "total_tables": total_tables,
        "total_forms": total_forms,
        "total_images": total_images,
        "unique_form_fields": sorted(unique_field_names),
        "unique_table_headers": sorted(unique_table_headers),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))

    return summary


def print_summary(summary: dict) -> None:
    """Display summary report in terminal using Rich Table.

    Args:
        summary: Summary dict returned by generate_summary.
    """
    console = Console()

    counts_table = Table(title="Extraction Summary", show_header=True)
    counts_table.add_column("Metric", style="bold cyan")
    counts_table.add_column("Value", justify="right")

    counts_table.add_row("Total Pages", str(summary.get("total_pages", 0)))
    counts_table.add_row("Total Tables", str(summary.get("total_tables", 0)))
    counts_table.add_row("Total Forms", str(summary.get("total_forms", 0)))
    counts_table.add_row("Total Images", str(summary.get("total_images", 0)))
    counts_table.add_row(
        "Unique Form Fields",
        str(len(summary.get("unique_form_fields", []))),
    )
    counts_table.add_row(
        "Unique Table Headers",
        str(len(summary.get("unique_table_headers", []))),
    )

    console.print(counts_table)

    form_fields = summary.get("unique_form_fields", [])
    if form_fields:
        fields_table = Table(title="Unique Form Fields", show_header=False)
        fields_table.add_column("Field Name")
        for name in form_fields:
            fields_table.add_row(name)
        console.print(fields_table)

    table_headers = summary.get("unique_table_headers", [])
    if table_headers:
        headers_table = Table(title="Unique Table Headers", show_header=False)
        headers_table.add_column("Header")
        for header in table_headers:
            headers_table.add_row(header)
        console.print(headers_table)
