import os
import re
import tempfile
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
import requests
from pypdf import PdfReader


CURRENT_YEAR = 2026
MIN_YEAR = CURRENT_YEAR - 2


def is_valid_recent_year(year_str: str) -> bool:
    try:
        y = int(str(year_str).strip()[:4])
        return MIN_YEAR <= y <= CURRENT_YEAR
    except (ValueError, TypeError):
        return True


class PaperFetcher:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "ResearchGapAnalyzer/2.0 (mailto:academic-rag@example.com)"
        }

    def search_arxiv(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            import arxiv
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=limit * 2,
                sort_by=arxiv.SortCriterion.Relevance
            )
            results = list(client.results(search))
            for res in results:
                pub_year = res.published.year if res.published else CURRENT_YEAR
                if pub_year < MIN_YEAR:
                    continue
                authors = [a.name for a in res.authors]
                entry_id = res.entry_id.split("/")[-1]
                papers.append({
                    "id": f"arxiv_{entry_id}",
                    "source_api": "arXiv",
                    "title": res.title.replace("\n", " ").strip(),
                    "authors": ", ".join(authors),
                    "year": str(pub_year),
                    "abstract": res.summary.replace("\n", " ").strip(),
                    "url": f"https://arxiv.org/abs/{entry_id}",
                    "pdf_url": res.pdf_url,
                    "is_open_access": True,
                    "citations": 0,
                })
                if len(papers) >= limit:
                    break
        except Exception as e:
            try:
                encoded_query = urllib.parse.quote(query)
                url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={limit * 2}"
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        published = entry.find("atom:published", ns)
                        id_elem = entry.find("atom:id", ns)
                        author_elems = entry.findall("atom:author", ns)
                        authors = [a.find("atom:name", ns).text for a in author_elems if a.find("atom:name", ns) is not None]
                        paper_id = id_elem.text.split('/')[-1] if id_elem is not None else "unknown"
                        year = published.text[:4] if published is not None and published.text else str(CURRENT_YEAR)
                        
                        if is_valid_recent_year(year):
                            papers.append({
                                "id": f"arxiv_{paper_id}",
                                "source_api": "arXiv",
                                "title": title.text.strip() if title is not None else "Untitled",
                                "authors": ", ".join(authors) if authors else "Unknown Authors",
                                "year": year,
                                "abstract": summary.text.strip() if summary is not None else "Abstract unavailable.",
                                "url": f"https://arxiv.org/abs/{paper_id}",
                                "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf",
                                "is_open_access": True,
                                "citations": 0,
                            })
                            if len(papers) >= limit:
                                break
            except Exception:
                pass
        return papers

    def search_crossref(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": query,
                "rows": limit * 2,
                "filter": f"from-pub-date:{MIN_YEAR}-01-01",
                "sort": "relevance",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                for item in items:
                    titles = item.get("title", [])
                    title = titles[0] if titles else "Untitled Work"
                    
                    pub_parts = item.get("published-print", {}).get("date-parts") or item.get("published-online", {}).get("date-parts") or item.get("issued", {}).get("date-parts")
                    year = str(pub_parts[0][0]) if pub_parts and pub_parts[0] else str(CURRENT_YEAR)
                    
                    if not is_valid_recent_year(year):
                        continue

                    authors_list = item.get("author", [])
                    authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list if a.get("family")]
                    
                    doi = item.get("DOI", "")
                    paper_url = f"https://doi.org/{doi}" if doi else item.get("URL", "")
                    
                    link_list = item.get("link", [])
                    pdf_url = None
                    for l in link_list:
                        if l.get("content-type") == "application/pdf":
                            pdf_url = l.get("URL")
                            break

                    papers.append({
                        "id": f"crossref_{doi.replace('/', '_') if doi else title[:20]}",
                        "source_api": "Crossref",
                        "title": title,
                        "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                        "year": year,
                        "abstract": item.get("abstract") or "Abstract unavailable via Crossref metadata.",
                        "url": paper_url,
                        "pdf_url": pdf_url,
                        "is_open_access": bool(pdf_url),
                        "citations": item.get("is-referenced-by-count", 0),
                    })
                    if len(papers) >= limit:
                        break
        except Exception:
            pass
        return papers

    def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": limit * 2,
                "year": f"{MIN_YEAR}-{CURRENT_YEAR}",
                "fields": "paperId,title,authors,year,abstract,openAccessPdf,url,citationCount",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    year = str(item.get("year") or CURRENT_YEAR)
                    if not is_valid_recent_year(year):
                        continue
                    oa_info = item.get("openAccessPdf") or {}
                    pdf_url = oa_info.get("url") if isinstance(oa_info, dict) else None
                    authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                    
                    papers.append({
                        "id": f"s2_{item.get('paperId')}",
                        "source_api": "Semantic Scholar",
                        "title": item.get("title", "Untitled"),
                        "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                        "year": year,
                        "abstract": item.get("abstract") or "Abstract unavailable.",
                        "url": item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId')}",
                        "pdf_url": pdf_url,
                        "is_open_access": bool(pdf_url),
                        "citations": item.get("citationCount", 0),
                    })
                    if len(papers) >= limit:
                        break
        except Exception:
            pass
        return papers

    def search_openalex(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            url = "https://api.openalex.org/works"
            params = {
                "search": query,
                "filter": f"publication_year:{MIN_YEAR}-{CURRENT_YEAR}",
                "per_page": limit * 2,
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    year = str(item.get("publication_year") or CURRENT_YEAR)
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
                    authors = [auth.get("author", {}).get("display_name") for auth in authorships if auth.get("author", {}).get("display_name")]

                    primary_loc = item.get("primary_location") or {}
                    pdf_url = primary_loc.get("pdf_url") or item.get("open_access", {}).get("oa_url")
                    paper_url = item.get("doi") or primary_loc.get("landing_page_url") or item.get("id") or ""

                    papers.append({
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
                    })
                    if len(papers) >= limit:
                        break
        except Exception:
            pass
        return papers

    def search_pubmed(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": f"{query} AND ({MIN_YEAR}:{CURRENT_YEAR}[dp])",
                "retmode": "json",
                "retmax": limit,
            }
            resp = requests.get(search_url, params=search_params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                id_list = resp.json().get("esearchresult", {}).get("idlist", [])
                if id_list:
                    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    summary_params = {
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "json",
                    }
                    sum_resp = requests.get(summary_url, params=summary_params, headers=self.headers, timeout=self.timeout)
                    if sum_resp.status_code == 200:
                        results = sum_resp.json().get("result", {})
                        for pmid in id_list:
                            item = results.get(pmid, {})
                            title = item.get("title", "Untitled PubMed Article")
                            pubdate = item.get("pubdate", "")
                            year = pubdate[:4] if pubdate else str(CURRENT_YEAR)
                            authors_list = item.get("authors", [])
                            authors = [a.get("name", "") for a in authors_list if a.get("name")]
                            
                            papers.append({
                                "id": f"pubmed_{pmid}",
                                "source_api": "PubMed",
                                "title": title.rstrip("."),
                                "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                                "year": year,
                                "abstract": f"PubMed ID: {pmid}. Published in {item.get('source', 'Journal')}.",
                                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                "pdf_url": None,
                                "is_open_access": True,
                                "citations": 0,
                            })
        except Exception:
            pass
        return papers

    def search_doaj(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        papers = []
        try:
            url = f"https://doaj.org/api/v2/search/articles/{urllib.parse.quote(query)}"
            params = {"page": 1, "pageSize": limit * 2}
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for res in results:
                    bib = res.get("bibjson", {})
                    year = str(bib.get("year") or CURRENT_YEAR)
                    if not is_valid_recent_year(year):
                        continue
                    
                    title = bib.get("title", "Untitled DOAJ Paper")
                    authors_list = bib.get("author", [])
                    authors = [a.get("name", "") for a in authors_list if a.get("name")]
                    
                    link_list = bib.get("link", [])
                    paper_url = ""
                    pdf_url = None
                    for l in link_list:
                        if l.get("type") == "fulltext":
                            paper_url = l.get("url", "")
                            if paper_url.endswith(".pdf"):
                                pdf_url = paper_url

                    papers.append({
                        "id": f"doaj_{res.get('id', title[:20])}",
                        "source_api": "DOAJ",
                        "title": title,
                        "authors": ", ".join(authors[:5]) if authors else "Unknown Authors",
                        "year": year,
                        "abstract": bib.get("abstract") or "Abstract unavailable via DOAJ index.",
                        "url": paper_url or f"https://doaj.org/article/{res.get('id')}",
                        "pdf_url": pdf_url,
                        "is_open_access": True,
                        "citations": 0,
                    })
                    if len(papers) >= limit:
                        break
        except Exception:
            pass
        return papers

    def search_all(self, query: str, limit_per_source: int = 3) -> List[Dict[str, Any]]:
        combined = []
        seen_titles = set()

        sources = [
            self.search_arxiv(query, limit=limit_per_source),
            self.search_crossref(query, limit=limit_per_source),
            self.search_semantic_scholar(query, limit=limit_per_source),
            self.search_openalex(query, limit=limit_per_source),
            self.search_pubmed(query, limit=limit_per_source),
            self.search_doaj(query, limit=limit_per_source),
        ]

        for source_list in sources:
            for paper in source_list:
                clean_title = re.sub(r"[^\w\s]", "", paper["title"].lower()).strip()
                if clean_title and clean_title not in seen_titles:
                    seen_titles.add(clean_title)
                    combined.append(paper)

        def sort_key(p):
            oa_score = 1 if p.get("is_open_access") else 0
            try:
                year_score = int(p.get("year", 2024))
            except Exception:
                year_score = 2024
            citations = p.get("citations") or 0
            return (oa_score, year_score, citations)

        combined.sort(key=sort_key, reverse=True)
        return combined

    def download_and_extract_text(self, paper: Dict[str, Any]) -> str:
        pdf_url = paper.get("pdf_url")
        extracted_text = ""

        if pdf_url:
            try:
                resp = requests.get(pdf_url, headers=self.headers, timeout=20, stream=True)
                if resp.status_code == 200 and ("pdf" in resp.headers.get("Content-Type", "").lower() or pdf_url.endswith(".pdf")):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(resp.content)
                        tmp_path = tmp.name
                    
                    try:
                        reader = PdfReader(tmp_path)
                        pages_text = []
                        for i, page in enumerate(reader.pages):
                            t = page.extract_text()
                            if t and len(t.strip()) > 50:
                                pages_text.append(f"--- Page {i+1} ---\n{t.strip()}")
                        if pages_text:
                            extracted_text = "\n\n".join(pages_text)
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
            except Exception:
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
