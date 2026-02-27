"""
Enricher node - extracts structured entities from article content using Pioneer AI.

Uses the fine-tuned GLiNER model (news-explorer-ner) to identify people,
organisations, locations, products, monetary figures, events, and dates
in every source article, adding an 'entities' dict to each source.
"""
import html
import os
import re

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from models import GraphState
from nodes.pioneer_client import pioneer_extract

load_dotenv()

ENRICHER_MODEL_ID = os.getenv(
    "PIONEER_ENRICHER_MODEL_ID",
    "a4888bce-85dc-4f2c-852f-97641cf71915",
)

ENRICHER_SCHEMA = [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "PRODUCT",
    "MONEY",
    "EVENT",
    "DATE",
]

_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_URL_RE = re.compile(r"https?://\S+")
_ANGLE_BRACKETS_RE = re.compile(r"[<>]")
_BRACKET_RE = re.compile(r"[\[\]()]")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def _sanitize_for_pioneer(text: str) -> str:
    """
    Aggressively strip HTML/JS/Markdown/URLs so Pioneer's WAF accepts the request.

    Tavily sometimes returns Markdown-formatted content (images, links,
    headings) which triggers Pioneer's WAF (especially ``![...]``).
    """
    text = BeautifulSoup(text, "lxml").get_text(separator=" ")
    text = html.unescape(text)
    text = _MD_IMAGE_RE.sub("", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _MD_HEADING_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _ANGLE_BRACKETS_RE.sub("", text)
    text = _BRACKET_RE.sub("", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def enrich_content_node(state: GraphState) -> dict:
    """
    Enrich extracted articles with structured entity data via Pioneer AI.

    For each source article in raw_content, runs Pioneer's GLiNER model
    to extract named entities and attaches them as metadata.

    Args:
        state: Current graph state containing raw_content with article text

    Returns:
        Dictionary with enriched raw_content (each source gains an 'entities' field)
    """
    print("--- ENRICHING WITH PIONEER AI ---")

    enriched_content = []
    total_entities = 0
    failed_sources = 0

    for topic_data in state.get("raw_content", []):
        for source in topic_data.get("sources", []):
            text = source.get("content", "")
            if not text or len(text) < 20:
                source["entities"] = {}
                continue

            clean = _sanitize_for_pioneer(text)
            truncated = clean[:4000]
            entities = pioneer_extract(ENRICHER_MODEL_ID, truncated, ENRICHER_SCHEMA)

            if not entities and len(clean) > 50:
                failed_sources += 1
                title = source.get("title", "unknown")[:80]
                print(f"  ! No entities for: {title}")

            grouped: dict[str, list[str]] = {}
            for entity in entities:
                label = entity.get("label", "OTHER")
                value = entity.get("text", "")
                if value:
                    grouped.setdefault(label, []).append(value)

            source["entities"] = grouped
            count = sum(len(v) for v in grouped.values())
            total_entities += count

        enriched_content.append(topic_data)

    print(f"  -> Extracted {total_entities} entities across all articles")
    if failed_sources:
        print(f"  -> {failed_sources} source(s) returned no entities (403 or empty)")

    return {"raw_content": enriched_content}
