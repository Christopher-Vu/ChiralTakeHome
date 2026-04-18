import arxiv
from state import Paper


def arxiv_search(query: str, max_results: int = 5):
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results)
    results = list(client.results(search))

    papers = []
    for r in results:
        raw_id = r.entry_id.split("/abs/")[-1]
        arxiv_id = raw_id.rsplit("v", 1)[0]
        papers.append(Paper(
            paper_id=arxiv_id,
            title=r.title,
            abstract=r.summary,
            year=r.published.year if r.published else None,
            source="arxiv",
        ))

    summary = f"Found {len(papers)} papers on arXiv for query '{query}'"
    raw = {"query": query, "results": [p.model_dump() for p in papers]}
    return summary, raw, papers


TOOLS = {
    "arxiv_search": arxiv_search,
}
