from __future__ import annotations

from pathlib import Path


def supported_templates() -> tuple[str, ...]:
    return ("ieee",)


def create_project_scaffold(template: str, output_dir: Path, force: bool = False) -> list[Path]:
    if template != "ieee":
        raise ValueError(f"Unsupported template: {template}")

    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        output_dir / "main.tex": _ieee_main_tex(),
        output_dir / "refs.bib": _ieee_refs_bib(),
    }

    created: list[Path] = []
    for path, content in files.items():
        if path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
        path.write_text(content, encoding="utf-8")
        created.append(path)

    return created


def _ieee_main_tex() -> str:
    return """\\documentclass[conference]{IEEEtran}
\\usepackage{graphicx}
\\usepackage{cite}

\\title{Paper Title}
\\author{Anonymous Author(s)}

\\begin{document}
\\maketitle

\\begin{abstract}
Write your abstract here.
\\end{abstract}

\\begin{IEEEkeywords}
keyword1, keyword2
\\end{IEEEkeywords}

\\section{Introduction}
Start writing your paper.

\\bibliographystyle{IEEEtran}
\\bibliography{refs}

\\end{document}
"""


def _ieee_refs_bib() -> str:
    return """@article{demo2026,
  author  = {Doe, Jane},
  title   = {A Demo Reference Entry},
  journal = {Demo Journal},
  year    = {2026},
  doi     = {10.0000/demo-doi}
}
"""