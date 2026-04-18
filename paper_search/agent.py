from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState, Plan, PlanStep, ToolCall, Paper
from tools import TOOLS
from prompts import PLANNER_SYSTEM, SYNTHESIZER_SYSTEM, EXECUTOR_SYSTEM
from datetime import datetime
import json

model = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)


def format_plan(plan: Plan) -> str:
    lines = [f"Plan: {plan.summary}", ""]
    for step in plan.steps:
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in step.args.items())
        lines.append(f"Step {step.step_id}: {step.action}")
        lines.append(f"  Tool: {step.tool}({args_str})")
        lines.append(f"  Why: {step.rationale}")
        lines.append("")
    return "\n".join(lines)


def planner_node(state: AgentState) -> dict:
    messages = [SystemMessage(content=PLANNER_SYSTEM)]
    user_content = f"Question: {state['question']}"
    if state.get("user_feedback"):
        user_content += f"\n\nThe user gave this feedback on the previous plan: {state['user_feedback']}"
    messages.append(HumanMessage(content=user_content))

    structured_model = model.with_structured_output(Plan)
    plan = structured_model.invoke(messages)
    return {"plan": plan, "user_feedback": None}


def human_approval_node(state: AgentState) -> Command:
    formatted = format_plan(state["plan"])
    resume_value = interrupt({
        "plan": formatted,
        "plan_obj": state["plan"].model_dump(),
    })

    action = resume_value.get("action")
    if action == "approve":
        return Command(update={"plan_approved": True}, goto="executor")
    elif action == "edit":
        feedback = resume_value.get("feedback", "")
        return Command(update={"user_feedback": feedback, "plan": None}, goto="planner")
    else:
        return Command(update={"plan_approved": True}, goto="executor")


def executor_node(state: AgentState) -> dict:
    new_trace = []
    new_retrieved = []
    seen_ids = set()

    for step in state["plan"].steps:
        tool_fn = TOOLS[step.tool]
        try:
            summary, raw, papers = tool_fn(**step.args)
            tool_call = ToolCall(
                step_id=step.step_id,
                tool=step.tool,
                args=step.args,
                result_summary=summary,
                raw_result=raw,
                timestamp=datetime.utcnow().isoformat(),
            )
            new_trace.append(tool_call)
            for p in papers:
                if p.paper_id not in seen_ids:
                    seen_ids.add(p.paper_id)
                    new_retrieved.append(p)
            print(f"[tool] {step.tool}({step.args}) → {summary}")
        except Exception as e:
            tool_call = ToolCall(
                step_id=step.step_id,
                tool=step.tool,
                args=step.args,
                result_summary=f"ERROR: {e}",
                raw_result={},
                timestamp=datetime.utcnow().isoformat(),
                error=str(e),
            )
            new_trace.append(tool_call)
            print(f"[tool] {step.tool}({step.args}) → ERROR: {e}")

    return {"trace": new_trace, "retrieved": new_retrieved}


def synthesizer_node(state: AgentState) -> dict:
    papers_json = json.dumps([p.model_dump() for p in state["retrieved"]], indent=2)
    trace_json = json.dumps(
        [{"step_id": tc.step_id, "tool": tc.tool, "args": tc.args, "result_summary": tc.result_summary, "error": tc.error}
         for tc in state["trace"]],
        indent=2
    )

    user_content = (
        f"Question: {state['question']}\n\n"
        f"Retrieved papers:\n{papers_json}\n\n"
        f"Tool execution trace:\n{trace_json}"
    )
    messages = [
        SystemMessage(content=SYNTHESIZER_SYSTEM),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)
    return {"answer": response.content}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner_node)
    g.add_node("human_approval", human_approval_node)
    g.add_node("executor", executor_node)
    g.add_node("synthesizer", synthesizer_node)
    g.add_edge(START, "planner")
    g.add_edge("planner", "human_approval")
    g.add_edge("executor", "synthesizer")
    g.add_edge("synthesizer", END)
    return g.compile(checkpointer=MemorySaver())
