"""
extract_pdf.py — convert a research-paper PDF into clean Markdown via Docling.

THE source-text stage of the paper pipeline (CLAUDE.md rule 5):
    FIND (Sonnet) -> ACQUIRE (fetch_papers.py) -> EXTRACT (this) -> DISSECT (Opus, reads .md)

Why Docling (not PyMuPDF / pymupdf4llm): our dissects live or die on Table-1 numbers
(e.g. Costa 66.78%, Osler order-flow coefficients, Chung logistic table). Docling's
TableFormer model preserves complex tables that PyMuPDF garbles. We do NOT use Nougat
(can hallucinate numbers) or native LLM vision on the raw PDF (banned — burns vision
tokens AND would land the whole paper in the orchestrator's main context).

HARD RULE this stage enforces: a paper is ALWAYS read as extracted Markdown, never as
the raw PDF. The DISSECT agent reads the .md this produces — it never opens the PDF.

Output: writes <pdf_stem>.md next to the PDF (gitignored — derivable from the PDF).
Idempotent: skips if the .md already exists unless --force.

Usage:
    python core/io/extract_pdf.py research/papers/b2b/osler_2003_...pdf
    python core/io/extract_pdf.py <pdf> --force      # re-extract
    python core/io/extract_pdf.py research/papers/b2b/   # whole folder
"""
from __future__ import annotations

import sys
from pathlib import Path


def _convert_one(pdf_path: Path, force: bool = False) -> Path | None:
    md_path = pdf_path.with_suffix(".md")
    if md_path.exists() and not force:
        print(f"[skip] {md_path.name} already exists (use --force to redo)")
        return md_path
    try:
        from docling.document_converter import DocumentConverter
    except ModuleNotFoundError:
        sys.exit(
            "ERROR: docling not installed. This is a research dependency.\n"
            "  pip install docling\n"
            "(first run also downloads the layout/table models, ~hundreds of MB)"
        )
    print(f"[docling] converting {pdf_path.name} ...")
    conv = DocumentConverter()
    result = conv.convert(str(pdf_path))
    md = result.document.export_to_markdown()
    md_path.write_text(md, encoding="utf-8")
    print(f"[ok] wrote {md_path}  ({len(md):,} chars)")
    return md_path


def main(argv: list[str]) -> None:
    args = [a for a in argv if a != "--force"]
    force = "--force" in argv
    if not args:
        sys.exit("usage: python core/io/extract_pdf.py <pdf-or-folder> [--force]")
    target = Path(args[0])
    if target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
        if not pdfs:
            sys.exit(f"no PDFs in {target}")
        for p in pdfs:
            _convert_one(p, force)
    elif target.is_file() and target.suffix.lower() == ".pdf":
        _convert_one(target, force)
    else:
        sys.exit(f"not a PDF or folder: {target}")


if __name__ == "__main__":
    main(sys.argv[1:])
