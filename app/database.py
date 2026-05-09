import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "fluent_agent.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vocabulary (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word        TEXT    NOT NULL,
            translation TEXT    NOT NULL,
            context     TEXT    DEFAULT '',
            source      TEXT    DEFAULT '',
            mastery     INTEGER DEFAULT 0 CHECK(mastery >= 0 AND mastery <= 5),
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_word(
    word: str,
    translation: str,
    context: str = "",
    source: str = "",
    mastery: int = 0,
) -> int:
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        """
        INSERT INTO vocabulary (word, translation, context, source, mastery, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (word, translation, context, source, mastery, now, now),
    )
    conn.commit()
    word_id = cursor.lastrowid
    conn.close()
    return word_id


def get_all_words() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vocabulary ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_word_by_id(word_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM vocabulary WHERE id = ?", (word_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_mastery(word_id: int, mastery: int) -> bool:
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE vocabulary SET mastery = ?, updated_at = ? WHERE id = ?",
        (mastery, now, word_id),
    )
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


def delete_word(word_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM vocabulary WHERE id = ?", (word_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0


def search_words(keyword: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM vocabulary
        WHERE word LIKE ? OR translation LIKE ? OR context LIKE ?
        ORDER BY created_at DESC
        """,
        (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
