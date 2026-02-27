"""
Video Searcher node — finds YouTube video URLs related to research topics using Tavily.
Limits: MAX_VIDEOS=5, MAX_VIDEOS_PER_TOPIC=2. Configurable via env vars.

Search strategy:
  1. Query Tavily for each planner topic, restricted to youtube.com/youtu.be domains.
     Queries stay natural (no "video YouTube" suffix) — domain filtering does the targeting.
  2. If strategy 1 yields no videos, fall back to 3 broad queries built from the objective
     directly (objective, objective + highlights, objective + news).
"""
import os
import re

from dotenv import load_dotenv
from tavily import TavilyClient

from models import GraphState

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MAX_VIDEOS = int(os.getenv("MAX_VIDEOS", "5"))
MAX_VIDEOS_PER_TOPIC = int(os.getenv("MAX_VIDEOS_PER_TOPIC", "2"))

_YOUTUBE_DOMAINS = ["youtube.com", "youtu.be"]

YOUTUBE_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)'
)


def _extract_youtube_urls(results: list[dict]) -> list[dict]:
    videos = []
    seen = set()
    for result in results:
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")

        yt_match = YOUTUBE_PATTERN.search(url)
        if yt_match:
            clean_url = f"https://www.youtube.com/watch?v={yt_match.group(1)}"
            if clean_url not in seen:
                seen.add(clean_url)
                videos.append({"url": clean_url, "title": title, "snippet": content[:300], "source": "youtube"})
                continue

        for match in YOUTUBE_PATTERN.finditer(content):
            clean_url = f"https://www.youtube.com/watch?v={match.group(1)}"
            if clean_url not in seen:
                seen.add(clean_url)
                videos.append({"url": clean_url, "title": f"(embedded) {title}", "snippet": content[:300], "source": "embedded"})
    return videos


def _search_youtube(query: str) -> list[dict]:
    """Run a single Tavily search restricted to YouTube domains. Returns extracted video dicts."""
    try:
        response = tavily.search(
            query=query,
            search_depth="basic",
            max_results=5,
            topic="news",
            include_domains=_YOUTUBE_DOMAINS,
        )
        return _extract_youtube_urls(response.get("results", []))
    except Exception as e:
        print(f"  ! Error searching YouTube for '{query}': {e}")
        return []


def video_searcher_node(state: GraphState) -> dict:
    print(f"--- SEARCHING VIDEOS (max {MAX_VIDEOS}) ---")
    topics = state.get("topics", [])
    objective = state.get("objective", "")

    candidate_videos: list[dict] = []
    seen_urls: set[str] = set()

    def _add(videos: list[dict]) -> None:
        for v in videos:
            if v["url"] not in seen_urls and len(candidate_videos) < MAX_VIDEOS:
                seen_urls.add(v["url"])
                candidate_videos.append(v)

    # ------------------------------------------------------------------
    # Strategy 1: one Tavily call per planner topic, YouTube-domain only
    # ------------------------------------------------------------------
    for topic in topics:
        if len(candidate_videos) >= MAX_VIDEOS:
            break
        print(f"  -> Searching (topic): {topic}")
        found = _search_youtube(topic)
        _add(found[:MAX_VIDEOS_PER_TOPIC])
        print(f"     Found: {len(found)} video(s)")

    # ------------------------------------------------------------------
    # Strategy 2: fallback — broad queries from the objective itself
    # ------------------------------------------------------------------
    if not candidate_videos and objective:
        print(f"  -> No videos from topics, trying broad queries from objective…")
        broad_queries = [
            objective,
            f"{objective} highlights",
            f"{objective} news",
        ]
        for query in broad_queries:
            if len(candidate_videos) >= MAX_VIDEOS:
                break
            print(f"  -> Searching (broad): {query}")
            found = _search_youtube(query)
            _add(found[:MAX_VIDEOS_PER_TOPIC])
            print(f"     Found: {len(found)} video(s)")

    print(f"  -> Videos selected: {len(candidate_videos)}")
    for i, v in enumerate(candidate_videos, 1):
        print(f"     {i}. {v['title'][:60]}")

    return {"video_sources": candidate_videos}
