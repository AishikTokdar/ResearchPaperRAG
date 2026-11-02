import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ["GRADIO_SSR_MODE"] = "False"

try:
    import spaces
except ImportError:
    class _SpacesFallback:
        @staticmethod
        def GPU(*args, **kwargs):
            if args and callable(args[0]) and len(args) == 1 and not kwargs:
                return args[0]
            def decorator(func):
                return func
            return decorator
    spaces = _SpacesFallback()

import gradio as gr

try:
    from app.main import app as fastapi_app
except (ImportError, ModuleNotFoundError):
    from backend.app.main import app as fastapi_app

@spaces.GPU
def zerogpu_probe(value: str = "") -> str:
    return value or "ResearchPaperRAG backend is ready."


demo = gr.Interface(
    fn=zerogpu_probe,
    inputs=gr.Textbox(label="Status", value=""),
    outputs=gr.Textbox(label="Backend status"),
    title="ResearchPaperRAG Backend API",
    description="The REST API is available at /docs and /redoc.",
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/", ssr_mode=False)

if __name__ == "__main__":
    import uvicorn

    try:
        import spaces.zero as _spaces_zero
        _zero_startup = getattr(_spaces_zero, "startup", None)
        if callable(_zero_startup):
            _zero_startup()
            print("ZeroGPU startup registration complete.")
        else:
            print("ZeroGPU startup hook unavailable; continuing with Gradio mount.")
    except Exception as exc:
        print(f"ZeroGPU startup registration failed: {exc}")

    port = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 7860)))
    uvicorn.run(app, host="0.0.0.0", port=port)
