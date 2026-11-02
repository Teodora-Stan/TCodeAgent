"""
Building the LangGraph graph: nodes + edges.

Flow diagram:

    START
      │
      ▼
    clarify_task ──► user_confirm ──(not ok)──► clarify_task
                          │ ok
                          ▼
    generate_tests ──(first time)──► ask_corner_cases ──(has ideas)──► generate_tests
          │ (regeneration)                  │ (nothing)
          ▼                                 ▼
    judge_tests ◄───────────────────────────┘
          │ rejected (< max)  ──► generate_tests
          │ rejected (= max)  ──► user_manual_tests ──► implement_code
          │ approved
          ▼
    implement_code ──► execute_tests ──(failed, stuck)──► final_report
          ▲                  │   │
          │                  │   └─(failed, import error / timeout)──► implement_code
          │                  │ failed (real tests)
          │                  ▼
          │           diagnose_failure ──(the code is at fault)──► implement_code
          │                  │ test suspected to be wrong
          │                  ▼
          │           confirm_test_fix ──(user: "nu")──► implement_code
          │                  │ user: "da"
          │                  ▼
          │           repair_tests ──► execute_tests (same code, corrected tests)
          │
          │           execute_tests ──(green)──► judge_code
          └───(requests improvements)──────────────┘
                                                   │ approved / limit reached
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

# Node name -> function mapping. A dict is easier to read than 13 add_node calls.
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

# Fixed edges: the node on the left is ALWAYS followed by the node on the right.
FIXED_EDGES = [
    (START, Node.CLARIFY_TASK),
    (Node.CLARIFY_TASK, Node.USER_CONFIRM),
    (Node.IMPLEMENT_CODE, Node.EXECUTE_TESTS),
    (Node.REPAIR_TESTS, Node.EXECUTE_TESTS),  # the corrected tests run against the same code
    (Node.FINAL_REPORT, END),
]

# Conditional edges: after the node on the left, the router decides where to go.
# The list on the right = the possible destinations (LangGraph uses them for validation and drawing).
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
    """Builds and compiles the graph.

    The checkpointer is REQUIRED for `interrupt()`: that's where the state is saved
    while the graph waits for the user's answer. main.py passes an on-disk one
    (SQLite, see persistence.py); without an argument an in-memory one is used
    (useful in tests).
    """
    builder = StateGraph(AgentState)

    for name, function in NODE_FUNCTIONS.items():
        builder.add_node(name, function)

    for source, target in FIXED_EDGES:
        builder.add_edge(source, target)

    for source, router, destinations in CONDITIONAL_EDGES:
        builder.add_conditional_edges(source, router, destinations)

    return builder.compile(checkpointer=checkpointer or InMemorySaver())
