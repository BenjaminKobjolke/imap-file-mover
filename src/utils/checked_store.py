"""
SQLite store of message UIDs that were already checked against the filters.
Lets unread-but-unmatched messages be skipped on later cycles instead of refetched.
"""
import sqlite3
from datetime import datetime
from typing import Iterable, List


class CheckedStore:
    """Remembers checked UIDs per account, folder and UIDVALIDITY."""

    def __init__(self, path: str = "checked_messages.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS checked ("
            "account TEXT, folder TEXT, uidvalidity INTEGER, uid INTEGER, checked_at TEXT, "
            "PRIMARY KEY (account, folder, uidvalidity, uid))"
        )
        self.conn.commit()

    def filter_new(self, account: str, folder: str, uidvalidity: int, uids: Iterable[int]) -> List[int]:
        """Return the UIDs that have not been checked yet."""
        seen = {row[0] for row in self.conn.execute(
            "SELECT uid FROM checked WHERE account = ? AND folder = ? AND uidvalidity = ?",
            (account, folder, uidvalidity),
        )}
        return [uid for uid in uids if uid not in seen]

    def add(self, account: str, folder: str, uidvalidity: int, uid: int) -> None:
        """Record a UID as checked."""
        self.conn.execute(
            "INSERT OR IGNORE INTO checked VALUES (?, ?, ?, ?, ?)",
            (account, folder, uidvalidity, uid, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()


if __name__ == "__main__":
    store = CheckedStore(":memory:")
    assert store.filter_new("a", "INBOX", 1, [1, 2, 3]) == [1, 2, 3]
    store.add("a", "INBOX", 1, 2)
    store.add("a", "INBOX", 1, 2)  # duplicate is ignored
    assert store.filter_new("a", "INBOX", 1, [1, 2, 3]) == [1, 3]
    assert store.filter_new("b", "INBOX", 1, [2]) == [2]  # other account
    assert store.filter_new("a", "INBOX", 2, [2]) == [2]  # UIDVALIDITY changed
    print("checked_store OK")
