"""
Punctul de intrare (interfața CLI).

Rulare:
    python main.py "Scrie o funcție care validează un CNP românesc"
    python main.py                  # cere task-ul de la tastatură
    python main.py --resume         # continuă ULTIMA rulare întreruptă
    python main.py --resume a1b2c3  # continuă rularea cu acest id

Bucla principală:
    1. rulăm graful până se termină SAU până un nod cere input (`interrupt`);
    2. dacă s-a oprit pentru input, afișăm întrebarea și citim răspunsul;
    3. reluăm graful cu `Command(resume=raspuns)` și repetăm.

Starea e salvată pe disc după fiecare nod (vezi persistence.py), deci la un
crash poți relua cu `--resume` fără să pierzi pașii deja făcuți.
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

# Câți pași poate face graful într-o singură rulare (între două întrebări).
# Implicit LangGraph permite 25; buclele de cod pot depăși ușor limita.
RECURSION_LIMIT = 150

# Linia care încheie un răspuns pe mai multe rânduri (ex: cod lipit).
END_OF_INPUT = "END"


def main() -> None:
    args = parse_args()
    show_llm_retries()

    # Checkpointer pe disc: starea e salvată după FIECARE nod (vezi persistence.py).
    app = build_graph(checkpointer=open_checkpointer())

    if args.resume is None:  # rulare nouă
        thread_id = new_thread_id()
        print_thread_id(thread_id)
        graph_input = initial_state(" ".join(args.task) or input("Descrie task-ul: ").strip())
    else:  # reluare: din id-ul dat sau din ultima rulare
        thread_id = args.resume or last_thread_id() or sys.exit("Nu există nicio rulare de reluat.")
        print_thread_id(thread_id)
        graph_input = resume_input(app, make_config(thread_id))

    try:
        final_state = run_agent(app, make_config(thread_id), graph_input)
    except AllModelsExhaustedError as error:
        # Mesaj clar în loc de traceback: nu e un bug, ci limita contului Groq.
        sys.exit(f"\n✖ {error}\nStarea e salvată; continui mai târziu cu: python main.py --resume")

    print("\n" + "=" * 70)
    print(final_state["final_report"])


def parse_args() -> argparse.Namespace:
    """Argumentele din linia de comandă: task-ul SAU `--resume [id]`."""
    parser = argparse.ArgumentParser(description="Agent asistent de cod cu auto-corecție.")
    parser.add_argument("task", nargs="*", help="cerința (dacă lipsește, e cerută de la tastatură)")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",  # `--resume` fără valoare -> "" -> ultima rulare
        metavar="ID",
        help="continuă o rulare întreruptă (implicit: ultima)",
    )
    return parser.parse_args()


def print_thread_id(thread_id: str) -> None:
    """Afișează id-ul rulării, ca utilizatorul să știe cum o poate relua."""
    print(f"(id rulare: {thread_id} - dacă se oprește, continui cu: python main.py --resume)")


def make_config(thread_id: str) -> dict:
    """Configurația LangGraph: `thread_id` alege rularea din checkpointer."""
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT}


def show_llm_retries() -> None:
    """Afișează mesajele clientului Groq când reîncearcă un request.

    Fără asta, la rate limit (429) agentul pare "înghețat" cât timp așteaptă.
    """
    logging.basicConfig(format="  ⚠ %(message)s")
    logging.getLogger("groq._base_client").setLevel(logging.INFO)


def resume_input(app, config: dict):
    """Ce îi dăm grafului ca să continue o rulare salvată.

    - rularea s-a oprit la o ÎNTREBARE -> o punem din nou și trimitem răspunsul;
    - s-a oprit din alt motiv (crash) -> `None` = "continuă de la ultimul checkpoint"
      (nodul care a crăpat e rulat din nou, cele dinaintea lui nu).
    """
    snapshot = app.get_state(config)
    if not snapshot.values:
        sys.exit(f"Rularea '{config['configurable']['thread_id']}' nu există în {SETTINGS.checkpoint_db}.")

    print(f"Reiau rularea; următorul pas: {', '.join(snapshot.next) or '(rularea e deja terminată)'}")
    if snapshot.interrupts:
        return Command(resume=ask_in_terminal(snapshot.interrupts[0].value))
    return None


def run_agent(app, config: dict, graph_input) -> dict:
    """Rulează graful cap-coadă, răspunzând la toate întrebările lui.

    `graph_input` e starea inițială (rulare nouă), `None` sau un `Command` (reluare).
    """
    while True:
        prompt = run_until_interrupt(app, graph_input, config)
        if prompt is None:  # graful a ajuns la END
            break
        graph_input = Command(resume=ask_in_terminal(prompt))

    return app.get_state(config).values


def run_until_interrupt(app, graph_input, config) -> UserPrompt | None:
    """Rulează graful până la final sau până la primul `interrupt()`.

    Întoarce întrebarea (payload-ul interrupt-ului) sau `None` dacă graful s-a terminat.
    """
    for update in app.stream(graph_input, config, stream_mode="updates"):
        # Când un nod apelează interrupt(), stream-ul emite cheia specială "__interrupt__".
        if "__interrupt__" in update:
            return update["__interrupt__"][0].value
    return None


def ask_in_terminal(prompt: UserPrompt) -> str:
    """Afișează o întrebare a agentului și citește răspunsul utilizatorului."""
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
    """Șterge ce s-a tastat cât timp agentul lucra.

    Altfel, textul scris "în avans" (ex: un "ok" apăsat cât rula LLM-ul) ar fi
    luat drept răspuns la URMĂTOAREA întrebare, fără ca utilizatorul s-o vadă.
    """
    if sys.stdin.isatty():
        termios.tcflush(sys.stdin, termios.TCIFLUSH)


def read_multiline() -> str:
    """Citește mai multe rânduri până la o linie `END` (sau Ctrl+D)."""
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
