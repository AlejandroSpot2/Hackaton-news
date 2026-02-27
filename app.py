"""
Newsloop — FastAPI web interface for the News Research Agent.

Run with: uvicorn app:app --reload
"""
import asyncio
import json
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel as PydanticModel

from agent import run_agent
from converter import to_markdown
from models import NewsDigest, ReportOutput


# =============================================================================
# In-memory state (single-process local demo)
# =============================================================================

_last_report: ReportOutput | None = None
_run_lock = asyncio.Lock()


# =============================================================================
# Bootstrap
# =============================================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    print("\nNewsloop running at http://localhost:8000\n")
    yield


app = FastAPI(title="Newsloop", lifespan=lifespan)

_TEMPLATE = Path(__file__).parent / "templates" / "index.html"


# =============================================================================
# UI
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_TEMPLATE.read_text(encoding="utf-8"))


# =============================================================================
# SSE helpers
# =============================================================================

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class RunRequest(PydanticModel):
    objective: str
    start_date: str
    end_date: str
    context: str = ""


# =============================================================================
# Agent streaming
# =============================================================================

async def _stream_agent(
    objective: str,
    start_date: str,
    end_date: str,
    context: str,
):
    """Runs the agent in a background thread and yields SSE events."""
    global _last_report

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str] = asyncio.Queue()

    class _Capture:
        """
        Replaces sys.stdout to intercept agent print() calls.
        Thread-safe: maintains a per-thread line buffer, forwards complete
        lines to the asyncio queue via call_soon_threadsafe.
        """

        def __init__(self, real_stdout):
            self._real = real_stdout
            self._bufs: dict[int, str] = {}
            self._lock = threading.Lock()

        def write(self, text: str) -> int:
            self._real.write(text)  # mirror to terminal so uvicorn logs still work
            tid = threading.get_ident()
            with self._lock:
                buf = self._bufs.get(tid, "") + text
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    stripped = line.strip()
                    if stripped:
                        loop.call_soon_threadsafe(queue.put_nowait, stripped)
                self._bufs[tid] = buf
            return len(text)

        def flush(self):
            self._real.flush()

    def _run():
        real_out = sys.stdout
        sys.stdout = _Capture(real_out)
        try:
            digest = run_agent(objective, start_date, end_date, context)
            if digest:
                sentinel = "__DONE__:" + digest.model_dump_json()
            else:
                sentinel = "__ERROR__:Agent produced no digest. Check your API keys and try again."
        except Exception as exc:
            sentinel = f"__ERROR__:{exc}"
        finally:
            sys.stdout = real_out
        loop.call_soon_threadsafe(queue.put_nowait, sentinel)

    threading.Thread(target=_run, daemon=True).start()

    # Drain the queue until done/error sentinel
    while True:
        try:
            line = await asyncio.wait_for(queue.get(), timeout=600.0)
        except asyncio.TimeoutError:
            yield _sse({"type": "error", "message": "Agent timed out after 10 minutes."})
            return

        if line.startswith("__DONE__:"):
            digest = NewsDigest.model_validate_json(line[9:])
            report = ReportOutput(
                generated_at=datetime.now().isoformat(),
                objective=objective,
                period_start=start_date,
                period_end=end_date,
                digest=digest,
            )
            _last_report = report
            yield _sse({"type": "done", "report": json.loads(report.model_dump_json())})
            return

        elif line.startswith("__ERROR__:"):
            yield _sse({"type": "error", "message": line[10:]})
            return

        else:
            yield _sse({"type": "log", "line": line})


@app.post("/run")
async def run(req: RunRequest):
    async def _guarded():
        if _run_lock.locked():
            yield _sse({
                "type": "error",
                "message": "A research run is already in progress. Please wait.",
            })
            return
        async with _run_lock:
            async for chunk in _stream_agent(
                req.objective, req.start_date, req.end_date, req.context
            ):
                yield chunk

    return StreamingResponse(
        _guarded(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Downloads
# =============================================================================

@app.get("/download/json")
async def download_json():
    if _last_report is None:
        return Response("No report available yet. Run a research session first.", status_code=404)
    name = f"newsloop_{_last_report.period_start}_{_last_report.period_end}.json"
    return Response(
        content=_last_report.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/download/md")
async def download_md():
    if _last_report is None:
        return Response("No report available yet. Run a research session first.", status_code=404)
    name = f"newsloop_{_last_report.period_start}_{_last_report.period_end}.md"
    return Response(
        content=to_markdown(_last_report),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
