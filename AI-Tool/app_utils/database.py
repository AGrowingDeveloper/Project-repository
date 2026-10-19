"""SQLite 数据库操作模块"""
import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")

def get_conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _create_tables(conn)
    return conn

def _create_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT,
        model TEXT DEFAULT 'deepseek-chat',
        base_url TEXT DEFAULT 'https://api.deepseek.com',
        temperature REAL DEFAULT 0.7,
        max_tokens INTEGER DEFAULT 2048,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        assistant_name TEXT,
        character TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    """)
    conn.commit()
    _migrate(conn)

def _migrate(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if "assistant_name" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN assistant_name TEXT")
        conn.commit()

def create_user(username, password_hash):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                     (username, password_hash, datetime.now().isoformat()))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user["id"],))
        conn.commit()
        return dict(user)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_settings(user_id):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_settings(user_id, **kwargs):
    conn = get_conn()
    try:
        sets = ",".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        conn.execute(f"UPDATE user_settings SET {sets} WHERE user_id = ?", values)
        conn.commit()
    finally:
        conn.close()

def create_session(user_id, name, assistant_name="", character=""):
    conn = get_conn()
    now = datetime.now().isoformat()
    try:
        cur = conn.execute("INSERT INTO sessions (user_id, name, assistant_name, character, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                           (user_id, name, assistant_name, character, now, now))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def list_sessions(user_id):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_session(session_id):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def delete_session(session_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

def add_message(session_id, role, content):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                     (session_id, role, content, datetime.now().isoformat()))
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), session_id))
        conn.commit()
    finally:
        conn.close()

def list_messages(session_id):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_stats(user_id):
    conn = get_conn()
    try:
        session_count = conn.execute("SELECT COUNT(*) as c FROM sessions WHERE user_id = ?", (user_id,)).fetchone()["c"]
        message_count = conn.execute("SELECT COUNT(*) as c FROM messages m JOIN sessions s ON m.session_id = s.id WHERE s.user_id = ?", (user_id,)).fetchone()["c"]
        return {"sessions": session_count, "messages": message_count}
    finally:
        conn.close()
