import sqlite3
from typing import List, Dict, Any

DB_PATH = "hermes_memory.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(session_id: str, role: str, content: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (session_id, role, content)
        VALUES (?, ?, ?)
    ''', (session_id, role, str(content)))
    conn.commit()
    conn.close()

def get_history(session_id: str, limit: int = 10) -> List[Dict[str, str]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, content FROM (
            SELECT id, role, content FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
    ''', (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def clear_history(session_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_history WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
