from paperfmt.core.normalize import parse_front_matter


def test_parse_front_matter_basic() -> None:
    text = """---\ntitle: Demo\nauthors:\n  - Alice\n---\n\n# Intro\n"""
    metadata, body = parse_front_matter(text)
    assert metadata["title"] == "Demo"
    assert "# Intro" in body
