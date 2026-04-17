import os
import arxiv
import requests
from state import Paper


def arxiv_search(query: str, max_results: int = 5):
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results)
    results = list(client.results(search))

    papers = []
    for r in results:
        # entry_id is like "http://arxiv.org/abs/2307.08691v2"
        raw_id = r.entry_id.split("/abs/")[-1]
        arxiv_id = raw_id.rsplit("v", 1)[0]
        papers.append(Paper(
            paper_id=arxiv_id,
            title=r.title,
            abstract=r.summary,
            year=r.published.year if r.published else None,
            citation_count=None,
            influential_citation_count=None,
            source="arxiv",
        ))

    summary = f"Found {len(papers)} papers on arXiv for query '{query}'"
    raw = {"query": query, "results": [p.model_dump() for p in papers]}
    return summary, raw, papers


def semantic_scholar_search(query: str, limit: int = 10):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,year,citationCount,influentialCitationCount,externalIds",
    }
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        papers.append(Paper(
            paper_id=item["paperId"],
            title=item.get("title", ""),
            abstract=item.get("abstract"),
            year=item.get("year"),
            citation_count=item.get("citationCount"),
            influential_citation_count=item.get("influentialCitationCount"),
            source="semantic_scholar",
        ))

    summary = f"Found {len(papers)} papers on Semantic Scholar for query '{query}'"
    raw = {"query": query, "results": data}
    return summary, raw, papers


def semantic_scholar_citations(paper_id: str, limit: int = 20):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
    params = {
        "limit": limit,
        "fields": "citingPaper.paperId,citingPaper.title,citingPaper.abstract,citingPaper.year,citingPaper.citationCount,citingPaper.influentialCitationCount",
    }
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        cp = item.get("citingPaper", {})
        if not cp.get("paperId"):
            continue
        papers.append(Paper(
            paper_id=cp["paperId"],
            title=cp.get("title", ""),
            abstract=cp.get("abstract"),
            year=cp.get("year"),
            citation_count=cp.get("citationCount"),
            influential_citation_count=cp.get("influentialCitationCount"),
            source="semantic_scholar",
        ))

    summary = f"Found {len(papers)} papers citing {paper_id}"
    raw = {"paper_id": paper_id, "results": data}
    return summary, raw, papers


TOOLS = {
    "arxiv_search": arxiv_search,
    "semantic_scholar_search": semantic_scholar_search,
    "semantic_scholar_citations": semantic_scholar_citations,
}
