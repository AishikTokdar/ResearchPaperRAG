import os
import re
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

import warnings

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from langchain_huggingface import HuggingFaceEmbeddings
except (ImportError, ModuleNotFoundError):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_chroma import Chroma
    HAS_CHROMA = True
except ImportError:
    try:
        from langchain_community.vectorstores import Chroma
        HAS_CHROMA = True
    except ImportError:
        HAS_CHROMA = False

from langchain_community.vectorstores import FAISS

from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama

from ..config import AI_PROVIDERS, PROVIDER_PRIORITY, get_all_provider_api_keys
from .model_health import (
    is_auth_or_invalid_key_error,
    record_failure,
    record_invalid_key_failure,
    record_success,
)


class GapAnalyzerEngine:
    def __init__(self, embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model_name = embedding_model_name
        self._embeddings = None
        self.vector_store = None
        self.documents: List[Document] = []
        self.paper_metadata_list: List[Dict[str, Any]] = []

    @property
    def embeddings(self):
        if self._embeddings is None:
            try:
                hf_token = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
                if hf_token and "HF_TOKEN" not in os.environ:
                    os.environ["HF_TOKEN"] = hf_token
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self._embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            except Exception as e:
                raise e
        return self._embeddings

    def initialize_session(self):
        self.vector_store = None
        self.documents = []
        self.paper_metadata_list = []

    def process_and_index_papers(
        self,
        fetched_papers_with_text: List[Tuple[Dict[str, Any], str]],
        uploaded_pdf_files: List[Tuple[str, bytes]] = None
    ) -> int:
        self.initialize_session()
        all_docs: List[Document] = []

        capped_fetched = fetched_papers_with_text[:5]
        for paper, full_text in capped_fetched:
            self.paper_metadata_list.append(paper)
            title = paper.get("title", "Untitled Paper")
            authors = paper.get("authors", "Unknown")
            year = paper.get("year", "N/A")
            source_url = paper.get("url") or paper.get("pdf_url") or paper.get("source_api") or "API Search"

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            raw_doc = Document(
                page_content=full_text,
                metadata={
                    "paper_title": title,
                    "authors": authors,
                    "year": year,
                    "source": source_url,
                    "type": "fetched",
                }
            )
            chunks = text_splitter.split_documents([raw_doc])
            for i, chunk in enumerate(chunks):
                chunk.metadata["section"] = "Main Text"
            all_docs.extend(chunks)

        if uploaded_pdf_files and len(capped_fetched) < 5:
            remaining_slots = 5 - len(capped_fetched)
            capped_uploads = uploaded_pdf_files[:remaining_slots]
            for filename, file_bytes in capped_uploads:
                title = filename.rsplit(".", 1)[0]
                paper_meta = {
                    "id": f"upload_{filename}",
                    "source_api": "User Uploaded PDF",
                    "title": title,
                    "authors": "Uploaded Document",
                    "year": "N/A",
                    "url": filename,
                    "is_open_access": True,
                }
                self.paper_metadata_list.append(paper_meta)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                try:
                    loader = PyPDFLoader(tmp_path)
                    pdf_docs = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    for doc in pdf_docs:
                        page_num = doc.metadata.get("page", 0) + 1
                        doc.metadata.update({
                            "paper_title": title,
                            "authors": "Uploaded Document",
                            "year": "N/A",
                            "source": filename,
                            "section": f"Page {page_num}",
                            "type": "uploaded",
                        })
                    pdf_chunks = text_splitter.split_documents(pdf_docs)
                    all_docs.extend(pdf_chunks)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

        self.documents = all_docs

        if not all_docs:
            return 0

        try:
            if HAS_CHROMA:
                self.vector_store = Chroma.from_documents(
                    documents=all_docs,
                    embedding=self.embeddings,
                )
            else:
                self.vector_store = FAISS.from_documents(
                    documents=all_docs,
                    embedding=self.embeddings,
                )
        except Exception:
            self.vector_store = FAISS.from_documents(
                documents=all_docs,
                embedding=self.embeddings,
            )

        return len(all_docs)

    def _get_all_fallback_candidates(
        self, provider: str, model_name: str
    ) -> List[Tuple[str, str]]:
        candidates: List[Tuple[str, str]] = []
        seen = set()

        def add(p: str, m: str):
            if not p or not m:
                return
            key = (p.lower(), m.lower())
            if key not in seen:
                seen.add(key)
                candidates.append((p, m))

        if provider and model_name:
            add(provider, model_name)
            p_clean = provider.lower()
            if p_clean in AI_PROVIDERS:
                for m in AI_PROVIDERS[p_clean].models:
                    add(provider, m)

        for prov_name in PROVIDER_PRIORITY:
            prov = AI_PROVIDERS.get(prov_name)
            if prov:
                for m in prov.models:
                    add(prov.name, m)

        for prov_name, prov in AI_PROVIDERS.items():
            for m in prov.models:
                add(prov.name, m)

        return candidates

    def _get_llm_with_key(
        self, provider: str = "gemini", model_name: str = "gemini-3.6-flash", api_key: Optional[str] = None
    ) -> ChatOpenAI:
        provider = provider.lower() if provider else "gemini"
        
        if provider == "groq":
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key or "placeholder",
                model=model_name or "llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "openrouter":
            return ChatOpenAI(
                base_url=os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
                api_key=api_key or "placeholder",
                model=model_name or "meta-llama/llama-3.3-70b-instruct:free",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "cerebras":
            return ChatOpenAI(
                base_url="https://api.cerebras.ai/v1",
                api_key=api_key or "placeholder",
                model=model_name or "llama3.3-70b",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "sambanova":
            return ChatOpenAI(
                base_url="https://api.sambanova.ai/v1",
                api_key=api_key or "placeholder",
                model=model_name or "Meta-Llama-3.3-70B-Instruct",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "huggingface":
            return ChatOpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=api_key or "placeholder",
                model=model_name or "meta-llama/Meta-Llama-3-8B-Instruct",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "ollama":
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return ChatOpenAI(
                base_url=f"{ollama_url}/v1",
                api_key="ollama",
                model=model_name or "mistral",
                temperature=0.2,
                max_tokens=8192,
            )
        else:
            key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            return ChatOpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=key or "placeholder",
                model=model_name or "gemini-3.6-flash",
                temperature=0.2,
                max_tokens=8192,
            )

    def _get_llms_to_try(
        self, provider: str = "gemini", model_name: str = "gemini-3.6-flash", api_key: Optional[str] = None
    ) -> List[ChatOpenAI]:
        provider = provider.lower() if provider else "gemini"
        keys = get_all_provider_api_keys(provider, api_key)
        if keys:
            return [
                self._get_llm_with_key(provider=provider, model_name=model_name, api_key=k)
                for k in keys
            ]
        return [self._get_llm_with_key(provider=provider, model_name=model_name, api_key=api_key)]

    def _get_balanced_documents(self, query: str, top_k_per_paper: int = 3, max_total_docs: int = 15) -> List[Document]:
        if not self.vector_store and not self.documents:
            return []

        candidate_docs: List[Document] = []
        if self.vector_store:
            try:
                candidate_docs = self.vector_store.similarity_search(query, k=30)
            except Exception:
                candidate_docs = list(self.documents[:30])
        else:
            candidate_docs = list(self.documents[:30])

        paper_docs_map: Dict[str, List[Document]] = {}
        for d in candidate_docs:
            p_title = d.metadata.get("paper_title") or d.metadata.get("source") or "Unknown Paper"
            if p_title not in paper_docs_map:
                paper_docs_map[p_title] = []
            paper_docs_map[p_title].append(d)

        for p in self.paper_metadata_list:
            title = p.get("title")
            if title and (title not in paper_docs_map or len(paper_docs_map[title]) == 0):
                matching = [d for d in self.documents if d.metadata.get("paper_title") == title]
                if matching:
                    paper_docs_map[title] = matching[:top_k_per_paper]

        balanced_docs: List[Document] = []
        paper_titles = list(paper_docs_map.keys())

        for i in range(top_k_per_paper):
            for p_title in paper_titles:
                docs_for_title = paper_docs_map[p_title]
                if i < len(docs_for_title):
                    balanced_docs.append(docs_for_title[i])
                    if len(balanced_docs) >= max_total_docs:
                        break
            if len(balanced_docs) >= max_total_docs:
                break

        return balanced_docs if balanced_docs else candidate_docs[:max_total_docs]

    def _get_llm(self, provider: str = "gemini", model_name: str = "gemini-3.6-flash", api_key: Optional[str] = None):
        return self._get_llm_with_key(provider=provider, model_name=model_name, api_key=api_key)

    def _try_single_generation(
        self,
        topic: str,
        provider: str,
        model_name: str,
        api_key: Optional[str]
    ) -> Optional[str]:
        llms = self._get_llms_to_try(provider=provider, model_name=model_name, api_key=api_key)
        last_err = None

        for llm in llms:
            try:
                retrieved_docs = self._get_balanced_documents(
                    f"Research gaps trends methods limitations contradictions for {topic}",
                    top_k_per_paper=3,
                    max_total_docs=15
                )

                formatted_context_items = []
                for d in retrieved_docs:
                    paper_title = d.metadata.get("paper_title", "Unknown")
                    section = d.metadata.get("section", "Section N/A")
                    year = d.metadata.get("year", "")
                    url = d.metadata.get("source", "") or d.metadata.get("url", "")
                    formatted_context_items.append(
                        f"[Paper: {paper_title} ({year}) | URL: {url} | Section: {section}]\n{d.page_content.strip()[:500]}"
                    )
                formatted_context = "\n\n".join(formatted_context_items)

                system_prompt = """You are an expert academic research assistant.
Analyze the provided research papers context for the topic: "{topic}".

Generate a comprehensive, professional Markdown research report formatted strictly into these 8 section headers:

# Research Analysis & Gap Report: {topic}

## 1. Literature Summary
Provide a clear, high-level synthesis summarizing the core objectives, findings, and contributions of the analyzed papers.

## 2. Trend Detection
Identify emerging technological, architectural, or domain trends evident in recent publications (2024-2026).

## 3. Common Methods
Detail the key methodologies, algorithms, models, datasets, and experimental frameworks adopted across the papers.

## 4. Limitations
Identify recurring methodological weaknesses, dataset constraints, evaluation bottlenecks, or scalability issues.

## 5. Contradictions
Highlight any conflicting findings, opposing conclusions, or divergent experimental results between studies.

## 6. Research Gaps
Detail specific unaddressed research gaps, missing benchmark evaluations, or unexplored application areas.

## 7. Future Directions
Outline strategic open problems and recommended research avenues for future academic work.

## 8. Novel Paper Suggestions
Propose 2 to 3 novel, concrete, and actionable student or researcher paper project concepts that directly address the identified gaps.

RULES:
- Maintain a clean, academic tone. Do NOT include any emojis or casual symbols.
- EVERY research paper citation in sections 1-7 MUST be formatted as a hyperlinked Markdown title: `[Paper Title, Year](URL)`. Use the exact URL provided in the paper source context.
- Example citation: `[Attention Is All You Need, 2024](https://arxiv.org/abs/1706.03762)`.
- Clicking the paper name must open the original research paper link in a new tab.
- Provide concrete technical details rather than vague generalities.

---
RETRIEVED MULTI-PAPER CONTEXT:
{context}
"""

                prompt = ChatPromptTemplate.from_template(system_prompt)
                chain = prompt | llm | StrOutputParser()
                report = chain.invoke({"topic": topic, "context": formatted_context})

                for p in self.paper_metadata_list:
                    title = p.get("title", "").strip()
                    url = p.get("url") or p.get("pdf_url") or ""
                    if title and url and len(title) > 4:
                        escaped_title = re.escape(title)
                        pattern_bracket = rf'\[({escaped_title}[^\]]*)\](?!\()'
                        report = re.sub(pattern_bracket, rf'[\1]({url})', report)

                record_success(provider, model_name)
                return report
            except Exception as err:
                if is_auth_or_invalid_key_error(err):
                    record_invalid_key_failure(provider, model_name)
                else:
                    record_failure(model_name)
                last_err = err
                continue

        return f"Error: {str(last_err)}"


    def _generate_split_gap_report(
        self,
        topic: str,
        provider: str = "groq",
        model_name: str = "openai/gpt-oss-120b",
        api_key: Optional[str] = None
    ) -> str:
        llms = self._get_llms_to_try(provider=provider, model_name=model_name, api_key=api_key)
        last_err = None

        for llm in llms:
            try:
                retrieved_docs = self._get_balanced_documents(
                    f"Research literature trends methods limitations contradictions {topic}",
                    top_k_per_paper=3,
                    max_total_docs=15
                )

                formatted_context_items = []
                for d in retrieved_docs:
                    paper_title = d.metadata.get("paper_title", "Unknown")
                    section = d.metadata.get("section", "Section N/A")
                    year = d.metadata.get("year", "")
                    url = d.metadata.get("source", "") or d.metadata.get("url", "")
                    formatted_context_items.append(
                        f"[Paper: {paper_title} ({year}) | URL: {url} | Section: {section}]\n{d.page_content.strip()[:400]}"
                    )
                compact_context = "\n\n".join(formatted_context_items)

                batch_1_prompt = """You are an academic research assistant.
Analyze the provided paper context for topic: "{topic}".
Generate Part 1 of the research report covering strictly these 4 sections:

## 1. Literature Summary
Provide a clear, high-level synthesis summarizing core objectives and contributions of analyzed papers.

## 2. Trend Detection
Identify emerging technological, architectural, or domain trends in recent publications (2024-2026).

## 3. Common Methods
Detail key methodologies, algorithms, models, datasets, and experimental frameworks.

## 4. Limitations
Identify recurring methodological weaknesses, dataset constraints, or evaluation bottlenecks.

RULES:
- Clean academic tone. No emojis or casual symbols.
- Format citations as `[Paper Title, Year](URL)` using the exact URL in the context.

CONTEXT:
{context}
"""

                batch_2_prompt = """You are an academic research assistant.
Analyze the provided paper context for topic: "{topic}".
Generate Part 2 of the research report covering strictly these 4 sections:

## 5. Contradictions
Highlight any conflicting findings, opposing conclusions, or divergent experimental results between studies.

## 6. Research Gaps
Detail specific unaddressed research gaps, missing benchmark evaluations, or unexplored application areas.

## 7. Future Directions
Outline strategic open problems and recommended research avenues for future academic work.

## 8. Novel Paper Suggestions
Propose 2 to 3 novel, concrete, and actionable student/researcher paper project concepts.

RULES:
- Clean academic tone. No emojis or casual symbols.
- Format citations as `[Paper Title, Year](URL)` using the exact URL in the context.

CONTEXT:
{context}
"""

                p1_chain = ChatPromptTemplate.from_template(batch_1_prompt) | llm | StrOutputParser()
                p2_chain = ChatPromptTemplate.from_template(batch_2_prompt) | llm | StrOutputParser()

                part1 = p1_chain.invoke({"topic": topic, "context": compact_context})
                part2 = p2_chain.invoke({"topic": topic, "context": compact_context})

                notice = "> [NOTICE] Large context detected. Prompt was automatically split into 2 focused generation batches (Sections 1-4 and Sections 5-8) to bypass API token limit constraints.\n\n"
                full_report = f"# Research Analysis & Gap Report: {topic}\n\n{notice}{part1.strip()}\n\n{part2.strip()}"

                for p in self.paper_metadata_list:
                    title = p.get("title", "").strip()
                    url = p.get("url") or p.get("pdf_url") or ""
                    if title and url and len(title) > 4:
                        escaped_title = re.escape(title)
                        pattern_bracket = rf'\[({escaped_title}[^\]]*)\](?!\()'
                        full_report = re.sub(pattern_bracket, rf'[\1]({url})', full_report)

                return full_report
            except Exception as err:
                last_err = err
                continue

        return f"Error: {str(last_err)}"

    def generate_gap_report(
        self,
        topic: str,
        provider: str = "gemini",
        model_name: str = "gemini-3.6-flash",
        api_key: Optional[str] = None
    ) -> str:
        if not self.vector_store:
            return "Error: No papers indexed in vector store. Please fetch or upload papers first."

        unique_candidates = self._get_all_fallback_candidates(provider, model_name)
        invalid_key_providers: list[str] = []

        for idx, (p_curr, m_curr) in enumerate(unique_candidates):
            res = self._try_single_generation(topic, p_curr, m_curr, api_key)
            if res and not res.strip().lower().startswith("error:"):
                warn_prefix = ""
                if invalid_key_providers:
                    names = ", ".join([p.title() for p in invalid_key_providers])
                    warn_prefix = f"> ⚠️ **[PROVIDER API KEY WARNING]** Provider(s) **{names}** were attempted during fallback, but failed due to an invalid/wrong API key. Execution continued through the fallback chain.\n\n"
                if idx > 0:
                    notice = f"> [FALLBACK ALERT] The requested model ({provider.upper()} / `{model_name}`) was temporarily unavailable or hit API rate limits. Automatically failed over to **{p_curr.upper()} / `{m_curr}`**, which successfully synthesized your 8-layer research report.\n\n"
                    res = warn_prefix + notice + res
                else:
                    res = warn_prefix + res
                return res

            res_split = self._generate_split_gap_report(topic, p_curr, m_curr, api_key)
            if res_split and not res_split.strip().lower().startswith("error:"):
                warn_prefix = ""
                if invalid_key_providers:
                    names = ", ".join([p.title() for p in invalid_key_providers])
                    warn_prefix = f"> ⚠️ **[PROVIDER API KEY WARNING]** Provider(s) **{names}** were attempted during fallback, but failed due to an invalid/wrong API key. Execution continued through the fallback chain.\n\n"
                if idx > 0:
                    notice = f"> [FALLBACK ALERT] The requested model ({provider.upper()} / `{model_name}`) was temporarily unavailable or hit API rate limits. Automatically failed over to **{p_curr.upper()} / `{m_curr}`** (with prompt splitting), which successfully synthesized your 8-layer research report.\n\n"
                    res_split = warn_prefix + notice + res_split
                else:
                    res_split = warn_prefix + res_split
                return res_split

            if p_curr not in invalid_key_providers and is_auth_or_invalid_key_error(Exception(res or res_split or "")):
                invalid_key_providers.append(p_curr)

        return (
            "> [SERVICE TEMPORARILY BUSY] The system could not complete the report synthesis across available AI model providers due to temporary rate limits or network congestion.\n\n"
            "**Recommended Actions**:\n"
            "- Please wait a few seconds and try again.\n"
            "- Check your API keys in `backend/.env` (e.g. `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`).\n"
            "- If multiple research papers are selected, try selecting 1-3 papers to reduce context size."
        )

    def _try_single_followup(
        self,
        question: str,
        provider: str,
        model_name: str,
        api_key: Optional[str]
    ) -> Optional[str]:
        llms = self._get_llms_to_try(provider=provider, model_name=model_name, api_key=api_key)
        last_err = None

        for llm in llms:
            try:
                retrieved_docs = self._get_balanced_documents(question, top_k_per_paper=3, max_total_docs=15)

                formatted_context_items = []
                for d in retrieved_docs:
                    p_title = d.metadata.get('paper_title', 'Paper')
                    p_sec = d.metadata.get('section', 'Section')
                    p_url = d.metadata.get('source', '') or d.metadata.get('url', '')
                    formatted_context_items.append(f"[Paper: {p_title} | URL: {p_url} | Section: {p_sec}]\n{d.page_content[:500]}")
                formatted_context = "\n\n".join(formatted_context_items)

                prompt_template = """You are a research assistant answering follow-up questions about the analyzed research papers.
Answer the user's question using ONLY the provided multi-paper context. Always cite the paper title for your statements.
If a paper has a URL, format the paper title citation as a hyperlinked Markdown link: `[Paper Title](URL)`. Do NOT include internal chunk identifiers (e.g. Chunk 19) or wrap citations in outer double brackets.

Context:
{context}

Question: {question}

Answer (with exact source citations and paper hyperlinks):"""

                prompt = ChatPromptTemplate.from_template(prompt_template)
                chain = prompt | llm | StrOutputParser()
                answer = chain.invoke({"context": formatted_context, "question": question})

                for p in self.paper_metadata_list:
                    title = p.get("title", "").strip()
                    url = p.get("url") or p.get("pdf_url") or ""
                    if title and url and len(title) > 4:
                        escaped_title = re.escape(title)
                        pattern_bracket = rf'\[({escaped_title}[^\]]*)\](?!\()'
                        answer = re.sub(pattern_bracket, rf'[\1]({url})', answer)

                # Strip internal chunk identifiers like | Chunk 19, (Chunk 19), [Chunk 19]
                answer = re.sub(r'\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*Chunk\s*\d+\]', r'[\1](\2)', answer, flags=re.IGNORECASE)
                answer = re.sub(r'\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^\]]+)\]', r'[\1](\2)', answer)
                answer = re.sub(r'\[\[([^\]]+)\]\(([^)]+)\)\]', r'[\1](\2)', answer)
                answer = re.sub(r'\s*\|\s*Chunk\s*\d+', '', answer, flags=re.IGNORECASE)
                answer = re.sub(r'\s*\(\s*Chunk\s*\d+\s*\)', '', answer, flags=re.IGNORECASE)
                answer = re.sub(r'\[\s*Chunk\s*\d+\s*\]', '', answer, flags=re.IGNORECASE)

                record_success(provider, model_name)
                return answer
            except Exception as e:
                if is_auth_or_invalid_key_error(e):
                    record_invalid_key_failure(provider, model_name)
                else:
                    record_failure(model_name)
                last_err = e
                continue

        return f"ERROR: {str(last_err)}"

    def ask_followup(
        self,
        question: str,
        provider: str = "gemini",
        model_name: str = "gemini-3.6-flash",
        api_key: Optional[str] = None
    ) -> str:
        if not self.vector_store:
            return "No documents available. Please load papers first."

        unique_candidates = self._get_all_fallback_candidates(provider, model_name)
        invalid_key_providers: list[str] = []

        for idx, (p_curr, m_curr) in enumerate(unique_candidates):
            res = self._try_single_followup(question, p_curr, m_curr, api_key)
            if res and not res.strip().lower().startswith("error:"):
                warn_prefix = ""
                if invalid_key_providers:
                    names = ", ".join([p.title() for p in invalid_key_providers])
                    warn_prefix = f"> ⚠️ **[PROVIDER API KEY WARNING]** Provider(s) **{names}** were attempted during fallback, but failed due to an invalid/wrong API key. Execution continued through the fallback chain.\n\n"
                if idx > 0:
                    notice = f"> [FALLBACK ALERT] The requested model ({provider.upper()} / `{model_name}`) was temporarily unavailable or hit API rate limits. Automatically failed over to **{p_curr.upper()} / `{m_curr}`**, which successfully answered your follow-up query.\n\n"
                    res = warn_prefix + notice + res
                else:
                    res = warn_prefix + res
                return res

            if p_curr not in invalid_key_providers and is_auth_or_invalid_key_error(Exception(res or "")):
                invalid_key_providers.append(p_curr)


        return (
            "> [SERVICE TEMPORARILY BUSY] The system could not answer your follow-up question across available AI model providers due to temporary rate limits or high network traffic.\n\n"
            "**Recommended Actions**:\n"
            "- Please wait a few seconds and try asking again.\n"
            "- Verify your API keys in `backend/.env` (e.g. `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`)."
        )
