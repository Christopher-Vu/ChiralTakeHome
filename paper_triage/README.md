# ML Paper Triage Agent

A LangGraph-based agent that answers research questions about ML papers using arXiv and Semantic Scholar, with human-in-the-loop plan approval and full tool-call traceability.

## Quickstart

1. **Clone and enter the directory**
   ```bash
   cd paper_triage
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your keys
   ```

4. **Run with a question**
   ```bash
   python main.py "What are the most influential follow-ups to FlashAttention-2?"
   ```

> **Note on Semantic Scholar API key:** The API works without a key but rate-limits aggressively (1 req/sec). For reliable use, get a free key at https://www.semanticscholar.org/product/api and set `SEMANTIC_SCHOLAR_API_KEY` in your `.env`.

## Example Query

```bash
python main.py "What are the most influential follow-ups to FlashAttention-2, and do any address the backward-pass memory issue?"
```

The agent will:
1. Generate a 2-5 step retrieval plan
2. Display the plan and ask for your approval
3. Execute the plan (calling arXiv and Semantic Scholar APIs)
4. Synthesize an answer with citations
5. Dump the full tool-call trace

At the approval prompt, enter:
- `y` — approve and execute
- `edit` — provide feedback and regenerate the plan
- `n` — abort

## Architecture

```
START
  │
  ▼
planner ──────────────────────────────────────┐
  │                                            │
  ▼                                            │
human_approval                                 │
  │ (interrupt — waits for user input)         │
  ├── approve ──► executor ──► synthesizer ──► END
  │
  └── edit (feedback) ──────────────────────────┘
```

**planner**: Calls Claude with `PLANNER_SYSTEM` and the user's question. Uses `with_structured_output(Plan)` to produce a typed list of steps (tool name + args + rationale). If the user provided feedback from a previous rejected plan, it's included here.

**human_approval**: Uses LangGraph's `interrupt()` to pause execution and surface the formatted plan to the user. On resume, routes to `executor` (approve) or back to `planner` (edit with feedback). This is a graph edge, not a prompt instruction — the interrupt is a first-class state machine transition.

**executor**: Iterates through the plan steps and calls the real tools (arXiv, Semantic Scholar). Results are accumulated into `trace` (full provenance) and `retrieved` (deduplicated papers). Errors are recorded in the trace rather than crashing.

**synthesizer**: Calls Claude with the retrieved papers and trace as context. Produces a grounded answer that cites every claim with a paper ID. Instructed to say so explicitly if the data is insufficient.

## Framework Choice

**Why LangGraph over alternatives?**

- **vs. plain LangChain**: LangGraph provides an explicit state machine with typed state (`AgentState`), named nodes, and graph edges. The human-in-the-loop behavior is an `interrupt()` call at a graph edge — not a fragile prompt instruction like "ask the user before proceeding." State is first-class and inspectable at any point via `graph.get_state()`.

- **vs. raw Anthropic tool use**: The Anthropic API's native tool use would require manual orchestration of the plan→approve→execute→synthesize loop, manual state management, and custom interrupt/resume logic. LangGraph provides all of this with checkpointing built in.

- **vs. CrewAI**: CrewAI is designed for multi-agent collaboration with defined roles. This task has a single retrieval→synthesis pipeline with a human gate — a state machine fits better than a crew. CrewAI also makes the trace harder to surface as first-class state.

**Tradeoffs**: LangGraph adds complexity (graph construction, `Command`/`interrupt` API) that wouldn't be necessary for a simpler single-shot pipeline. The payoff is the clean interrupt/resume pattern and inspectable state, which are essential for the human-approval requirement.

## Retrieval vs. Reasoning Boundary

**The LLM can guess where to look, but only tools can make claims.**

The boundary is strict:
- **Retrieval owns**: citation counts, post-cutoff papers, exact abstract text, inter-paper relationships (who cites whom), paper IDs and years.
- **LLM owns**: query decomposition, relevance judgment, synthesis, and natural language generation.

**Concrete rule**: no number in the final answer that isn't traceable to a tool result in the trace. The synthesizer is instructed to cite every factual claim with a paper ID and to refuse to state counts or dates from memory.

This prevents the common failure mode where a model confidently states "FlashAttention-2 has 3,000 citations" from training data that may be months stale.

## Known Limitations

- **No retry logic**: if a tool call fails (network error, rate limit), the error is recorded in the trace but the step is skipped — there's no retry or fallback.
- **Single-shot plan approval**: users can reject the whole plan and provide feedback, but cannot edit individual steps. A partial edit UI would require a more complex interrupt payload.
- **No caching**: every run makes fresh API calls. Repeated queries against the same papers will re-fetch.
- **No budget guard**: there's no limit on how many papers are retrieved or how long the synthesizer prompt grows. A large citation set could exceed token limits.
- **Seed paper failure modes**: if the first search step returns no results (e.g., a paper with an unusual title), subsequent `semantic_scholar_citations` steps will fail because there's no valid `paper_id`. The trace will record the errors but the synthesizer will note the gap.
