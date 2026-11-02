"""
Entry point (CLI interface).

Usage:
    python main.py "Scrie o funcție care validează un CNP românesc"
    python main.py                  # asks for the task on the keyboard
    python main.py --resume         # continues the LAST interrupted run
    python main.py --resume a1b2c3  # continues the run with this id

Main loop:
    1. run the graph until it finishes OR until a node asks for input (`interrupt`);
    2. if it stopped for input, show the question and read the answer;
    3. resume the graph with `Command(resume=answer)` and repeat.

The state is saved to disk after every node (see persistence.py), so after a
crash you can continue with `--resume` without losing the steps already done.
"""

import argparse
import logging
import sys
import termios

from langgraph.types import Command

from config import SETTINGS
from graph import build_graph
from llm import AllModelsExhaustedError
from persistence import last_thread_id, new_thread_id, open_checkpointer
from state import initial_state
from utils.user_io import UserPrompt

# How many steps the graph may take in a single run (between two questions).
# LangGraph allows 25 by default; the code loops can easily exceed that.
RECURSION_LIMIT = 150

# The line that ends a multi-line answer (e.g. pasted code).
END_OF_INPUT = "END"


def main() -> None:
    args = parse_args()
    show_llm_retries()

    # On-disk checkpointer: the state is saved after EVERY node (see persistence.py).
    app = build_graph(checkpointer=open_checkpointer())

    if args.resume is None:  # new run
        thread_id = new_thread_id()
        print_thread_id(thread_id)
        graph_input = initial_state(" ".join(args.task) or input("Descrie task-ul: ").strip())
    else:  # resume: from the given id or from the last run
        thread_id = args.resume or last_thread_id() or sys.exit("Nu există nicio rulare de reluat.")
        print_thread_id(thread_id)
        graph_input = resume_input(app, make_config(thread_id))

    try:
        final_state = run_agent(app, make_config(thread_id), graph_input)
    except AllModelsExhaustedError as error:
        # A clear message instead of a traceback: this is not a bug, it's the Groq account limit.
        sys.exit(f"\n✖ {error}\nStarea e salvată; continui mai târziu cu: python main.py --resume")

    print("\n" + "=" * 70)
    print(final_state["final_report"])


def parse_args() -> argparse.Namespace:
    """Command-line arguments: the task OR `--resume [id]`."""
    parser = argparse.ArgumentParser(description="Agent asistent de cod cu auto-corecție.")
    parser.add_argument("task", nargs="*", help="cerința (dacă lipsește, e cerută de la tastatură)")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",  # `--resume` without a value -> "" -> the last run
        metavar="ID",
        help="continuă o rulare întreruptă (implicit: ultima)",
    )
    return parser.parse_args()


def print_thread_id(thread_id: str) -> None:
    """Prints the run id, so the user knows how to resume it."""
    print(f"(id rulare: {thread_id} - dacă se oprește, continui cu: python main.py --resume)")


def make_config(thread_id: str) -> dict:
    """The LangGraph config: `thread_id` selects the run in the checkpointer."""
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def show_llm_retries() -> None:
    """Shows the Groq client's messages when it retries a request.

    Without this, on a rate limit (429) the agent looks "frozen" while it waits.
    """
    logging.basicConfig(format="  ⚠ %(message)s")
    logging.getLogger("groq._base_client").setLevel(logging.INFO)


def resume_input(app, config: dict):
    """What we give the graph so it continues a saved run.

    - the run stopped at a QUESTION -> ask it again and send the answer;
    - it stopped for another reason (crash) -> `None` = "continue from the last checkpoint"
      (the node that crashed runs again, the ones before it don't).
    """
    snapshot = app.get_state(config)
    if not snapshot.values:
        sys.exit(f"Rularea '{config['configurable']['thread_id']}' nu există în {SETTINGS.checkpoint_db}.")

    print(f"Reiau rularea; următorul pas: {', '.join(snapshot.next) or '(rularea e deja terminată)'}")
    if snapshot.interrupts:
        return Command(resume=ask_in_terminal(snapshot.interrupts[0].value))
    return None


def run_agent(app, config: dict, graph_input) -> dict:
    """Runs the graph end to end, answering all of its questions.

    `graph_input` is the initial state (new run), `None` or a `Command` (resume).
    """
    while True:
        prompt = run_until_interrupt(app, graph_input, config)
        if prompt is None:  # the graph reached END
            break
        graph_input = Command(resume=ask_in_terminal(prompt))

    return app.get_state(config).values


def run_until_interrupt(app, graph_input, config) -> UserPrompt | None:
    """Runs the graph until the end or until the first `interrupt()`.

    Returns the question (the interrupt payload) or `None` if the graph finished.
    """
    for update in app.stream(graph_input, config, stream_mode="updates"):
        # When a node calls interrupt(), the stream emits the special "__interrupt__" key.
        if "__interrupt__" in update:
            return update["__interrupt__"][0].value
    return None


def ask_in_terminal(prompt: UserPrompt) -> str:
    """Shows one of the agent's questions and reads the user's answer."""
    print("\n" + "=" * 70)
    print(f"[{prompt['title']}]")
    print("-" * 70)
    print(prompt["message"])
    print("-" * 70)
    print(prompt["question"])

    discard_typed_ahead_input()
    if prompt["multiline"]:
        return read_multiline()
    return input("> ")


def discard_typed_ahead_input() -> None:
    """Discards whatever was typed while the agent was working.

    Otherwise, text typed "ahead" (e.g. an "ok" pressed while the LLM was running)
    would be taken as the answer to the NEXT question, without the user seeing it.
    """
    if sys.stdin.isatty():
        termios.tcflush(sys.stdin, termios.TCIFLUSH)


def read_multiline() -> str:
    """Reads several lines until an `END` line (or Ctrl+D)."""
    print(f"(încheie cu o linie care conține doar '{END_OF_INPUT}')")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == END_OF_INPUT:
            break
        lines.append(line)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
