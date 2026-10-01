import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ["GRADIO_SSR_MODE"] = "False"

import gradio as gr

try:
    from app.main import app as fastapi_app
except (ImportError, ModuleNotFoundError):
    from backend.app.main import app as fastapi_app

def zerogpu_probe(value: str = "") -> str:
    return value or "ResearchPaperRAG backend is ready."


demo = gr.Interface(
    fn=zerogpu_probe,
    inputs=gr.Textbox(label="Status", value=""),
    outputs=gr.Textbox(label="Backend status"),
    title="ResearchPaperRAG Backend API",
    description="The REST API is available at /docs and /redoc.",
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio", ssr_mode=False)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 7860)))
    uvicorn.run(app, host="0.0.0.0", port=port)
