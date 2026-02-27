"""
Pioneer AI client for GLiNER model inference.

Pioneer returns entities grouped by label:
  {"result": {"entities": {"company": ["BYD"], "location": ["Mexico"]}}}

This module normalises them into a flat list:
  [{"label": "company", "text": "BYD"}, {"label": "location", "text": "Mexico"}]
"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

PIONEER_API_URL = "https://api.pioneer.ai/inference"
PIONEER_API_KEY = os.getenv("PIONEER_API_KEY", "")

MAX_RETRIES = 3
RETRY_BACKOFF = 3
REQUEST_TIMEOUT = 60


def _flatten_entities(grouped: dict) -> list[dict]:
    """Convert Pioneer's grouped entity format into a flat list."""
    flat: list[dict] = []
    for label, texts in grouped.items():
        for text in texts:
            flat.append({"label": label, "text": text})
    return flat


def pioneer_extract(model_id: str, text: str, schema: list[str]) -> list[dict]:
    """
    Run entity extraction on Pioneer's GLiNER inference API with retries.

    Args:
        model_id: Pioneer Job ID (UUID) of the trained model
        text: Input text to extract entities from
        schema: List of entity type labels to extract

    Returns:
        Flat list of entity dicts with 'label' and 'text' keys.
        Returns empty list on failure after all retries.
    """
    payload = {
        "model_id": model_id,
        "task": "extract_entities",
        "text": text,
        "schema": schema,
    }
    headers = {
        "X-API-Key": PIONEER_API_KEY,
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                PIONEER_API_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code >= 500:
                body = response.text[:300]
                print(f"  ! Pioneer API {response.status_code} (attempt {attempt + 1}/{MAX_RETRIES}): {body}")
                last_error = response
                time.sleep(RETRY_BACKOFF * (2 ** attempt))
                continue

            if response.status_code >= 400:
                body = response.text[:300]
                print(f"  ! Pioneer API {response.status_code}: {body}")
                return []

            data = response.json()
            entities_grouped = data.get("result", {}).get("entities", {})
            return _flatten_entities(entities_grouped)

        except requests.exceptions.Timeout:
            print(f"  ! Pioneer timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            last_error = None
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
        except requests.exceptions.RequestException as e:
            print(f"  ! Pioneer request error: {e}")
            return []

    if last_error is not None:
        print(f"  ! Pioneer failed after {MAX_RETRIES} retries (last status: {last_error.status_code})")
    return []
