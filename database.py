"""SQLite database for ZebraTur internal data (customers, quotes, orders cache, audit)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterable

import config

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db():
    with _lock:
        conn = _connect()
        try:
            yield conn
        finally:
            conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    birth_date TEXT,
    nationality TEXT,
    idn TEXT,
    telephone TEXT,
    email TEXT,
    passport_nr TEXT,
    passport_expiry TEXT,
    notes TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(surname, name);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(telephone);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shs_order_id TEXT UNIQUE,
    type TEXT,
    status TEXT,
    status_id INTEGER,
    customer_main TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    pax_count INTEGER,
    departure_date TEXT,
    return_date TEXT,
    destination TEXT,
    hotel_name TEXT,
    meal TEXT,
    room_type TEXT,
    nights INTEGER,
    net_amount REAL,
    gross_amount REAL,
    sale_amount REAL,
    currency TEXT,
    markup_percent REAL,
    agent TEXT,
    payload TEXT,
    last_synced_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_departure ON orders(departure_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_main);

CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    customer_main TEXT,
    customer_phone TEXT,
    title TEXT,
    summary TEXT,
    options TEXT,         -- JSON of search options offered
    status TEXT DEFAULT 'open', -- open, sent, won, lost
    sale_amount REAL,
    currency TEXT,
    agent TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);

CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,         -- package, hotel, transport, excursion, transfer
    params TEXT NOT NULL,
    pinned INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_used_at INTEGER
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    direction TEXT,            -- out, in
    text TEXT,
    shs_message_id TEXT,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_order ON messages(order_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    action TEXT,
    target TEXT,
    details TEXT,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER
);
"""


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)


def now() -> int:
    return int(time.time())


# -------------------- helpers --------------------

def insert(table: str, data: dict) -> int:
    data = {k: v for k, v in data.items() if k is not None}
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    with db() as conn:
        cur = conn.execute(sql, list(data.values()))
        return cur.lastrowid


def update(table: str, row_id: int, data: dict) -> None:
    if not data:
        return
    sets = ", ".join(f"{k}=?" for k in data.keys())
    sql = f"UPDATE {table} SET {sets} WHERE id=?"
    with db() as conn:
        conn.execute(sql, list(data.values()) + [row_id])


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute(query, list(params)).fetchall()]


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict | None:
    with db() as conn:
        row = conn.execute(query, list(params)).fetchone()
        return dict(row) if row else None


def delete(table: str, row_id: int) -> None:
    with db() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


# -------------------- customers --------------------

def create_customer(payload: dict) -> int:
    ts = now()
    payload = {**payload, "created_at": ts, "updated_at": ts}
    return insert("customers", payload)


def list_customers(q: str | None = None, limit: int = 200) -> list[dict]:
    if q:
        like = f"%{q.strip()}%"
        return fetch_all(
            "SELECT * FROM customers WHERE name LIKE ? OR surname LIKE ? OR telephone LIKE ? OR email LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (like, like, like, like, limit),
        )
    return fetch_all("SELECT * FROM customers ORDER BY updated_at DESC LIMIT ?", (limit,))


def get_customer(cid: int) -> dict | None:
    return fetch_one("SELECT * FROM customers WHERE id=?", (cid,))


def update_customer(cid: int, payload: dict) -> None:
    payload = {**payload, "updated_at": now()}
    update("customers", cid, payload)


def delete_customer(cid: int) -> None:
    delete("customers", cid)


# -------------------- orders --------------------

def upsert_order(payload: dict) -> int:
    ts = now()
    shs_id = payload.get("shs_order_id")
    if shs_id:
        existing = fetch_one("SELECT id FROM orders WHERE shs_order_id=?", (shs_id,))
        if existing:
            payload = {**payload, "updated_at": ts, "last_synced_at": ts}
            update("orders", existing["id"], payload)
            return existing["id"]
    payload = {**payload, "created_at": ts, "updated_at": ts, "last_synced_at": ts}
    return insert("orders", payload)


def list_orders(*, status: str | None = None, q: str | None = None,
                date_from: str | None = None, date_to: str | None = None,
                limit: int = 500) -> list[dict]:
    where = []
    params: list[Any] = []
    if status:
        where.append("status = ?"); params.append(status)
    if q:
        like = f"%{q.strip()}%"
        where.append("(shs_order_id LIKE ? OR customer_main LIKE ? OR customer_phone LIKE ? OR hotel_name LIKE ? OR destination LIKE ?)")
        params.extend([like] * 5)
    if date_from:
        where.append("departure_date >= ?"); params.append(date_from)
    if date_to:
        where.append("departure_date <= ?"); params.append(date_to)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    return fetch_all(f"SELECT * FROM orders {where_sql} ORDER BY updated_at DESC LIMIT ?", params)


def get_order(order_id: int) -> dict | None:
    return fetch_one("SELECT * FROM orders WHERE id=?", (order_id,))


def get_order_by_shs(shs_id: str) -> dict | None:
    return fetch_one("SELECT * FROM orders WHERE shs_order_id=?", (str(shs_id),))


# -------------------- quotes --------------------

def create_quote(payload: dict) -> int:
    ts = now()
    payload = {**payload, "created_at": ts, "updated_at": ts}
    if isinstance(payload.get("options"), (list, dict)):
        payload["options"] = json.dumps(payload["options"], ensure_ascii=False)
    return insert("quotes", payload)


def list_quotes(status: str | None = None, limit: int = 200) -> list[dict]:
    if status:
        return fetch_all("SELECT * FROM quotes WHERE status=? ORDER BY updated_at DESC LIMIT ?",
                         (status, limit))
    return fetch_all("SELECT * FROM quotes ORDER BY updated_at DESC LIMIT ?", (limit,))


def get_quote(qid: int) -> dict | None:
    q = fetch_one("SELECT * FROM quotes WHERE id=?", (qid,))
    if q and q.get("options"):
        try:
            q["options"] = json.loads(q["options"])
        except Exception:
            pass
    return q


def update_quote(qid: int, payload: dict) -> None:
    payload = {**payload, "updated_at": now()}
    if isinstance(payload.get("options"), (list, dict)):
        payload["options"] = json.dumps(payload["options"], ensure_ascii=False)
    update("quotes", qid, payload)


# -------------------- saved searches --------------------

def save_search(name: str, kind: str, params: dict) -> int:
    ts = now()
    return insert("saved_searches", {
        "name": name, "kind": kind,
        "params": json.dumps(params, ensure_ascii=False),
        "created_at": ts, "last_used_at": ts,
    })


def list_saved_searches(kind: str | None = None) -> list[dict]:
    if kind:
        rows = fetch_all("SELECT * FROM saved_searches WHERE kind=? ORDER BY pinned DESC, last_used_at DESC", (kind,))
    else:
        rows = fetch_all("SELECT * FROM saved_searches ORDER BY pinned DESC, last_used_at DESC")
    for r in rows:
        try:
            r["params"] = json.loads(r["params"])
        except Exception:
            pass
    return rows


# -------------------- messages --------------------

def log_message(order_id: str, direction: str, text: str, shs_message_id: str | None = None) -> int:
    return insert("messages", {
        "order_id": str(order_id),
        "direction": direction,
        "text": text,
        "shs_message_id": shs_message_id,
        "created_at": now(),
    })


def list_messages(order_id: str | None = None) -> list[dict]:
    if order_id:
        return fetch_all("SELECT * FROM messages WHERE order_id=? ORDER BY created_at DESC",
                         (str(order_id),))
    return fetch_all("SELECT * FROM messages ORDER BY created_at DESC LIMIT 500")


# -------------------- audit --------------------

def audit(actor: str, action: str, target: str = "", details: Any = "") -> None:
    if not isinstance(details, str):
        details = json.dumps(details, ensure_ascii=False)[:4000]
    insert("audit_log", {
        "actor": actor, "action": action, "target": target,
        "details": details, "created_at": now(),
    })


# -------------------- settings --------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    row = fetch_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    ts = now()
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, ts),
        )


# -------------------- stats --------------------

def order_stats(date_from: str | None = None, date_to: str | None = None) -> dict:
    where, params = [], []
    if date_from:
        where.append("created_at >= ?"); params.append(int(time.mktime(time.strptime(date_from, "%Y-%m-%d"))))
    if date_to:
        where.append("created_at <= ?"); params.append(int(time.mktime(time.strptime(date_to, "%Y-%m-%d"))) + 86400)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = fetch_all(f"""
        SELECT status, COUNT(*) as cnt, COALESCE(SUM(sale_amount),0) as revenue
        FROM orders {where_sql} GROUP BY status
    """, params)
    return {"by_status": rows}
