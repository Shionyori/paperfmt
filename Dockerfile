FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pandoc \
       texlive-xetex \
       texlive-latex-recommended \
       texlive-fonts-recommended \
       texlive-latex-extra \
       texlive-publishers \
       texlive-lang-chinese \
       lmodern \
       fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY paperfmt ./paperfmt

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["paperfmt"]
