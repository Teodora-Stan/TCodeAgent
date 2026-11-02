"""
Saving the state to disk, so an interrupted run (crash, Ctrl+C, exhausted LLM
quota) can be RESUMED where it left off.

How it works:
  - LangGraph automatically saves the state in the checkpointer after EVERY node.
  - We use `SqliteSaver`, which writes to an SQLite file (`checkpoints.sqlite`),
    so the state survives the program exiting (unlike `InMemorySaver`, which
    keeps it only in RAM).
  - Each run has a `thread_id`. We also save it in `.last_thread`, so that
    `python main.py --resume` knows which run to continue without you typing it.
"""

import sqlite3
import uuid
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from config import SETTINGS

# The file where we remember the last run (next to the database).
LAST_THREAD_FILE = SETTINGS.checkpoint_db.with_name(".last_thread")


def open_checkpointer(db_path: Path = SETTINGS.checkpoint_db) -> SqliteSaver:
    """Opens (or creates) the SQLite checkpoint database.

    `check_same_thread=False`: LangGraph may run the nodes on threads other
    than the one that opened the connection.
    """
    connection = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(connection)


def new_thread_id() -> str:
    """A new run identifier, immediately saved as the "last run"."""
    thread_id = uuid.uuid4().hex[:8]  # short, so it's easy to type
    LAST_THREAD_FILE.write_text(thread_id, encoding="utf-8")
    return thread_id


def last_thread_id() -> str | None:
    """The identifier of the last started run, or `None` if there isn't one."""
    if not LAST_THREAD_FILE.exists():
        return None
    return LAST_THREAD_FILE.read_text(encoding="utf-8").strip() or None
