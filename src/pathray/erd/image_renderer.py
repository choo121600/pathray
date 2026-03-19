"""Mermaid ERD image renderer using mermaid-cli (mmdc)."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def render_images(
    mmd_path: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Path | None]:
    """Render a .mmd file to PNG and SVG using npx @mermaid-js/mermaid-cli.

    If Node.js / npx is not installed, logs a warning and returns None values
    for both outputs instead of raising an exception.

    Args:
        mmd_path: Path to the input .mmd file.
        output_dir: Directory for output files. Defaults to same dir as mmd_path.

    Returns:
        Dict with keys "png" and "svg" pointing to the generated file paths,
        or None for each if rendering was skipped.
    """
    mmd_path = Path(mmd_path)
    if output_dir is None:
        output_dir = mmd_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = mmd_path.stem
    png_path = output_dir / f"{stem}.png"
    svg_path = output_dir / f"{stem}.svg"

    results: dict[str, Path | None] = {"png": None, "svg": None}

    for fmt, out_path in (("png", png_path), ("svg", svg_path)):
        try:
            subprocess.run(
                [
                    "npx",
                    "--yes",
                    "@mermaid-js/mermaid-cli",
                    "-i",
                    str(mmd_path),
                    "-o",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            results[fmt] = out_path
        except FileNotFoundError:
            logger.warning(
                "npx not found — skipping ERD image rendering (%s). "
                "Install Node.js to enable image output.",
                fmt,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "mermaid-cli timed out for %s (120s limit).", fmt,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "mermaid-cli failed for %s (exit %d): %s",
                fmt,
                exc.returncode,
                exc.stderr,
            )

    return results
