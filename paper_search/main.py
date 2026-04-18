import sys
from dotenv import load_dotenv
from agent import build_graph, format_plan
from state import AgentState
from langgraph.types import Command
import uuid
import json


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print('Usage: python main.py "<question>"')
        sys.exit(1)

    question = sys.argv[1]
    graph = build_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_state = {
        "question": question,
        "plan": None,
        "plan_approved": False,
        "user_feedback": None,
        "trace": [],
        "retrieved": [],
        "answer": None,
    }

    graph.invoke(initial_state, config=config)

    while True:
        state = graph.get_state(config)
        if not state.next:
            break

        try:
            interrupt_payload = state.tasks[0].interrupts[0].value
        except (IndexError, AttributeError):
            print("[error] Could not read interrupt payload. State:", state)
            break

        print("\n" + "=" * 60)
        print(interrupt_payload["plan"])
        print("=" * 60)
        user_input = input("\nApprove? (y / n / edit): ").strip().lower()

        if user_input == "y":
            graph.invoke(Command(resume={"action": "approve"}), config=config)
        elif user_input.startswith("e"):
            feedback = input("Feedback: ").strip()
            graph.invoke(Command(resume={"action": "edit", "feedback": feedback}), config=config)
        else:
            print("Aborted.")
            return

    final_state = graph.get_state(config).values
    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(final_state.get("answer", "(no answer)"))
    print("\n" + "=" * 60)
    print("FULL TRACE")
    print("=" * 60)
    for tc in final_state.get("trace", []):
        print(f"\n[{tc.timestamp}] {tc.tool}({tc.args})")
        print(f"  → {tc.result_summary}")
        if tc.error:
            print(f"  ERROR: {tc.error}")


if __name__ == "__main__":
    main()
