# ML Paper Search Agent

A LangGraph-based agent that answers research questions about ML papers using arXiv and Semantic Scholar, with human-in-the-loop plan approval and full tool-call traceability.

## Quickstart

1. **Clone and enter the directory**
   ```bash
   cd paper_search
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # add a claude api key in the file
   ```

4. **Run with a question**
   ```bash
   python main.py "What are the most influential follow-ups to the original transformer paper?"
   ```

## Example Query

```bash
python main.py "What are the most influential follow-ups to the original transformer paper?"
```

The agent will:
1. Generate a 2-5 step retrieval plan
2. Display the plan and ask for your approval
3. Execute the plan (calling the arXiv API)
4. Synthesize an answer with citations
5. Dump the full tool-call trace

At the approval prompt, enter:
- `y` — approve and execute
- `edit` — provide feedback and regenerate the plan
- `n` — abort

## Design Decisions

**Why LangGraph** LangGraph is more or less essential for human-in-the-loop interrupts (plan approval, edits). Iterating on output after API calls are already made is computationally disastrous, so they are a necessary design choice; LangGraph facilitates them.

**Retrieval vs. reasoning** Retrieval handles anything that requires external knowledge (and by extension, tool calls); paper existence and abstracts, for example, shouldn't be adressed without retrieval. The LLM reasons over making tool (retrieval) calls and writing the final answer. 

## Architecture

```
START
  │
  ▼
planner ───────────────────────────────────────┐
  │                                            │
  ▼                                            │
human_approval                                 │
  │ (interrupt — waits for user input)         │
  ├── approve ──► executor ──► synthesizer ──► END
  │
  └── edit (feedback) ─────────────────────────┘
```
