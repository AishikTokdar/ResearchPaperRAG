import inspect
import logging
import os
import sys
import time
import uuid
from collections.abc import AsyncGenerator

os.environ["GRADIO_SSR_MODE"] = "False"

import gradio as gr  # noqa: E402 - configure Gradio before import
import gradio_client.utils as _client_utils  # noqa: E402

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


@spaces.GPU
def zerogpu_probe() -> None:
    return None


_orig_js_to_py = getattr(_client_utils, "_json_schema_to_python_type", None)


def _safe_json_schema_to_python_type(schema, defs=None):
    if isinstance(schema, bool):
        return "dict"
    if _orig_js_to_py:
        return _orig_js_to_py(schema, defs)
    return "Any"


if _orig_js_to_py:
    _client_utils._json_schema_to_python_type = _safe_json_schema_to_python_type

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    from app.agents.base_agent import AgentResult
    from app.agents.pipeline import AgentPipeline
    from app.config import (
        AI_PROVIDERS,
        PROVIDER_PRIORITY,
        get_embedding_fallback_chain,
        get_settings,
        provider_has_credentials,
    )
    from app.services.llm_service import LLMService
    from app.services.pdf_processor import PDFProcessor
    from app.services.session_vector_registry import SessionVectorRegistry
    from app.services.usage_counters import (
        increment_chat_completions,
        increment_pdf_uploads,
        read_counters,
    )
except ModuleNotFoundError:
    from backend.app.agents.base_agent import AgentResult
    from backend.app.agents.pipeline import AgentPipeline
    from backend.app.config import (
        AI_PROVIDERS,
        PROVIDER_PRIORITY,
        get_embedding_fallback_chain,
        get_settings,
        provider_has_credentials,
    )
    from backend.app.services.llm_service import LLMService
    from backend.app.services.pdf_processor import PDFProcessor
    from backend.app.services.session_vector_registry import SessionVectorRegistry
    from backend.app.services.usage_counters import (
        increment_chat_completions,
        increment_pdf_uploads,
        read_counters,
    )

logger = logging.getLogger(__name__)

SERVER_BOOT_ID = str(uuid.uuid4())

settings = get_settings()
pdf_processor = PDFProcessor()
vector_registry = SessionVectorRegistry(settings.max_vector_sessions)
llm_service = LLMService()


def build_model_choices() -> list[str]:
    choices = [settings.default_model]
    for prov_name in PROVIDER_PRIORITY:
        provider = AI_PROVIDERS.get(prov_name)
        if provider:
            for model_id in provider.models:
                choices.append(model_id)
    return list(dict.fromkeys(choices))


ALL_MODEL_CHOICES = build_model_choices()


def ensure_session_id(session_id: str | None) -> str:
    from app.services.session_vector_registry import is_valid_session_id

    if not isinstance(session_id, str) or not is_valid_session_id(session_id):
        return str(uuid.uuid4())
    return session_id.strip()


def upload_pdf_files(
    files: list[str] | None,
    session_id: str | None = None,
) -> tuple[str, str, dict]:
    session_id = ensure_session_id(session_id)

    if not files:
        err_msg = "No PDF files provided. Please select at least one PDF file."
        return err_msg, session_id, {"status": "error", "message": "No files uploaded"}

    if len(files) > 3:
        err_msg = "Maximum 3 PDF document uploads allowed per session."
        return err_msg, session_id, {"status": "error", "message": err_msg}

    file_contents: list[tuple[str, bytes]] = []
    total_bytes = 0

    for file_item in files:
        file_path = (
            file_item if isinstance(file_item, str) else getattr(file_item, "name", str(file_item))
        )
        fname = os.path.basename(file_path)

        if not fname.lower().endswith(".pdf"):
            err_msg = f"File '{fname}' is not a valid PDF document."
            return err_msg, session_id, {"status": "error", "message": err_msg}

        try:
            with open(file_path, "rb") as f:
                remaining = settings.max_file_size - total_bytes
                if os.fstat(f.fileno()).st_size > remaining:
                    return "Combined PDFs exceed the upload limit.", session_id, {"status": "error", "message": "Upload limit exceeded"}
                data = f.read(remaining + 1)
        except Exception:
            err_msg = "Could not read the uploaded PDF. Please retry."
            return err_msg, session_id, {"status": "error", "message": err_msg}

        if len(data) > settings.max_file_size:
            err_msg = f"File '{fname}' exceeds the 50 MB size limit."
            return err_msg, session_id, {"status": "error", "message": err_msg}

        total_bytes += len(data)
        if total_bytes > settings.max_file_size:
            return "Combined PDFs exceed the upload limit.", session_id, {"status": "error", "message": "Upload limit exceeded"}
        if not data.startswith(b"%PDF-"):
            return "Uploaded file is not a PDF.", session_id, {"status": "error", "message": "Invalid PDF"}
        file_contents.append((fname, data))

    if total_bytes > settings.max_file_size:
        total_mb = round(total_bytes / (1024 * 1024), 2)
        err_msg = f"Combined size of uploaded PDFs ({total_mb} MB) exceeds the 50 MB limit."
        return err_msg, session_id, {"status": "error", "message": err_msg}

    all_chunks = []
    file_metas = []

    for fname, data in file_contents:
        try:
            res = pdf_processor.process_uploaded_file(data, fname)
            all_chunks.extend(res.chunks)
            file_metas.append(
                {
                    "file_name": fname,
                    "page_count": res.total_pages,
                    "chunks_created": res.total_chunks,
                }
            )
        except Exception:
            err_msg = "Unable to process the PDF. Check the file and retry."
            return err_msg, session_id, {"status": "error", "message": err_msg}

    try:
        vector_service = vector_registry.get_or_create(session_id)
        vector_service = vector_registry.activate(vector_service)
        vector_service.create_from_documents(all_chunks)
        increment_pdf_uploads()
    except Exception:
        err_msg = "Document indexing is unavailable. Please retry."
        return err_msg, session_id, {"status": "error", "message": err_msg}

    success_md = (
        f"### Document Processing Complete!\n"
        f"- **Files Processed**: {len(file_metas)}\n"
        f"- **Total Chunks Created**: `{len(all_chunks)}`\n"
        f"- **Session ID**: `{session_id}`\n\n"
        f"You can now switch to the **RAG Chat** tab and ask questions about your documents!"
    )

    result_meta = {
        "status": "success",
        "message": f"Successfully processed {len(file_metas)} document(s)",
        "chunks_created": len(all_chunks),
        "files": file_metas,
        "session_id": session_id,
    }

    return success_md, session_id, result_meta


def _history_pairs(history: list | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in history or []:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            pairs.append((str(item[0]), str(item[1])))
        elif isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    block.get("text", "") for block in content if isinstance(block, dict)
                )
            if item.get("role") == "user":
                pairs.append((str(content), ""))
            elif item.get("role") == "assistant" and pairs:
                pairs[-1] = (pairs[-1][0], str(content))
    return pairs


async def stream_chat_response(
    question: str,
    model: str,
    knowledge_mode: str,
    include_sources: bool,
    history: list,
    session_id: str | None = None,
) -> AsyncGenerator[tuple[list, str, str], None]:
    async for pairs, status, active_session in _stream_chat_response_pairs(
        question, model, knowledge_mode, include_sources, _history_pairs(history), session_id
    ):
        messages = [
            message
            for question_text, answer_text in pairs
            for message in (
                {"role": "user", "content": question_text},
                {"role": "assistant", "content": answer_text},
            )
        ]
        yield messages, status, active_session


async def _stream_chat_response_pairs(
    question: str,
    model: str,
    knowledge_mode: str,
    include_sources: bool,
    history: list[tuple[str, str]] | list[dict],
    session_id: str | None = None,
) -> AsyncGenerator[tuple[list, str, str], None]:
    session_id = ensure_session_id(session_id)
    q = (question or "").strip()

    if not q:
        yield history, "Please enter a question.", session_id
        return
    if len(q) > 2000 or model not in ALL_MODEL_CHOICES:
        yield history, "Use a supported model and a question of at most 2,000 characters.", session_id
        return

    vector_service = vector_registry.get_or_create(session_id)
    if not vector_service.is_ready:
        err_msg = "No PDF document loaded for this session. Please upload a PDF first in the PDF Upload tab."
        new_history = history + [(q, err_msg)] if isinstance(history, list) else history
        yield new_history, err_msg, session_id
        return

    hybrid_mode = "hybrid" in knowledge_mode.lower()

    if history is None:
        history = []

    current_history = list(history)
    current_history.append((q, ""))

    start_time = time.time()
    yield current_history, "Initializing 7-Stage Agent Pipeline...", session_id

    try:
        pipeline = AgentPipeline(vector_service, llm_service)
        context = {
            "question": q,
            "model": model,
            "include_sources": include_sources,
            "hybrid_mode": hybrid_mode,
            "retrieval_k": pipeline.retrieval_k,
        }
        results: list[AgentResult] = []
        total_ms = 0.0

        yield current_history, "[Stage 1/7 Extractor] Retrieving relevant PDF chunks...", session_id
        ok, chunks, ms, err = pipeline._step(pipeline.extractor, q, context, results)
        total_ms += ms
        if not ok:
            err_text = f"Extractor Agent error: {err}"
            current_history[-1] = (q, err_text)
            yield current_history, err_text, session_id
            return

        yield (
            current_history,
            "[Stage 2/7 Analyzer] Filtering duplicate and noisy chunks...",
            session_id,
        )
        ok, filtered, ms, err = pipeline._step(pipeline.analyzer, chunks, context, results)
        total_ms += ms
        if not ok:
            err_text = f"Analyzer Agent error: {err}"
            current_history[-1] = (q, err_text)
            yield current_history, err_text, session_id
            return

        yield current_history, "[Stage 3/7 Preprocessor] Normalizing document text...", session_id
        ok, cleaned, ms, err = pipeline._step(pipeline.preprocessor, filtered, context, results)
        total_ms += ms
        if not ok:
            err_text = f"Preprocessor Agent error: {err}"
            current_history[-1] = (q, err_text)
            yield current_history, err_text, session_id
            return

        yield (
            current_history,
            "[Stage 4/7 Optimizer] Trimming to optimal token budget...",
            session_id,
        )
        ok, (stream_q, opt_chunks), ms, err = pipeline._step(
            pipeline.optimizer, (q, cleaned), context, results
        )
        total_ms += ms
        if not ok:
            err_text = f"Optimizer Agent error: {err}"
            current_history[-1] = (q, err_text)
            yield current_history, err_text, session_id
            return

        yield (
            current_history,
            "[Stage 5/7 Synthesizer] Generating AI answer via streaming LLM...",
            session_id,
        )
        accumulated_answer = ""
        model_used = None
        completed = False

        async for event in llm_service.stream_answer_with_failover(
            question=stream_q,
            context_docs=opt_chunks,
            model=model,
            hybrid_mode=hybrid_mode,
        ):
            if event.get("type") == "token":
                accumulated_answer += event.get("content", "")
                current_history[-1] = (q, accumulated_answer)
                yield current_history, "Streaming response tokens...", session_id
            elif event.get("type") == "complete":
                accumulated_answer = event["answer"]
                completed = True
                model_used = event.get("model_used")

        if not completed:
            raise RuntimeError("The response was interrupted. Please retry.")
        context["model_used"] = model_used
        context["answer_length"] = len(accumulated_answer)

        yield current_history, "[Stage 6/7 Validator] Verification and quality check...", session_id
        ok, validated, ms, err = pipeline._step(
            pipeline.validator, accumulated_answer, context, results
        )
        total_ms += ms

        yield (
            current_history,
            "[Stage 7/7 Assembler] Formatting final citations and response...",
            session_id,
        )
        ok, assembled, ms, err = pipeline._step(pipeline.assembler, validated, context, results)
        total_ms += ms

        increment_chat_completions()

        final_answer = assembled.get("answer", accumulated_answer)
        sources = assembled.get("sources") or []

        if include_sources and sources:
            final_answer += "\n\n---\n**Source Citations:**\n"
            for i, src in enumerate(sources, 1):
                final_answer += f"{i}. {src}\n"

        elapsed_sec = (
            round(total_ms / 1000.0, 2) if total_ms > 0 else round(time.time() - start_time, 2)
        )
        model_name = assembled.get("model_used") or model_used or model
        final_status = f"Answer generated in {elapsed_sec}s using `{model_name}`"

        current_history[-1] = (q, final_answer)
        yield current_history, final_status, session_id

    except Exception:
        logger.exception("Error in Gradio chat stream handler")
        err_text = "The response could not be completed. Please retry."
        current_history[-1] = (q, err_text)
        yield current_history, err_text, session_id


def get_system_status(session_id: str | None = None) -> dict:
    session_id = ensure_session_id(session_id)
    vector_service = vector_registry.get_or_create(session_id)
    is_ready = vector_service.is_ready

    return {
        "status": "ready" if is_ready else "waiting",
        "message": "PDF loaded and ready for questions"
        if is_ready
        else "No PDF loaded. Please upload a PDF first.",
        "pdf_loaded": is_ready,
        "model": settings.default_model,
        "documents_loaded": 1 if is_ready else 0,
        "server_boot_id": SERVER_BOOT_ID,
        "session_id": session_id,
    }


def get_available_models_info() -> dict:
    models_list = []
    for prov_name, prov in AI_PROVIDERS.items():
        enabled = provider_has_credentials(prov)
        for m in prov.models:
            models_list.append(
                {
                    "id": m,
                    "name": m,
                    "provider": prov_name,
                    "is_default": m == settings.default_model,
                    "is_available": enabled,
                }
            )
    return {
        "models": models_list,
        "default_model": settings.default_model,
    }


def get_metrics_summary() -> dict:
    chain = get_embedding_fallback_chain()
    emb_names = {p.name for p, _ in chain}
    provider_rows = []

    for name, prov in AI_PROVIDERS.items():
        llm_ok = provider_has_credentials(prov)
        emb_ok = name in emb_names
        if llm_ok and emb_ok:
            st = "working"
        elif llm_ok or emb_ok:
            st = "partial"
        else:
            st = "unavailable"
        provider_rows.append(
            {
                "id": name,
                "display_name": name.replace("_", " ").title(),
                "llm_ready": llm_ok,
                "embedding_ready": emb_ok,
                "status": st,
            }
        )

    total_pdf, total_chats = read_counters()
    usable = sum(1 for r in provider_rows if r["status"] in ("working", "partial"))
    overall = "ok" if usable else "degraded"

    return {
        "status": overall,
        "providers_total": len(provider_rows),
        "working_providers": usable,
        "app_version": settings.app_version,
        "default_model": settings.default_model,
        "providers_detail": provider_rows,
        "pipeline_agents": 7,
        "embedding_chain_steps": len(chain),
        "total_pdf_uploads": total_pdf,
        "total_chat_completions": total_chats,
        "server_boot_id": SERVER_BOOT_ID,
    }


def create_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="ResearchPaperRAG Backend Engine") as demo:
        session_state = gr.State(lambda: ensure_session_id(None))

        with gr.Column(elem_classes=["main-header"]):
            gr.Markdown(
                """
                # ResearchPaperRAG AI Backend Engine
                **Enterprise Multi-Document PDF RAG Platform powered by 7-Agent Pipeline & Multi-Provider LLM Failover**
                """
            )
            gr.HTML(
                """
                <div class="badge-bar">
                    <span class="badge">7-Stage Agent Pipeline</span>
                    <span class="badge">FAISS Vector Search</span>
                    <span class="badge">5-Provider Failover</span>
                    <span class="badge">Hybrid Brain Knowledge</span>
                    <span class="badge">Hugging Face Spaces Ready</span>
                </div>
                """
            )

        with gr.Tabs():
            with gr.Tab("PDF Document Upload", id="tab_upload"):
                gr.Markdown(
                    """
                    ### Upload & Index PDF Documents
                    Upload up to **3 PDF documents** (cumulative size <= **50 MB**). The RAG pipeline extracts text, builds vector embeddings, and persists the FAISS index to session storage.
                    """
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        file_input = gr.File(
                            file_count="multiple",
                            file_types=[".pdf"],
                            label="Select PDF Files (Max 3 files, combined <= 50MB)",
                        )
                        upload_button = gr.Button(
                            "Upload & Build Vector Index", variant="primary", size="lg"
                        )

                    with gr.Column(scale=3):
                        upload_output_md = gr.Markdown("*Upload document files to get started...*")
                        upload_meta_json = gr.JSON(label="Processing & Document Metadata", value={})

                upload_button.click(
                    fn=upload_pdf_files,
                    inputs=[file_input, session_state],
                    outputs=[upload_output_md, session_state, upload_meta_json],
                    api_name="upload",
                    concurrency_id="rag-processing",
                    concurrency_limit=settings.max_concurrent_requests,
                )

            with gr.Tab("RAG Chat & Pipeline", id="tab_chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot_options = {
                            "height": 480,
                            "label": "ResearchPaperRAG 7-Agent Pipeline Response",
                        }
                        if "type" in inspect.signature(gr.Chatbot).parameters:
                            chatbot_options["type"] = "messages"
                        chatbot = gr.Chatbot(**chatbot_options, allow_tags=False)
                        status_text = gr.Markdown("*Ready for questions.*")

                        with gr.Row():
                            question_input = gr.Textbox(
                                placeholder="Ask a question about your uploaded PDF documents...",
                                label="Your Question",
                                lines=2,
                                scale=4,
                            )
                            submit_button = gr.Button("Submit", variant="primary", scale=1)

                        with gr.Row():
                            clear_button = gr.Button(
                                "Clear Chat History", variant="secondary", size="sm"
                            )

                    with gr.Column(scale=1):
                        gr.Markdown("### Generation Settings")
                        model_dropdown = gr.Dropdown(
                            choices=ALL_MODEL_CHOICES,
                            value=settings.default_model,
                            allow_custom_value=False,
                            label="Select AI Model",
                            info="Supports OpenRouter, Gemini, Groq & SambaNova free-tier models.",
                        )
                        knowledge_mode_radio = gr.Radio(
                            choices=[
                                "Hybrid Brain (PDF + Pretrained World Knowledge)",
                                "Strict to Source (PDF Document Only)",
                            ],
                            value="Strict to Source (PDF Document Only)",
                            label="Knowledge Retrieval Mode",
                            info="Hybrid synthesizes general AI knowledge with document facts.",
                        )
                        sources_checkbox = gr.Checkbox(
                            value=True,
                            label="Include Source Citations",
                            info="Show exact PDF source passages used for the answer.",
                        )

                        session_display = gr.Textbox(
                            label="Active Session ID",
                            interactive=False,
                            info="Isolated FAISS index container key",
                        )

                submit_event = submit_button.click(
                    fn=stream_chat_response,
                    inputs=[
                        question_input,
                        model_dropdown,
                        knowledge_mode_radio,
                        sources_checkbox,
                        chatbot,
                        session_state,
                    ],
                    outputs=[chatbot, status_text, session_state],
                    api_name="ask",
                    concurrency_id="rag-processing",
                    concurrency_limit=settings.max_concurrent_requests,
                )

                submit_event.then(lambda: "", outputs=[question_input])

                question_input.submit(
                    fn=stream_chat_response,
                    inputs=[
                        question_input,
                        model_dropdown,
                        knowledge_mode_radio,
                        sources_checkbox,
                        chatbot,
                        session_state,
                    ],
                    outputs=[chatbot, status_text, session_state],
                    concurrency_id="rag-processing",
                    concurrency_limit=settings.max_concurrent_requests,
                ).then(lambda: "", outputs=[question_input])

                clear_button.click(lambda: ([], "*Chat cleared.*"), outputs=[chatbot, status_text])

            with gr.Tab("System Status & Metrics", id="tab_metrics"):
                gr.Markdown("### System Operational Diagnostics & Provider Health")
                refresh_metrics_btn = gr.Button("Refresh System Metrics", variant="secondary")

                with gr.Row():
                    status_json_output = gr.JSON(label="Current Session Vector Index Status")
                    summary_json_output = gr.JSON(label="AI Provider Health & Metrics Summary")

                refresh_metrics_btn.click(
                    fn=get_system_status,
                    inputs=[session_state],
                    outputs=[status_json_output],
                    api_name="status",
                ).then(
                    fn=get_metrics_summary,
                    inputs=[],
                    outputs=[summary_json_output],
                    api_name="runtime_summary",
                )

        demo.load(
            fn=get_system_status,
            inputs=[session_state],
            outputs=[status_json_output],
        ).then(
            fn=get_metrics_summary,
            inputs=[],
            outputs=[summary_json_output],
        ).then(
            fn=ensure_session_id,
            inputs=[session_state],
            outputs=[session_display],
        ).then(
            fn=zerogpu_probe,
            inputs=[],
            outputs=[],
        )

        gr.Button("get_models_hidden", visible=False).click(
            fn=get_available_models_info,
            inputs=[],
            outputs=[summary_json_output],
            api_name="models",
        )

    demo.queue(max_size=16, default_concurrency_limit=settings.max_concurrent_requests)
    return demo


demo = create_gradio_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 7860)))
    demo.launch(server_name="0.0.0.0", server_port=port, ssr_mode=False, max_file_size=settings.max_file_size)
