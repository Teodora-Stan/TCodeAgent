"""
Nodurile grafului, câte unul pe fișier. Re-exportate aici ca graph.py să le
poată importa dintr-un singur loc: `from nodes import node_clarify_task, ...`.
"""

from nodes.ask_corner_cases import node_ask_corner_cases
from nodes.clarify_task import node_clarify_task
from nodes.confirm_test_fix import node_confirm_test_fix
from nodes.diagnose_failure import node_diagnose_failure
from nodes.execute_tests import node_execute_tests
from nodes.final_report import node_final_report
from nodes.generate_tests import node_generate_tests
from nodes.implement_code import node_implement_code
from nodes.judge_code import node_judge_code
from nodes.judge_tests import node_judge_tests
from nodes.repair_tests import node_repair_tests
from nodes.user_confirm import node_user_confirm
from nodes.user_manual_tests import node_user_manual_tests

__all__ = [
    "node_ask_corner_cases",
    "node_clarify_task",
    "node_confirm_test_fix",
    "node_diagnose_failure",
    "node_execute_tests",
    "node_final_report",
    "node_generate_tests",
    "node_implement_code",
    "node_judge_code",
    "node_judge_tests",
    "node_repair_tests",
    "node_user_confirm",
    "node_user_manual_tests",
]
