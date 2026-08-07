import os

os.environ["GRADIO_SSR_MODE"] = "False"

import spaces
import gradio as gr
from app.main import app as fastapi_app

@spaces.GPU
def zerogpu_probe(value: str) -> str:
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
