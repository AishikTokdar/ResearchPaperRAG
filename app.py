import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

import streamlit as st
import pandas as pd
from backend.app.services.paper_fetcher import PaperFetcher
from backend.app.services.gap_analyzer_engine import GapAnalyzerEngine

st.set_page_config(
    page_title="Research Gap Analyzer | RAG Assistant",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5 0%, #7B1FA2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .paper-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 4px solid #1E88E5;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
    .oa-badge {
        background-color: #2e7d32;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .non-oa-badge {
        background-color: #ed6c02;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

if "fetcher" not in st.session_state:
    st.session_state.fetcher = PaperFetcher()

if "analyzer" not in st.session_state:
    st.session_state.analyzer = GapAnalyzerEngine()

if "fetched_papers" not in st.session_state:
    st.session_state.fetched_papers = []

if "selected_paper_ids" not in st.session_state:
    st.session_state.selected_paper_ids = set()

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "gap_report" not in st.session_state:
    st.session_state.gap_report = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "search_topic" not in st.session_state:
    st.session_state.search_topic = ""

with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/research.png", width=64)
    st.title("Settings & LLM")
    
    provider = st.selectbox(
        "LLM Provider",
        options=["Gemini", "Groq", "Ollama (Local)", "OpenRouter"],
        index=0,
        help="Select local Ollama for offline use or a free API tier."
    )
    
    provider_key = provider.split(" ")[0].lower()
    
    model_name = ""
    api_key = ""
    
    if provider_key == "ollama":
        st.info("Local Ollama Mode: Make sure Ollama is running (`ollama serve`).")
        model_name = st.text_input("Ollama Model Name", value="mistral", help="e.g. mistral, llama3, phi3")
    elif provider_key == "groq":
        api_key = st.text_input("Groq API Key", value=os.getenv("GROQ_API_KEY", ""), type="password")
        model_name = st.selectbox("Groq Model", ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"])
    elif provider_key == "gemini":
        api_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""), type="password")
        model_name = st.selectbox("Gemini Model", ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"])
    elif provider_key == "openrouter":
        api_key = st.text_input("OpenRouter API Key", value=os.getenv("OPENROUTER_API_KEY", ""), type="password")
        model_name = st.text_input("OpenRouter Model", value="meta-llama/llama-3-8b-instruct:free")

    st.markdown("---")
    if st.button("Clear Session", use_container_width=True):
        st.session_state.fetched_papers = []
        st.session_state.selected_paper_ids = set()
        st.session_state.uploaded_files = []
        st.session_state.gap_report = None
        st.session_state.chat_history = []
        st.session_state.analyzer.initialize_session()
        st.success("Session cleared!")
        st.rerun()

    st.markdown("---")
    st.markdown("**Free Academic APIs Enabled:**")
    st.markdown("- Semantic Scholar API\n- arXiv API\n- OpenAlex API")

st.markdown('<div class="main-header">Research Gap Analyzer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Automated Academic Paper Retrieval, Multi-Paper RAG Synthesis & Research Gap Analysis</div>',
    unsafe_allow_html=True
)

tab_search, tab_upload = st.tabs(["Search by Topic", "Upload Custom PDFs"])

with tab_search:
    st.subheader("Topic-based Paper Retrieval")
    col_input, col_limit, col_btn = st.columns([4, 1.5, 1.5])
    
    with col_input:
        topic_query = st.text_input(
            "Research Topic or Question",
            value=st.session_state.search_topic or "Plant disease detection using deep learning in Indian agriculture",
            placeholder="Enter research topic (e.g. Retrieval-Augmented Generation for educational chatbots)",
        )
    with col_limit:
        limit_count = st.slider("Papers per API", min_value=2, max_value=5, value=3)
    with col_btn:
        st.write("")
        st.write("")
        search_pressed = st.button("Fetch Papers", use_container_width=True, type="primary")

    if search_pressed and topic_query.strip():
        st.session_state.search_topic = topic_query.strip()
        with st.spinner(f"Fetching papers for '{topic_query}' from Semantic Scholar, arXiv, and OpenAlex..."):
            papers = st.session_state.fetcher.search_all(query=topic_query, limit_per_source=limit_count)
            st.session_state.fetched_papers = papers
            st.session_state.selected_paper_ids = set([p["id"] for p in papers[:5]])
            if papers:
                st.success(f"Retrieved {len(papers)} papers!")
            else:
                st.warning("No papers found matching the query. Try broadening your keywords.")

    if st.session_state.fetched_papers:
        st.markdown("### Fetched Papers")
        st.caption("Select papers to include in the multi-paper RAG analysis:")
        
        col_all, col_none = st.columns([1, 1])
        with col_all:
            if st.button("Select All"):
                st.session_state.selected_paper_ids = set([p["id"] for p in st.session_state.fetched_papers])
                st.rerun()
        with col_none:
            if st.button("Deselect All"):
                st.session_state.selected_paper_ids = set()
                st.rerun()

        for paper in st.session_state.fetched_papers:
            pid = paper["id"]
            is_selected = pid in st.session_state.selected_paper_ids
            
            with st.container():
                col_check, col_details = st.columns([0.5, 9.5])
                with col_check:
                    checked = st.checkbox("", value=is_selected, key=f"check_{pid}")
                    if checked and pid not in st.session_state.selected_paper_ids:
                        st.session_state.selected_paper_ids.add(pid)
                    elif not checked and pid in st.session_state.selected_paper_ids:
                        st.session_state.selected_paper_ids.remove(pid)
                
                with col_details:
                    oa_tag = '<span class="oa-badge">Open Access PDF</span>' if paper.get("is_open_access") else '<span class="non-oa-badge">Abstract Only</span>'
                    st.markdown(
                        f"**{paper['title']}** ({paper['year']}) &nbsp; {oa_tag} &nbsp; *[{paper['source_api']}]*",
                        unsafe_allow_html=True
                    )
                    st.caption(f"Authors: {paper['authors']} | Citations: {paper.get('citations', 0)}")
                    with st.expander("View Abstract & Metadata"):
                        st.write(paper["abstract"])
                        if paper.get("url"):
                            st.markdown(f"[Paper Link]({paper['url']})")

with tab_upload:
    st.subheader("Upload Local PDF Research Papers")
    uploaded = st.file_uploader(
        "Upload one or multiple PDF papers",
        type=["pdf"],
        accept_multiple_files=True,
        help="PDFs uploaded here will be processed alongside fetched papers."
    )
    if uploaded:
        st.session_state.uploaded_files = uploaded
        st.success(f"{len(uploaded)} PDF file(s) attached!")
        for pdf in uploaded:
            st.markdown(f"- **{pdf.name}** ({round(pdf.size / 1024, 1)} KB)")

st.markdown("---")
selected_fetched = [p for p in st.session_state.fetched_papers if p["id"] in st.session_state.selected_paper_ids]
total_active = len(selected_fetched) + len(st.session_state.uploaded_files)

col_kb_info, col_analyze_btn = st.columns([6, 4])
with col_kb_info:
    st.markdown(f"### Active Knowledge Base: **{total_active} Papers**")
    st.write(f"- Selected Auto-Fetched Papers: **{len(selected_fetched)}**")
    st.write(f"- Custom Uploaded PDFs: **{len(st.session_state.uploaded_files)}**")

with col_analyze_btn:
    st.write("")
    run_analysis = st.button("Run Multi-Paper Gap Analysis", type="primary", use_container_width=True, disabled=(total_active == 0))

if run_analysis:
    st.session_state.chat_history = []
    if total_active == 0:
        st.error("Please select or upload at least one paper before running analysis.")
    else:
        progress_text = "Processing papers: Extracting text, chunking, and embedding into Chroma..."
        my_bar = st.progress(0, text=progress_text)
        
        fetched_with_text = []
        for i, paper in enumerate(selected_fetched):
            my_bar.progress(int((i + 1) / (total_active + 1) * 50), text=f"Processing paper {i+1}/{len(selected_fetched)}: {paper['title'][:40]}...")
            text = st.session_state.fetcher.download_and_extract_text(paper)
            fetched_with_text.append((paper, text))

        uploaded_bytes_list = []
        if st.session_state.uploaded_files:
            for uf in st.session_state.uploaded_files:
                uploaded_bytes_list.append((uf.name, uf.getvalue()))

        my_bar.progress(75, text="Generating SentenceTransformers embeddings & indexing in Chroma...")
        num_chunks = st.session_state.analyzer.process_and_index_papers(
            fetched_papers_with_text=fetched_with_text,
            uploaded_pdf_files=uploaded_bytes_list
        )

        my_bar.progress(90, text=f"Running RAG synthesis using {provider}...")
        topic_for_report = st.session_state.search_topic or "Multi-Paper Research Literature Review"
        report = st.session_state.analyzer.generate_gap_report(
            topic=topic_for_report,
            provider=provider_key,
            model_name=model_name,
            api_key=api_key,
        )
        st.session_state.gap_report = report
        my_bar.progress(100, text="Analysis Complete!")
        st.success(f"Multi-paper analysis generated successfully! Created {num_chunks} vector chunks.")

if st.session_state.gap_report:
    st.markdown("---")
    st.markdown("## Structured Research Gap Report")
    
    st.download_button(
        label="Download Structured Report (.md)",
        data=st.session_state.gap_report,
        file_name="research_gap_report.md",
        mime="text/markdown",
    )
    
    st.markdown(st.session_state.gap_report)

    st.markdown("---")
    st.markdown("## Interactive Grounded Follow-up Chat")
    st.caption("Ask questions about the research gaps, limitations, or specific findings. Answers are strictly grounded in the indexed papers with source citations.")

    for q, a in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.write(a)

    user_query = st.chat_input("Ask a follow-up question (e.g. Which gap is best suited for a student project?)")
    if user_query:
        with st.chat_message("user"):
            st.write(user_query)
        
        with st.chat_message("assistant"):
            with st.spinner("Searching indexed papers and formulating grounded answer..."):
                ans = st.session_state.analyzer.ask_followup(
                    question=user_query,
                    provider=provider_key,
                    model_name=model_name,
                    api_key=api_key
                )
                st.write(ans)
                st.session_state.chat_history.append((user_query, ans))
