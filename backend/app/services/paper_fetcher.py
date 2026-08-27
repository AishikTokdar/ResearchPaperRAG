import concurrent.futures
import re
import urllib.parse
from datetime import UTC, datetime
from typing import Any
from xml.etree import ElementTree as ET

import requests

from .hybrid_retrieval import words
from .pdf_extraction import extract_pdf_bytes
from .safe_download import download_pdf

CURRENT_YEAR = datetime.now(UTC).year
MIN_YEAR = CURRENT_YEAR - 2
_SEARCH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=6, thread_name_prefix="paper-search"
)


class _TimeoutAdapter(requests.adapters.HTTPAdapter):
    """The installed arXiv SDK omits a requests timeout; enforce one at transport level."""

    def __init__(self, timeout: int):
        super().__init__()
        self.timeout = timeout

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        return super().send(
            request,
            stream=stream,
            timeout=self.timeout if timeout is None else timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )


def is_valid_recent_year(year_str: str) -> bool:
    try:
        y = int(str(year_str).strip()[:4])
        return MIN_YEAR <= y <= CURRENT_YEAR
    except (ValueError, TypeError):
        return True


class PaperFetcher:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {"User-Agent": "ResearchGapAnalyzer/2.0 (mailto:academic-rag@example.com)"}

    def search_arxiv(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            import arxiv

            # Sanitize and truncate extra long search phrases for arXiv API
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()
            search_q = " ".join(clean_q.split()[:10]) if len(clean_q.split()) > 10 else clean_q

            client = arxiv.Client(page_size=limit * 2, delay_seconds=3, num_retries=1)
            # SDK 4.x exposes no timeout option. This verified transport seam has a regression test.
            client._session.mount("https://", _TimeoutAdapter(self.timeout))
            search = arxiv.Search(
                query=search_q, max_results=limit * 2, sort_by=arxiv.SortCriterion.Relevance
            )
            try:
                results = list(client.results(search))
            finally:
                client._session.close()
            for res in results:
                pub_year = res.published.year if res.published else None
                if pub_year is not None and not MIN_YEAR <= pub_year <= CURRENT_YEAR:
                    continue
                authors = [a.name for a in res.authors]
                entry_id = res.entry_id.split("/")[-1]
                papers.append(
                    {
                        "id": f"arxiv_{entry_id}",
                        "source_api": "arXiv",
                        "title": res.title.replace("\n", " ").strip(),
                        "authors": ", ".join(authors),
                        "year": str(pub_year) if pub_year is not None else "Unknown",
                        "abstract": res.summary.replace("\n", " ").strip(),
                        "url": f"https://arxiv.org/abs/{entry_id}",
                        "pdf_url": res.pdf_url,
                        "is_open_access": True,
                        "citations": 0,
                    }
                )
                if len(papers) >= limit:
                    break
        except Exception:
            try:
                encoded_query = urllib.parse.quote(query)
                url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={limit * 2}"
                resp = requests.get(url, timeout=self.timeout)
                resp.raise_for_status()
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        published = entry.find("atom:published", ns)
                        id_elem = entry.find("atom:id", ns)
                        author_elems = entry.findall("atom:author", ns)
                        authors = [
                            name
                            for a in author_elems
                            if (name := a.findtext("atom:name", default="", namespaces=ns))
                        ]
                        paper_id = (
                            (id_elem.text or "unknown").split("/")[-1]
                            if id_elem is not None
                            else "unknown"
                        )
                        year = (
                            published.text[:4]
                            if published is not None and published.text
                            else "Unknown"
                        )

                        if is_valid_recent_year(year):
                            papers.append(
                                {
                                    "id": f"arxiv_{paper_id}",
                                    "source_api": "arXiv",
                                    "title": (title.text or "Untitled").strip()
                                    if title is not None
                                    else "Untitled",
                                    "authors": ", ".join(authors) if authors else "Unknown Authors",
                                    "year": year,
                                    "abstract": (summary.text or "Abstract unavailable.").strip()
                                    if summary is not None
                                    else "Abstract unavailable.",
                                    "url": f"https://arxiv.org/abs/{paper_id}",
                                    "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf",
                                    "is_open_access": True,
                                    "citations": 0,
                                }
                            )
                            if len(papers) >= limit:
                                break
            except Exception:
                raise
        return papers

    def search_crossref(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            url = "https://api.crossref.org/works"
            params: dict[str, Any] = {
                "query": query,
                "rows": limit * 2,
                "filter": f"from-pub-date:{MIN_YEAR}-01-01",
                "sort": "relevance",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                for item in items:
                    titles = item.get("title", [])
                    title = titles[0] if titles else "Untitled Work"

                    pub_parts = (
                        item.get("published-print", {}).get("date-parts")
                        or item.get("published-online", {}).get("date-parts")
                        or item.get("issued", {}).get("date-parts")
                    )
                    year = str(pub_parts[0][0]) if pub_parts and pub_parts[0] else "Unknown"

                    if not is_valid_recent_year(year):
                        continue

                    authors_list = item.get("author", [])
                    authors = [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in authors_list
                        if a.get("family")
                    ]

                    doi = item.get("DOI", "")
                    paper_url = f"https://doi.org/{doi}" if doi else item.get("URL", "")

                    link_list = item.get("link", [])
                    pdf_url = None
                    for link in link_list:
                        if link.get("content-type") == "application/pdf":
                            pdf_url = link.get("URL")
                            break

                    papers.append(
                        {
                            "id": f"crossref_{doi.replace('/', '_') if doi else title[:20]}",
                            "source_api": "Crossref",
                            "title": title,
                            "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                            "year": year,
                            "abstract": item.get("abstract")
                            or "Abstract unavailable via Crossref metadata.",
                            "url": paper_url,
                            "doi": doi,
                            "pdf_url": pdf_url,
                            "is_open_access": bool(pdf_url),
                            "citations": item.get("is-referenced-by-count", 0),
                        }
                    )
                    if len(papers) >= limit:
                        break
        except Exception:
            raise
        return papers

    def search_semantic_scholar(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params: dict[str, Any] = {
                "query": query,
                "limit": limit * 2,
                "year": f"{MIN_YEAR}-{CURRENT_YEAR}",
                "fields": "paperId,title,authors,year,abstract,openAccessPdf,url,citationCount",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    year = str(item.get("year") or "Unknown")
                    if not is_valid_recent_year(year):
                        continue
                    oa_info = item.get("openAccessPdf") or {}
                    pdf_url = oa_info.get("url") if isinstance(oa_info, dict) else None
                    authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]

                    papers.append(
                        {
                            "id": f"s2_{item.get('paperId')}",
                            "source_api": "Semantic Scholar",
                            "title": item.get("title", "Untitled"),
                            "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                            "year": year,
                            "abstract": item.get("abstract") or "Abstract unavailable.",
                            "url": item.get("url")
                            or f"https://www.semanticscholar.org/paper/{item.get('paperId')}",
                            "pdf_url": pdf_url,
                            "is_open_access": bool(pdf_url),
                            "citations": item.get("citationCount", 0),
                        }
                    )
                    if len(papers) >= limit:
                        break
        except Exception:
            raise
        return papers

    def search_openalex(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            url = "https://api.openalex.org/works"
            params: dict[str, Any] = {
                "search": query,
                "filter": f"publication_year:{MIN_YEAR}-{CURRENT_YEAR}",
                "per_page": limit * 2,
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    year = str(item.get("publication_year") or "Unknown")
                    if not is_valid_recent_year(year):
                        continue

                    abstract = "Abstract unavailable."
                    inv_index = item.get("abstract_inverted_index")
                    if isinstance(inv_index, dict):
                        try:
                            word_positions = []
                            for word, pos_list in inv_index.items():
                                for pos in pos_list:
                                    word_positions.append((pos, word))
                            word_positions.sort()
                            abstract = " ".join([wp[1] for wp in word_positions])
                        except Exception:
                            pass

                    authorships = item.get("authorships", [])
                    authors = [
                        auth.get("author", {}).get("display_name")
                        for auth in authorships
                        if auth.get("author", {}).get("display_name")
                    ]

                    primary_loc = item.get("primary_location") or {}
                    pdf_url = primary_loc.get("pdf_url") or item.get("open_access", {}).get(
                        "oa_url"
                    )
                    paper_url = (
                        item.get("doi")
                        or primary_loc.get("landing_page_url")
                        or item.get("id")
                        or ""
                    )

                    papers.append(
                        {
                            "id": f"oa_{item.get('id', '').split('/')[-1]}",
                            "source_api": "OpenAlex",
                            "title": item.get("display_name") or item.get("title") or "Untitled",
                            "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                            "year": year,
                            "abstract": abstract,
                            "url": paper_url,
                            "pdf_url": pdf_url,
                            "is_open_access": item.get("open_access", {}).get("is_oa", False),
                            "citations": item.get("cited_by_count", 0),
                        }
                    )
                    if len(papers) >= limit:
                        break
        except Exception:
            raise
        return papers

    def search_pubmed(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params: dict[str, Any] = {
                "db": "pubmed",
                "term": f"{query} AND ({MIN_YEAR}:{CURRENT_YEAR}[dp])",
                "retmode": "json",
                "retmax": limit,
            }
            resp = requests.get(
                search_url, params=search_params, headers=self.headers, timeout=self.timeout
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                id_list = resp.json().get("esearchresult", {}).get("idlist", [])
                if id_list:
                    response = requests.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                        params={"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"},
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    root = ET.fromstring(response.content)
                    for article in root.findall(".//PubmedArticle"):
                        pmid = article.findtext(".//MedlineCitation/PMID", "")
                        title_node = article.find(".//ArticleTitle")
                        title = (
                            "".join(title_node.itertext())
                            if title_node is not None
                            else "Untitled PubMed Article"
                        )
                        year = (
                            article.findtext(".//JournalIssue/PubDate/Year")
                            or article.findtext(".//JournalIssue/PubDate/MedlineDate", "")[:4]
                        )
                        if not is_valid_recent_year(year):
                            continue
                        abstract_parts = []
                        for part in article.findall(".//Abstract/AbstractText"):
                            label = part.get("Label", "")
                            abstract_parts.append(
                                (label + ": " if label else "") + "".join(part.itertext())
                            )
                        authors = [
                            " ".join(
                                filter(
                                    None, [author.findtext("ForeName"), author.findtext("LastName")]
                                )
                            )
                            for author in article.findall(".//AuthorList/Author")
                        ]
                        doi = next(
                            (
                                node.text or ""
                                for node in article.findall(".//ArticleId")
                                if node.get("IdType") == "doi"
                            ),
                            "",
                        )
                        papers.append(
                            {
                                "id": f"pubmed_{pmid}",
                                "source_api": "PubMed",
                                "title": title,
                                "authors": ", ".join(authors[:5]) or "Unknown Authors",
                                "year": year,
                                "abstract": "\n".join(abstract_parts) or "Abstract unavailable.",
                                "doi": doi,
                                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                "pdf_url": None,
                                "is_open_access": False,
                                "citations": 0,
                            }
                        )
        except Exception:
            raise
        return papers

    def search_doaj(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = []
        try:
            url = f"https://doaj.org/api/v2/search/articles/{urllib.parse.quote(query)}"
            params: dict[str, Any] = {"page": 1, "pageSize": limit * 2}
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for res in results:
                    bib = res.get("bibjson", {})
                    year = str(bib.get("year") or "Unknown")
                    if not is_valid_recent_year(year):
                        continue

                    title = bib.get("title", "Untitled DOAJ Paper")
                    authors_list = bib.get("author", [])
                    authors = [a.get("name", "") for a in authors_list if a.get("name")]

                    link_list = bib.get("link", [])
                    paper_url = ""
                    pdf_url = None
                    for link in link_list:
                        if link.get("type") == "fulltext":
                            paper_url = link.get("url", "")
                            if paper_url.endswith(".pdf"):
                                pdf_url = paper_url

                    papers.append(
                        {
                            "id": f"doaj_{res.get('id', title[:20])}",
                            "source_api": "DOAJ",
                            "title": title,
                            "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                            "year": year,
                            "abstract": bib.get("abstract")
                            or "Abstract unavailable via DOAJ index.",
                            "url": paper_url or f"https://doaj.org/article/{res.get('id')}",
                            "pdf_url": pdf_url,
                            "is_open_access": True,
                            "citations": 0,
                        }
                    )
                    if len(papers) >= limit:
                        break
        except Exception:
            raise
        return papers

    def search_all(
        self,
        query: str,
        limit_per_source: int = 3,
        source_status: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        search_funcs = [
            ("arXiv", self.search_arxiv),
            ("Crossref", self.search_crossref),
            ("Semantic Scholar", self.search_semantic_scholar),
            ("OpenAlex", self.search_openalex),
            ("PubMed", self.search_pubmed),
            ("DOAJ", self.search_doaj),
        ]

        sources: dict[str, list[dict[str, Any]]] = {}
        statuses: list[dict[str, Any]] = []
        executor = _SEARCH_EXECUTOR
        future_map = {}
        try:
            future_map = {
                executor.submit(fn, query, limit_per_source): name for name, fn in search_funcs
            }
            done, pending = concurrent.futures.wait(future_map, timeout=12.0)
            for future, name in future_map.items():
                if future in pending:
                    statuses.append({"source": name, "status": "timeout"})
                    continue
                try:
                    result = future.result()
                    sources[name] = result
                    statuses.append({"source": name, "status": "ok", "count": len(result)})
                except Exception:
                    statuses.append({"source": name, "status": "unavailable"})
        finally:
            for future in future_map:
                future.cancel()

        combined = []
        seen_titles: set[str] = set()
        seen_dois: set[str] = set()
        query_terms = set(words(query))
        for name, _ in search_funcs:
            for rank, paper in enumerate(sources.get(name, [])):
                title = " ".join(words(paper["title"]))
                doi = (
                    str(
                        paper.get("doi")
                        or (
                            paper.get("url", "").split("doi.org/", 1)[1]
                            if "doi.org/" in paper.get("url", "")
                            else ""
                        )
                    )
                    .casefold()
                    .strip()
                )
                if title in seen_titles or (doi and doi in seen_dois):
                    continue
                seen_titles.add(title)
                if doi:
                    seen_dois.add(doi)
                relevance = len(query_terms & set(words(paper["title"]))) / max(1, len(query_terms))
                paper["_rank_score"] = relevance + 1 / (60 + rank + 1)
                combined.append(paper)
        combined.sort(key=lambda paper: paper["_rank_score"], reverse=True)
        for paper in combined:
            paper.pop("_rank_score", None)
        if source_status is not None:
            source_status.extend(statuses)
        return combined

    def download_and_extract_text(self, paper: dict[str, Any]) -> str:
        pdf_url = paper.get("pdf_url")
        extracted_text = ""

        abstract = str(paper.get("abstract") or "").strip()
        paper["evidence_scope"] = (
            "metadata_only"
            if not abstract or abstract.startswith(("Abstract unavailable", "PubMed ID:"))
            else "abstract_only"
        )
        if pdf_url:
            try:
                data = download_pdf(pdf_url)
                parsed = extract_pdf_bytes(data)
                extracted_text = "\n\n".join(
                    f"--- Page {page['page'] + 1} ---\n{page['text']}" for page in parsed["pages"]
                )
                paper["evidence_scope"] = "full_text" if parsed["complete"] else "partial_full_text"
            except Exception:
                # Download failures yield explicitly limited abstract evidence, never fabricated full text.
                pass

        if not extracted_text.strip():
            extracted_text = (
                f"Paper Title: {paper.get('title')}\n"
                f"Authors: {paper.get('authors')}\n"
                f"Publication Year: {paper.get('year')}\n"
                f"Source: {paper.get('source_api')} ({paper.get('url')})\n\n"
                f"ABSTRACT:\n{paper.get('abstract')}\n"
            )

        return extracted_text
