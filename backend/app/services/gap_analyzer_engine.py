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
                chunk.metadata["section"] = f"Chunk {i+1}"
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

    def _get_llm(self, provider: str = "groq", model_name: str = "openai/gpt-oss-120b", api_key: Optional[str] = None):
        provider = provider.lower() if provider else "groq"
        
        if provider == "groq":
            key = api_key or os.getenv("GROQ_API_KEY")
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=key or "placeholder",
                model=model_name or "llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "openrouter":
            key = api_key or os.getenv("OPENROUTER_API_KEY")
            return ChatOpenAI(
                base_url=os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
                api_key=key or "placeholder",
                model=model_name or "meta-llama/llama-3.3-70b-instruct:free",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "cerebras":
            key = api_key or os.getenv("CEREBRAS_API_KEY")
            return ChatOpenAI(
                base_url="https://api.cerebras.ai/v1",
                api_key=key or "placeholder",
                model=model_name or "llama3.3-70b",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "sambanova":
            key = api_key or os.getenv("SAMBANOVA_API_KEY")
            return ChatOpenAI(
                base_url="https://api.sambanova.ai/v1",
                api_key=key or "placeholder",
                model=model_name or "Meta-Llama-3.3-70B-Instruct",
                temperature=0.2,
                max_tokens=8192,
            )
        elif provider == "huggingface":
            key = api_key or os.getenv("HF_API_KEY")
            return ChatOpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=key or "placeholder",
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

    def generate_gap_report(
        self,
        topic: str,
        provider: str = "groq",
        model_name: str = "openai/gpt-oss-120b",
        api_key: Optional[str] = None
    ) -> str:
        if not self.vector_store:
            return "Error: No papers indexed in vector store. Please fetch or upload papers first."

        llm = self._get_llm(provider=provider, model_name=model_name, api_key=api_key)

        retriever = self.vector_store.as_retriever(search_kwargs={"k": 8})
        retrieved_docs = retriever.invoke(f"Research gaps trends methods limitations contradictions for {topic}")

        formatted_context_items = []
        for d in retrieved_docs:
            paper_title = d.metadata.get("paper_title", "Unknown")
            section = d.metadata.get("section", "Section N/A")
            year = d.metadata.get("year", "")
            url = d.metadata.get("source", "") or d.metadata.get("url", "")
            formatted_context_items.append(
                f"[Paper: {paper_title} ({year}) | URL: {url} | Section: {section}]\n{d.page_content.strip()}"
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

        try:
            report = chain.invoke({"topic": topic, "context": formatted_context})

            for p in self.paper_metadata_list:
                title = p.get("title", "").strip()
                url = p.get("url") or p.get("pdf_url") or ""
                if title and url and len(title) > 4:
                    escaped_title = re.escape(title)
                    pattern_bracket = rf'\[({escaped_title}[^\]]*)\](?!\()'
                    report = re.sub(pattern_bracket, rf'[\1]({url})', report)

            return report
        except Exception as e:
            return f"Error generating research gap report: {str(e)}"

    def ask_followup(
        self,
        question: str,
        provider: str = "groq",
        model_name: str = "openai/gpt-oss-120b",
        api_key: Optional[str] = None
    ) -> str:
        if not self.vector_store:
            return "No documents available. Please load papers first."

        llm = self._get_llm(provider=provider, model_name=model_name, api_key=api_key)
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})

        prompt_template = """You are a research assistant answering follow-up questions about the analyzed research papers.
Answer the user's question using ONLY the provided multi-paper context. Always cite the paper title and section for your statements.
If a paper has a URL, format the paper title citation as a hyperlinked Markdown link: `[Paper Title](URL)`.

Context:
{context}

Question: {question}

Answer (with exact source citations and paper hyperlinks):"""

        prompt = ChatPromptTemplate.from_template(prompt_template)

        def format_docs(docs):
            formatted = []
            for d in docs:
                p_title = d.metadata.get('paper_title', 'Paper')
                p_sec = d.metadata.get('section', 'Section')
                p_url = d.metadata.get('source', '') or d.metadata.get('url', '')
                formatted.append(f"[Paper: {p_title} | URL: {p_url} | Section: {p_sec}]\n{d.page_content}")
            return "\n\n".join(formatted)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        try:
            answer = rag_chain.invoke(question)

            for p in self.paper_metadata_list:
                title = p.get("title", "").strip()
                url = p.get("url") or p.get("pdf_url") or ""
                if title and url and len(title) > 4:
                    escaped_title = re.escape(title)
                    pattern_bracket = rf'\[({escaped_title}[^\]]*)\](?!\()'
                    answer = re.sub(pattern_bracket, rf'[\1]({url})', answer)

            return answer
        except Exception as e:
            return f"Error answering question: {str(e)}"
