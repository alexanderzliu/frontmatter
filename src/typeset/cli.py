"""Command-line interface for typeset."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from typeset.config.defaults import DEFAULT_CONFIG_YAML
from typeset.config.loader import find_config_file, load_config
from typeset.config.models import (
    EpubConfig,
    MetadataConfig,
    PdfConfig,
    StyleMapping,
    TypesetConfig,
)
from typeset.parser.docx_parser import DocxParser
from typeset.renderers.epub.renderer import EpubRenderer
from typeset.renderers.pdf.renderer import PdfRenderer

app = typer.Typer(
    name="typeset",
    help="Transform Word documents into print-ready PDFs and EPUBs.",
    add_completion=True,
)
console = Console()


@app.command()
def convert(
    input_file: Path = typer.Argument(
        ...,
        help="Input Word document (.docx)",
        exists=True,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: ./output)",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file (YAML)",
    ),
    format: str = typer.Option(
        "both",
        "--format",
        "-f",
        help="Output format: epub, pdf, or both",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Override book title",
    ),
    author: Optional[str] = typer.Option(
        None,
        "--author",
        "-a",
        help="Override book author",
    ),
) -> None:
    """
    Convert a Word document to EPUB and/or PDF.

    Examples:
        typeset convert manuscript.docx
        typeset convert book.docx -f epub -o ./dist
        typeset convert book.docx -c myconfig.yaml
    """
    # Validate format
    format = format.lower()
    if format not in ("epub", "pdf", "both"):
        console.print(f"[red]Invalid format: {format}. Use 'epub', 'pdf', or 'both'.[/red]")
        raise typer.Exit(1)

    # Load configuration
    cfg: TypesetConfig
    if config:
        if not config.exists():
            console.print(f"[red]Configuration file not found: {config}[/red]")
            raise typer.Exit(1)
        cfg = load_config(config)
    else:
        # Try to find config file automatically
        auto_config = find_config_file(Path.cwd())
        if auto_config:
            console.print(f"[dim]Using configuration: {auto_config}[/dim]")
            cfg = load_config(auto_config)
        else:
            cfg = TypesetConfig()

    # Override from CLI options
    if title:
        cfg.metadata.title = title
    if author:
        cfg.metadata.authors = [author]
    if output:
        cfg.output_dir = output

    # Ensure output directory exists
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename base
    output_base = cfg.metadata.title if cfg.metadata.title != "Untitled" else input_file.stem
    # Sanitize filename
    output_base = "".join(c for c in output_base if c.isalnum() or c in " -_").strip()
    if not output_base:
        output_base = input_file.stem

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Parse document
        task = progress.add_task("Parsing document...", total=None)
        try:
            parser = DocxParser(cfg.style_mapping)
            document = parser.parse(input_file)

            # Use parsed metadata title if not overridden
            if not title and document.metadata.title:
                output_base = document.metadata.title
                output_base = "".join(c for c in output_base if c.isalnum() or c in " -_").strip()

            # Merge config metadata with parsed metadata
            if not cfg.metadata.title or cfg.metadata.title == "Untitled":
                cfg.metadata.title = document.metadata.title
            if not cfg.metadata.authors:
                cfg.metadata.authors = document.metadata.authors

            # Update document metadata from config
            document.metadata.title = cfg.metadata.title
            document.metadata.authors = cfg.metadata.authors
            if cfg.metadata.publisher:
                document.metadata.publisher = cfg.metadata.publisher
            if cfg.metadata.isbn_print:
                document.metadata.isbn_print = cfg.metadata.isbn_print
            if cfg.metadata.isbn_epub:
                document.metadata.isbn_epub = cfg.metadata.isbn_epub
            if cfg.metadata.copyright:
                document.metadata.copyright = cfg.metadata.copyright

            progress.update(task, description="[green]Document parsed[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]Parse error: {e}[/red]")
            raise typer.Exit(1)

        # Generate EPUB
        if format in ("epub", "both"):
            task = progress.add_task("Generating EPUB...", total=None)
            try:
                epub_path = cfg.output_dir / f"{output_base}.epub"
                renderer = EpubRenderer(cfg.epub)
                renderer.render(document, epub_path)
                progress.update(task, description=f"[green]EPUB saved: {epub_path}[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]EPUB error: {e}[/red]")
                console.print_exception()
                if format == "epub":
                    raise typer.Exit(1)

        # Generate PDF
        if format in ("pdf", "both"):
            task = progress.add_task("Generating PDF...", total=None)
            try:
                pdf_path = cfg.output_dir / f"{output_base}.pdf"
                renderer = PdfRenderer(cfg.pdf)
                renderer.render(document, pdf_path)
                progress.update(task, description=f"[green]PDF saved: {pdf_path}[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]PDF error: {e}[/red]")
                console.print_exception()
                if format == "pdf":
                    raise typer.Exit(1)

    console.print()
    console.print("[bold green]Conversion complete![/bold green]")


@app.command()
def init(
    output: Path = typer.Option(
        Path("./typeset.yaml"),
        "--output",
        "-o",
        help="Output configuration file path",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
) -> None:
    """
    Initialize a new configuration file with defaults.
    """
    if output.exists() and not force:
        console.print(f"[yellow]File already exists: {output}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    output.write_text(DEFAULT_CONFIG_YAML)
    console.print(f"[green]Configuration file created: {output}[/green]")
    console.print()
    console.print("Edit this file to customize your book's metadata and formatting.")


@app.command()
def validate(
    config_path: Path = typer.Argument(
        ...,
        help="Configuration file to validate",
        exists=True,
    ),
) -> None:
    """
    Validate a configuration file.
    """
    try:
        cfg = load_config(config_path)
        console.print("[green]Configuration is valid![/green]")
        console.print()
        console.print(f"Title: {cfg.metadata.title}")
        console.print(f"Authors: {', '.join(cfg.metadata.authors) or 'Not specified'}")
        console.print(f"Page size: {cfg.pdf.page_size}")
        console.print(f"Output directory: {cfg.output_dir}")
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    input_file: Path = typer.Argument(
        ...,
        help="Input Word document (.docx)",
        exists=True,
        readable=True,
    ),
) -> None:
    """
    Show information about a Word document.
    """
    try:
        parser = DocxParser()
        document = parser.parse(input_file)

        console.print(f"[bold]Title:[/bold] {document.metadata.title}")
        console.print(f"[bold]Authors:[/bold] {', '.join(document.metadata.authors) or 'Not specified'}")
        console.print(f"[bold]Language:[/bold] {document.metadata.language}")
        console.print(f"[bold]Chapters:[/bold] {len(document.chapters)}")
        console.print(f"[bold]Word count:[/bold] ~{document.word_count():,}")
        console.print()

        if document.chapters:
            console.print("[bold]Chapter titles:[/bold]")
            for i, chapter in enumerate(document.chapters, 1):
                title = chapter.title or "(Untitled)"
                console.print(f"  {i}. {title}")

    except Exception as e:
        console.print(f"[red]Error reading document: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
