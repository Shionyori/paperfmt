# paperfmt

paperfmt is a CLI-first academic paper formatter that orchestrates Pandoc and LaTeX.

MVP scope:
- Input: Markdown only
- Template: IEEE only
- Output: PDF (optional .tex and build log)
- Positioning: document compiler, not an editor or writing platform

## Quick Start

1. Install dependencies:

```bash
# Ubuntu example
sudo apt update
sudo apt install -y pandoc texlive-xetex texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra texlive-publishers lmodern fonts-noto-cjk
```

2. Install paperfmt:

```bash
pip install -e .
```

3. Build:

```bash
paperfmt build samples/paper.md --style ieee -o dist/paper.pdf
```

## Configuration

Create `paperfmt.yaml` in your project root:

```yaml
style: ieee
engine: xelatex
timeout_seconds: 30
output_dir: dist
keep_tex: false
keep_log: false
```

Priority: CLI flags > project `paperfmt.yaml` > `~/.config/paperfmt/defaults.yaml` > built-in defaults.

## CLI options

```bash
paperfmt build INPUT.md [--style ieee] [-o OUTPUT.pdf] [--config PATH] [--keep-tex] [--keep-log] [--timeout 30] [-v|-vv]
```

## Notes

- If `pandoc` is missing, paperfmt stops with an install hint.
- If `xelatex` is missing, paperfmt stops with an install hint.
- If LaTeX compile fails, paperfmt prints the trailing error excerpt.
