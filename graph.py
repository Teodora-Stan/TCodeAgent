"""
Construirea grafului LangGraph: noduri + muchii.

Diagrama fluxului:

    START
      │
      ▼
    clarify_task ──► user_confirm ──(nu e ok)──► clarify_task
                          │ ok
                          ▼
    generate_tests ──(prima dată)──► ask_corner_cases ──(are idei)──► generate_tests
          │ (regenerare)                    │ (nimic)
          ▼                                 ▼
    judge_tests ◄───────────────────────────┘
          │ respins (< max)  ──► generate_tests
          │ respins (= max)  ──► user_manual_tests ──► implement_code
          │ aprobat
          ▼
    implement_code ──► execute_tests ──(picat, blocat)──► final_report
          ▲                  │   │
          │                  │   └─(picat, eroare de import / timeout)──► implement_code
          │                  │ picat (teste reale)
          │                  ▼
          │           diagnose_failure ──(vina e a codului)──► implement_code
          │                  │ test suspectat ca greșit
          │                  ▼
          │           confirm_test_fix ──(user: "nu")──► implement_code
          │                  │ user: "da"
          │                  ▼
          │           repair_tests ──► execute_tests (același cod, teste corectate)
          │
          │           execute_tests ──(verde)──► judge_code
          └───(cere îmbunătățiri)──────────────────┘
                                                   │ aprobat / limită atinsă
                                                   ▼
                                             final_report ──► END
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

import nodes
import routers
from node_names import Node
from state import AgentState

# Asocierea nume nod -> funcție. Un dicționar e mai ușor de citit decât 10 apeluri add_node.
NODE_FUNCTIONS = {
    Node.CLARIFY_TASK: nodes.node_clarify_task,
    Node.USER_CONFIRM: nodes.node_user_confirm,
    Node.GENERATE_TESTS: nodes.node_generate_tests,
    Node.ASK_CORNER_CASES: nodes.node_ask_corner_cases,
    Node.JUDGE_TESTS: nodes.node_judge_tests,
    Node.USER_MANUAL_TESTS: nodes.node_user_manual_tests,
    Node.IMPLEMENT_CODE: nodes.node_implement_code,
    Node.EXECUTE_TESTS: nodes.node_execute_tests,
    Node.JUDGE_CODE: nodes.node_judge_code,
    Node.DIAGNOSE_FAILURE: nodes.node_diagnose_failure,
    Node.CONFIRM_TEST_FIX: nodes.node_confirm_test_fix,
    Node.REPAIR_TESTS: nodes.node_repair_tests,
    Node.FINAL_REPORT: nodes.node_final_report,
}

# Muchii fixe: după nodul din stânga urmează MEREU nodul din dreapta.
FIXED_EDGES = [
    (START, Node.CLARIFY_TASK),
    (Node.CLARIFY_TASK, Node.USER_CONFIRM),
    (Node.IMPLEMENT_CODE, Node.EXECUTE_TESTS),
    (Node.REPAIR_TESTS, Node.EXECUTE_TESTS),  # testele corectate se rulează pe același cod
    (Node.FINAL_REPORT, END),
]

# Muchii condiționate: după nodul din stânga, router-ul decide unde mergem.
# Lista din dreapta = destinațiile posibile (LangGraph le folosește la validare și la desenare).
CONDITIONAL_EDGES = [
    (Node.USER_CONFIRM, routers.route_after_confirm, [Node.GENERATE_TESTS, Node.CLARIFY_TASK]),
    (Node.GENERATE_TESTS, routers.route_after_generate_tests, [Node.ASK_CORNER_CASES, Node.JUDGE_TESTS]),
    (Node.ASK_CORNER_CASES, routers.route_after_corner_cases, [Node.GENERATE_TESTS, Node.JUDGE_TESTS]),
    (
        Node.JUDGE_TESTS,
        routers.route_after_test_judge,
        [Node.IMPLEMENT_CODE, Node.USER_MANUAL_TESTS, Node.GENERATE_TESTS],
    ),
    (Node.USER_MANUAL_TESTS, routers.route_after_manual_tests, [Node.USER_MANUAL_TESTS, Node.IMPLEMENT_CODE]),
    (
        Node.EXECUTE_TESTS,
        routers.route_after_execution,
        [Node.JUDGE_CODE, Node.FINAL_REPORT, Node.DIAGNOSE_FAILURE, Node.IMPLEMENT_CODE],
    ),
    (Node.DIAGNOSE_FAILURE, routers.route_after_diagnosis, [Node.CONFIRM_TEST_FIX, Node.IMPLEMENT_CODE]),
    (Node.CONFIRM_TEST_FIX, routers.route_after_test_fix_confirm, [Node.REPAIR_TESTS, Node.IMPLEMENT_CODE]),
    (Node.JUDGE_CODE, routers.route_after_code_judge, [Node.FINAL_REPORT, Node.IMPLEMENT_CODE]),
]


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Construiește și compilează graful.

    Checkpointer-ul e OBLIGATORIU pentru `interrupt()`: acolo se salvează starea
    cât timp graful așteaptă răspunsul utilizatorului. main.py îi dă unul pe
    disc (SQLite, vezi persistence.py); fără argument se folosește unul în memorie
    (util în teste).
    """
    builder = StateGraph(AgentState)

    for name, function in NODE_FUNCTIONS.items():
        builder.add_node(name, function)

    for source, target in FIXED_EDGES:
        builder.add_edge(source, target)

    for source, router, destinations in CONDITIONAL_EDGES:
        builder.add_conditional_edges(source, router, destinations)

    return builder.compile(checkpointer=checkpointer or InMemorySaver())
