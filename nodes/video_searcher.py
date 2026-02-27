"""
Video Searcher node — finds YouTube video URLs related to research topics using Tavily.
Limits: MAX_VIDEOS=5, MAX_VIDEOS_PER_TOPIC=2. Configurable via env vars.

No domain filtering is applied (matches the generic text searcher pattern).
YouTube URLs are extracted from any result via regex.
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


def video_searcher_node(state: GraphState) -> dict:
    print(f"--- SEARCHING VIDEOS (max {MAX_VIDEOS}) ---")
    topics = state.get("topics", [])
    candidate_videos = []

    for topic in topics:
        if len(candidate_videos) >= MAX_VIDEOS:
            break
        query = f"{topic} video YouTube"
        print(f"  -> Searching: {query}")
        try:
            response = tavily.search(query=query, search_depth="basic", max_results=5, topic="news")
            found = _extract_youtube_urls(response.get("results", []))
            candidate_videos.extend(found[:MAX_VIDEOS_PER_TOPIC])
            print(f"     Found: {len(found)} videos")
        except Exception as e:
            print(f"  ! Error searching videos for '{topic}': {e}")

    seen = set()
    unique_videos = []
    for v in candidate_videos:
        if v["url"] not in seen:
            seen.add(v["url"])
            unique_videos.append(v)

    final_videos = unique_videos[:MAX_VIDEOS]
    print(f"  -> Videos selected: {len(final_videos)}")
    for i, v in enumerate(final_videos, 1):
        print(f"     {i}. {v['title'][:60]}")

    return {"video_sources": final_videos}
