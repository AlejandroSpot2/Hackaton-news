"""
Visual Analyzer node — uploads videos to Reka Vision API, indexes them, runs Q&A.
"""
import os
import time

import requests
from dotenv import load_dotenv

from models import GraphState

load_dotenv()

REKA_API_KEY = os.getenv("REKA_API_KEY")
VISION_BASE_URL = "https://vision-agent.api.reka.ai"
INDEX_TIMEOUT_SECONDS = 300
INDEX_POLL_INTERVAL = 10


def _upload_video(url: str, name: str) -> str | None:
    headers = {"X-Api-Key": REKA_API_KEY}
    try:
        response = requests.post(
            f"{VISION_BASE_URL}/v1/videos/upload",
            headers=headers,
            data={"video_url": url, "video_name": name, "index": True},
            timeout=60,
        )
        response.raise_for_status()
        video_id = response.json().get("video_id")
        print(f"    Subido: {video_id}")
        return video_id
    except Exception as e:
        print(f"    ! Error subiendo video: {e}")
        return None


def _wait_for_indexing(video_id: str) -> bool:
    headers = {"X-Api-Key": REKA_API_KEY}
    elapsed = 0
    while elapsed < INDEX_TIMEOUT_SECONDS:
        try:
            resp = requests.get(f"{VISION_BASE_URL}/v1/videos/{video_id}", headers=headers, timeout=15)
            status = resp.json().get("indexing_status", "pending")
            if status == "indexed":
                print(f"    Indexado ✓")
                return True
            elif status == "failed":
                print(f"    ! Indexación falló")
                return False
            elapsed += INDEX_POLL_INTERVAL
            print(f"    Indexando... ({status}, {elapsed}s/{INDEX_TIMEOUT_SECONDS}s)", end="\r")
            time.sleep(INDEX_POLL_INTERVAL)
        except Exception as e:
            print(f"    ! Error verificando estado: {e}")
            return False
    print(f"    ! Timeout después de {INDEX_TIMEOUT_SECONDS}s")
    return False


def _qa_video(video_id: str, objective: str, topic: str) -> str:
    headers = {"X-Api-Key": REKA_API_KEY, "Content-Type": "application/json"}
    try:
        resp = requests.post(
            f"{VISION_BASE_URL}/v1/qa/chat",
            headers=headers,
            json={
                "video_id": video_id,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Contexto: Este video es sobre noticias relacionadas con: {topic}.\n"
                        f"Objetivo de la investigación: {objective}.\n\n"
                        "Analiza el video y proporciona:\n"
                        "1. Resumen del contenido principal\n"
                        "2. Datos clave: cifras, empresas, ubicaciones, fechas\n"
                        "3. Personas que aparecen y qué dicen\n"
                        "4. Conclusiones o tendencias relevantes\n\n"
                        "Responde en español, de forma concisa y estructurada."
                    ),
                }],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("chat_response", "")
    except Exception as e:
        print(f"    ! Error en Q&A: {e}")
        return ""


def _delete_video(video_id: str) -> None:
    try:
        requests.delete(f"{VISION_BASE_URL}/v1/videos/{video_id}", headers={"X-Api-Key": REKA_API_KEY}, timeout=10)
    except Exception:
        pass


def visual_analyzer_node(state: GraphState) -> dict:
    print("--- ANALIZANDO VIDEOS (REKA VISION) ---")
    video_sources = state.get("video_sources", [])
    objective = state.get("objective", "noticias México")

    if not video_sources:
        print("  -> No hay videos para analizar")
        return {"visual_analysis": []}

    total = len(video_sources)
    visual_analysis = []

    for i, video in enumerate(video_sources, 1):
        url = video["url"]
        title = video.get("title", f"video_{i}")
        topic = video.get("snippet", objective)[:200]

        print(f"\n  [{i}/{total}] {title[:60]}")
        print(f"    URL: {url}")

        video_id = _upload_video(url, f"news_{i}_{hash(url) % 100000}")
        if not video_id:
            continue

        if not _wait_for_indexing(video_id):
            _delete_video(video_id)
            continue

        print(f"    Analizando contenido...")
        analysis = _qa_video(video_id, objective, topic)

        if analysis:
            visual_analysis.append({
                "video_url": url,
                "video_title": title,
                "analysis": analysis,
                "source_topic": topic[:100],
            })
            print(f"    ✓ Análisis listo ({len(analysis)} chars)")
        else:
            print(f"    ! Análisis vacío")

        _delete_video(video_id)

    print(f"\n  => Videos analizados: {len(visual_analysis)}/{total}")
    return {"visual_analysis": visual_analysis}
