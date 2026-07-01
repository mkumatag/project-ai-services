"""
Hello World service — sends a greeting prompt to the configured LLM and
displays the response in the browser.

Environment variables (same naming as the rest of the project):
  LLM_ENDPOINT   — base URL of the vLLM server  (e.g. http://vllm:8000)
  LLM_MODEL      — model name                   (e.g. meta-llama/Llama-3.1-8B-Instruct)
  LLM_API_KEY    — optional Bearer token
  PORT           — listening port (default 7000)
"""
import os
import logging
from contextlib import asynccontextmanager

import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)-18s - %(levelname)-8s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hello-world")

# ---------------------------------------------------------------------------
# Config (read once at startup)
# ---------------------------------------------------------------------------
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "").rstrip("/")
LLM_MODEL    = os.getenv("LLM_MODEL", "")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "256"))
TEMPERATURE  = float(os.getenv("TEMPERATURE", "0.7"))

# ---------------------------------------------------------------------------
# HTTP session (same pattern as common/misc_utils.py)
# ---------------------------------------------------------------------------
SESSION: requests.Session | None = None


def _build_session() -> requests.Session:
    from requests.adapters import HTTPAdapter
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=2, pool_maxsize=4, pool_block=False)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SESSION
    SESSION = _build_session()
    logger.info("Hello-world service starting  llm=%s  model=%s", LLM_ENDPOINT or "<not set>", LLM_MODEL or "<not set>")
    yield
    SESSION.close()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Hello World LLM Service", lifespan=lifespan)


def _call_llm(prompt: str) -> str:
    """Send *prompt* to the LLM and return the text reply."""
    if not LLM_ENDPOINT or not LLM_MODEL:
        return "[LLM_ENDPOINT or LLM_MODEL is not configured — set the env vars and restart]"

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": False,
    }

    try:
        resp = SESSION.post(f"{LLM_ENDPOINT}/v1/chat/completions", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return f"[LLM error: {exc}]"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Hello World — AI Services</title>
  <style>
    body{font-family:system-ui,sans-serif;max-width:680px;margin:60px auto;padding:0 20px;background:#f4f4f4;color:#161616}
    h1{font-size:1.6rem;margin-bottom:.5rem}
    p.sub{color:#525252;margin-bottom:1.5rem}
    label{display:block;font-weight:600;margin-bottom:.3rem}
    input[type=text]{width:100%;padding:.6rem .8rem;font-size:1rem;border:1px solid #8d8d8d;border-radius:4px;box-sizing:border-box}
    button{margin-top:.8rem;padding:.6rem 1.4rem;font-size:1rem;background:#0f62fe;color:#fff;border:none;border-radius:4px;cursor:pointer}
    button:disabled{background:#8d8d8d;cursor:not-allowed}
    #result{margin-top:1.5rem;background:#fff;border:1px solid #e0e0e0;border-radius:4px;padding:1rem 1.2rem;min-height:3rem;white-space:pre-wrap;line-height:1.6}
    .spinner{display:inline-block;width:16px;height:16px;border:3px solid #ccc;border-top-color:#0f62fe;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
</head>
<body>
  <h1>👋 Hello World — AI Services</h1>
  <p class="sub">Type anything below and the LLM will greet you back.</p>
  <label for="prompt">Your message</label>
  <input id="prompt" type="text" value="Say hello to me in a creative way!" autofocus/>
  <br/>
  <button id="btn" onclick="ask()">Ask the LLM</button>
  <div id="result"></div>

  <script>
    async function ask() {
      const prompt = document.getElementById('prompt').value.trim();
      if (!prompt) return;

      const btn = document.getElementById('btn');
      const result = document.getElementById('result');
      btn.disabled = true;
      result.innerHTML = '<span class="spinner"></span>Thinking…';

      try {
        const resp = await fetch('/hello', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({prompt})
        });
        const data = await resp.json();
        result.textContent = data.reply ?? data.error ?? JSON.stringify(data);
      } catch (err) {
        result.textContent = 'Request failed: ' + err;
      } finally {
        btn.disabled = false;
      }
    }

    // Allow Enter key to submit
    document.getElementById('prompt').addEventListener('keydown', e => {
      if (e.key === 'Enter') ask();
    });
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """Serve the browser UI."""
    return HTMLResponse(content=_HTML)


@app.post("/hello")
def hello(body: dict):
    """
    Accepts ``{"prompt": "..."}`` and returns ``{"reply": "..."}`` from the LLM.
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt must not be empty"}, status_code=400)

    logger.info("Received prompt: %s", prompt[:120])
    reply = _call_llm(prompt)
    logger.info("LLM reply: %s", reply[:120])
    return {"reply": reply}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
