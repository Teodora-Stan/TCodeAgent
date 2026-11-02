"""
Salvarea stării pe disc, ca o rulare întreruptă (crash, Ctrl+C, cotă LLM
epuizată) să poată fi RELUATĂ de unde a rămas.

Cum funcționează:
  - LangGraph salvează automat starea în checkpointer după FIECARE nod.
  - Folosim `SqliteSaver`, care scrie într-un fișier SQLite (`checkpoints.sqlite`),
    deci starea supraviețuiește închiderii programului (spre deosebire de
    `InMemorySaver`, care o ține doar în RAM).
  - Fiecare rulare are un `thread_id`. Îl salvăm și în `.last_thread`, ca
    `python main.py --resume` să știe ce rulare să continue fără să-l scrii tu.
"""

import sqlite3
import uuid
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from config import SETTINGS

# Fișierul în care ținem minte ultima rulare (lângă baza de date).
LAST_THREAD_FILE = SETTINGS.checkpoint_db.with_name(".last_thread")


def open_checkpointer(db_path: Path = SETTINGS.checkpoint_db) -> SqliteSaver:
    """Deschide (sau creează) baza SQLite cu checkpoint-uri.

    `check_same_thread=False`: LangGraph poate rula nodurile pe alte fire de
    execuție decât cel care a deschis conexiunea.
    """
    connection = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(connection)


def new_thread_id() -> str:
    """Un identificator nou de rulare, salvat imediat ca "ultima rulare"."""
    thread_id = uuid.uuid4().hex[:8]  # scurt, ca să poată fi tastat ușor
    LAST_THREAD_FILE.write_text(thread_id, encoding="utf-8")
    return thread_id


def last_thread_id() -> str | None:
    """Identificatorul ultimei rulări pornite, sau `None` dacă nu există."""
    if not LAST_THREAD_FILE.exists():
        return None
    return LAST_THREAD_FILE.read_text(encoding="utf-8").strip() or None
