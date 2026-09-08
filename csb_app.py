#!/usr/bin/env python3
"""
CSB - Crusader Secret Bureau
Local desktop intelligence application.

This build focuses on reliable local persistence, visible attachments,
robust record saving, fresh Data Intake data, and detailed diagnostics.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import sqlite3
import subprocess
import tempfile
import traceback
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from typing import Any

import flet as ft
# Kein csb_debug_probe mehr – alle Debug-Aufrufe wurden entfernt.

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# ============================================================
# Paths / constants
# ============================================================

APP_DIR = Path(os.path.expanduser("~")) / ".csb"
APP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "csb_database.db"
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOG_DIR / f"csb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

GOLD = "#C9A227"
GOLD_LIGHT = "#E8D48B"
DARK_BG = "#0F1419"
CARD_BG = "#1A2332"
ACCENT = "#2A3F5F"
DANGER = "#C0392B"
SUCCESS = "#27AE60"
TEXT_LIGHT = "#E8E6E3"
MUTED = "#7F8A99"
PANEL_BG = "#101823"
FIELD_BG = "#0A0E14"

LOG = logging.getLogger("csb")
LOG.setLevel(logging.DEBUG)
_file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
LOG.addHandler(_file_handler)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def event(action: str, detail: str = "") -> None:
    LOG.info("%s%s", action, f" | {detail}" if detail else "")


def log_exception(context: str, exc: BaseException) -> None:
    LOG.error("%s | %s: %s", context, type(exc).__name__, exc)
    LOG.error("TRACEBACK | %s", traceback.format_exc())


def global_exception_handler(exc_type, exc_value, exc_tb) -> None:
    if exc_type is KeyboardInterrupt:
        return
    LOG.error("UNHANDLED_EXCEPTION | %s: %s", getattr(exc_type, "__name__", exc_type), exc_value)
    LOG.error("TRACEBACK | %s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))


import sys
sys.excepthook = global_exception_handler

event("APP_MODULE_LOADED", f"python={sys.version.split()[0]} | flet={getattr(ft, '__version__', 'unknown')}")


# ============================================================
# Cryptography
# ============================================================

def derive_key(passphrase: str, salt: bytes = b"CSB_STONEWORKS_SALT_2024") -> bytes:
    if not passphrase:
        raise ValueError("Passphrase cannot be empty.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_text(plain: str, passphrase: str) -> str:
    return Fernet(derive_key(passphrase)).encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str, passphrase: str) -> str:
    return Fernet(derive_key(passphrase)).decrypt(token.encode("utf-8")).decode("utf-8")


# ============================================================
# Database
# ============================================================

PERSON_FIELDS = {
    "name": "TEXT NOT NULL",
    "aliases": "TEXT",
    "minecraft_uuid": "TEXT",
    "discord_username": "TEXT",
    "discord_id": "TEXT",
    "status": "TEXT DEFAULT 'Active'",

    # Domestic Intelligence
    "domestic_rank_position": "TEXT",
    "domestic_organization_faction": "TEXT",
    "domestic_faction_role": "TEXT",
    "domestic_political_alignment": "TEXT",
    "domestic_home_base": "TEXT",
    "domestic_known_locations": "TEXT",
    "domestic_territory": "TEXT",
    "domestic_known_associates": "TEXT",
    "domestic_allies": "TEXT",
    "domestic_enemies": "TEXT",
    "domestic_known_assets": "TEXT",
    "domestic_known_alt_accounts": "TEXT",
    "domestic_last_seen": "TEXT",
    "domestic_activity_pattern": "TEXT",
    "domestic_communication_channels": "TEXT",
    "domestic_events_incidents": "TEXT",
    "domestic_operations": "TEXT",
    "domestic_influence_reach": "TEXT",
    "domestic_military_role": "TEXT",
    "domestic_economic_activity": "TEXT",
    "domestic_reputation": "TEXT",
    "domestic_source": "TEXT",
    "domestic_source_reliability": "TEXT",
    "domestic_threat_level": "TEXT",
    "domestic_intelligence_confidence": "TEXT",
    "domestic_tags": "TEXT",
    "domestic_notes": "TEXT",

    # External Intelligence
    "external_rank_position": "TEXT",
    "external_organization_faction": "TEXT",
    "external_faction_role": "TEXT",
    "external_political_alignment": "TEXT",
    "external_affiliations": "TEXT",
    "external_known_locations": "TEXT",
    "external_home_base": "TEXT",
    "external_contacts_associates": "TEXT",
    "external_allies_partners": "TEXT",
    "external_enemies_rivals": "TEXT",
    "external_known_assets": "TEXT",
    "external_alt_accounts": "TEXT",
    "external_activity_pattern": "TEXT",
    "external_communication_channels": "TEXT",
    "external_travel_visits": "TEXT",
    "external_diplomatic_political_activity": "TEXT",
    "external_military_activity": "TEXT",
    "external_economic_trade_activity": "TEXT",
    "external_operations": "TEXT",
    "external_influence_reach": "TEXT",
    "external_reputation": "TEXT",
    "external_source": "TEXT",
    "external_source_reliability": "TEXT",
    "external_threat_level": "TEXT",
    "external_intelligence_confidence": "TEXT",
    "external_tags": "TEXT",
    "external_notes": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}

ORG_FIELDS = {
    "name": "TEXT NOT NULL",
    "type": "TEXT",
    "nation": "TEXT",
    "leader": "TEXT",
    "leadership_structure": "TEXT",
    "headquarters": "TEXT",
    "territory": "TEXT",
    "discord_server": "TEXT",
    "public_contact": "TEXT",
    "member_count_estimate": "TEXT",
    "military_strength": "TEXT",
    "economic_strength": "TEXT",
    "diplomatic_status": "TEXT",
    "allies": "TEXT",
    "enemies": "TEXT",
    "affiliated_organizations": "TEXT",
    "active_interests": "TEXT",
    "known_operations": "TEXT",
    "threat_level": "TEXT",
    "source": "TEXT",
    "source_reliability": "TEXT",
    "intelligence_confidence": "TEXT",
    "tags": "TEXT",
    "notes": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}

OP_FIELDS = {
    "codename": "TEXT NOT NULL",
    "status": "TEXT DEFAULT 'Planned'",
    "priority": "TEXT",
    "classification": "TEXT",
    "phase": "TEXT",
    "objective": "TEXT",
    "handler": "TEXT",
    "involved_persons": "TEXT",
    "target_organizations": "TEXT",
    "target_location": "TEXT",
    "start_date": "TEXT",
    "end_date": "TEXT",
    "communication_channel": "TEXT",
    "discord_channel": "TEXT",
    "assets": "TEXT",
    "resources_needed": "TEXT",
    "cover_story": "TEXT",
    "risks": "TEXT",
    "success_criteria": "TEXT",
    "outcome": "TEXT",
    "source": "TEXT",
    "intelligence_confidence": "TEXT",
    "tags": "TEXT",
    "notes": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}

SCHEMAS = {
    "persons": PERSON_FIELDS,
    "organizations": ORG_FIELDS,
    "operations": OP_FIELDS,
}


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=FULL")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        # Fallback for environments where WAL is unavailable.
        conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str, schema: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column, declaration in schema.items():
        if column not in existing:
            # Only internal schema names reach this statement.
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
            event("DATABASE_SCHEMA_MIGRATION", f"table={table} | added={column}")


def init_db() -> None:
    event("DATABASE_INIT_STARTED", str(DB_PATH))
    conn = get_connection()
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {", ".join(f"{k} {v}" for k, v in PERSON_FIELDS.items())}
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {", ".join(f"{k} {v}" for k, v in ORG_FIELDS.items())}
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {", ".join(f"{k} {v}" for k, v in OP_FIELDS.items())}
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT,
                is_identification INTEGER NOT NULL DEFAULT 0,
                data BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        for table, schema in SCHEMAS.items():
            _ensure_columns(conn, table, schema)
        # One-time, non-destructive migration from the former unsplit person fields.
        legacy_map = {
            "rank": "domestic_rank_position",
            "organization": "domestic_organization_faction",
            "faction_role": "domestic_faction_role",
            "political_alignment": "domestic_political_alignment",
            "home_base": "domestic_home_base",
            "known_locations": "domestic_known_locations",
            "territory": "domestic_territory",
            "known_associates": "domestic_known_associates",
            "allies": "domestic_allies",
            "enemies": "domestic_enemies",
            "known_assets": "domestic_known_assets",
            "known_alt_accounts": "domestic_known_alt_accounts",
            "last_seen": "domestic_last_seen",
            "activity_pattern": "domestic_activity_pattern",
            "communication_channels": "domestic_communication_channels",
            "source": "domestic_source",
            "source_reliability": "domestic_source_reliability",
            "threat_level": "domestic_threat_level",
            "intelligence_confidence": "domestic_intelligence_confidence",
            "tags": "domestic_tags",
            "notes": "domestic_notes",
        }
        existing_person_columns = {row["name"] for row in conn.execute("PRAGMA table_info(persons)")}
        for legacy, target in legacy_map.items():
            if legacy in existing_person_columns and target in existing_person_columns:
                conn.execute(
                    f"UPDATE persons SET {target}=COALESCE(NULLIF({target}, ''), {legacy}) "
                    f"WHERE COALESCE({target}, '')='' AND COALESCE({legacy}, '')<>''"
                )
        event("DATABASE_PERSON_INTELLIGENCE_MIGRATION_COMPLETED")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_record ON attachments(table_name, record_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(lower(name))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(lower(name))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ops_codename ON operations(lower(codename))")
        conn.commit()
        event("DATABASE_INIT_COMPLETED", str(DB_PATH))
    except Exception as exc:
        conn.rollback()
        log_exception("DATABASE_INIT_FAILED", exc)
        raise
    finally:
        conn.close()


def export_database_copy(path: str) -> None:
    source = get_connection()
    try:
        target = sqlite3.connect(path, timeout=20)
        try:
            source.execute("PRAGMA wal_checkpoint(FULL)")
            source.backup(target)
            target.execute("PRAGMA integrity_check")
            target.commit()
        finally:
            target.close()
    finally:
        source.close()


def record_identity(table: str) -> str:
    return "codename" if table == "operations" else "name"


def fetch_record(table: str, record_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_records(table: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        order_col = "codename" if table == "operations" else "name"
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY lower({order_col}), id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_attachments(table: str, record_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM attachments WHERE table_name=? AND record_id=? "
            "ORDER BY is_identification DESC, id DESC",
            (table, record_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_attachment(table: str, record_id: int, path: str, identification: bool) -> None:
    source = Path(path)
    raw = source.read_bytes()
    mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    conn = get_connection()
    try:
        if identification:
            conn.execute(
                "UPDATE attachments SET is_identification=0 WHERE table_name=? AND record_id=?",
                (table, record_id),
            )
        conn.execute(
            "INSERT INTO attachments "
            "(table_name, record_id, filename, mime_type, is_identification, data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (table, record_id, source.name, mime, int(identification), raw, now_str()),
        )
        conn.commit()
        event(
            "ATTACHMENT_SAVE_SUCCESS",
            f"table={table} | record_id={record_id} | identification={identification}",
        )
    except Exception as exc:
        conn.rollback()
        log_exception("ATTACHMENT_SAVE_FAILED", exc)
        raise
    finally:
        conn.close()


def delete_attachment(attachment_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
        conn.commit()
        event("ATTACHMENT_DELETE_SUCCESS", f"attachment_id={attachment_id}")
    finally:
        conn.close()


def save_record(table: str, entry_id: int | None, values: dict[str, str]) -> int:
    schema = SCHEMAS[table]
    required = record_identity(table)
    identity_value = values.get(required, "").strip()
    if not identity_value:
        raise ValueError(f"{required.capitalize()} is required.")

    missing = set(values) - set(schema)
    if missing:
        raise ValueError(f"Database schema is missing: {', '.join(sorted(missing))}")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        timestamp = now_str()

        if entry_id is None:
            columns = list(values) + ["created_at", "updated_at"]
            placeholders = ",".join("?" for _ in columns)
            params = [values[c] for c in values] + [timestamp, timestamp]
            cur = conn.execute(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                params,
            )
            saved_id = int(cur.lastrowid)
            mode = "insert"
        else:
            exists = conn.execute(
                f"SELECT 1 FROM {table} WHERE id=?",
                (entry_id,),
            ).fetchone()
            if not exists:
                raise ValueError("The record no longer exists.")
            sets = ", ".join(f"{k}=?" for k in values)
            params = list(values.values()) + [timestamp, entry_id]
            conn.execute(
                f"UPDATE {table} SET {sets}, updated_at=? WHERE id=?",
                params,
            )
            saved_id = entry_id
            mode = "update"

        conn.commit()

        # Verify the committed row immediately. This catches failed writes
        # before the UI claims success.
        verify = conn.execute(
            f"SELECT * FROM {table} WHERE id=?",
            (saved_id,),
        ).fetchone()
        if verify is None:
            raise RuntimeError("The database commit completed but the saved record could not be reloaded.")

        event("RECORD_SAVE_SUCCESS", f"table={table} | mode={mode} | record_id={saved_id}")
        return saved_id

    except Exception as exc:
        conn.rollback()
        log_exception("RECORD_SAVE_FAILED", exc)
        raise
    finally:
        conn.close()


def delete_record(table: str, record_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (record_id,)).fetchone()
        if not exists:
            raise ValueError("The record no longer exists.")
        conn.execute("DELETE FROM attachments WHERE table_name=? AND record_id=?", (table, record_id))
        conn.execute(f"DELETE FROM {table} WHERE id=?", (record_id,))
        conn.commit()

        verify = conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (record_id,)).fetchone()
        if verify:
            raise RuntimeError("The record could not be deleted.")
        event("RECORD_DELETE_SUCCESS", f"table={table} | record_id={record_id}")
    except Exception as exc:
        conn.rollback()
        log_exception("RECORD_DELETE_FAILED", exc)
        raise
    finally:
        conn.close()


# ============================================================
# Entry import/export
# ============================================================

ENTRY_FORMAT = "csb-entry-v3"
DATABASE_FORMAT = "csb-database-v2"


def export_entry(table: str, record_id: int, path: str) -> None:
    row = fetch_record(table, record_id)
    if not row:
        raise ValueError("The record no longer exists.")
    attachments = fetch_attachments(table, record_id)
    payload = {
        "format": ENTRY_FORMAT,
        "table": table,
        "exported_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "entry": {k: v for k, v in row.items() if k not in {"id", "created_at", "updated_at"}},
        "attachments": [
            {
                "filename": a["filename"],
                "mime_type": a["mime_type"],
                "is_identification": bool(a["is_identification"]),
                "data_base64": base64.b64encode(a["data"]).decode("ascii"),
            }
            for a in attachments
        ],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    event("ENTRY_EXPORT_SUCCESS", f"table={table} | record_id={record_id}")


def import_entry(path: str) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("format") not in {"csb-entry-v1", "csb-entry-v2", ENTRY_FORMAT}:
        raise ValueError("Unsupported CSB entry file format.")
    table = payload.get("table")
    if table not in SCHEMAS:
        raise ValueError("Unsupported record type.")
    entry = payload.get("entry")
    if not isinstance(entry, dict):
        raise ValueError("The imported file does not contain a valid entry.")
    attachments = payload.get("attachments", [])
    if not isinstance(attachments, list):
        raise ValueError("The imported attachment list is invalid.")
    event("ENTRY_IMPORT_PARSED", f"table={table}")
    return table, entry, attachments


def write_imported_entry(table: str, entry: dict[str, Any], attachments: list[dict[str, Any]], replace_id: int | None) -> int:
    schema = SCHEMAS[table]
    required = record_identity(table)
    identity = str(entry.get(required, "")).strip()
    if not identity:
        raise ValueError(f"Imported record is missing required field: {required}.")

    clean = {k: ("" if entry.get(k) is None else str(entry.get(k))) for k in schema if k in entry}
    clean.setdefault(required, identity)

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        if replace_id is None:
            cols = list(clean) + ["created_at", "updated_at"]
            params = list(clean.values()) + [now_str(), now_str()]
            placeholders = ",".join("?" for _ in cols)
            cur = conn.execute(
                f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                params,
            )
            saved_id = int(cur.lastrowid)
        else:
            sets = ", ".join(f"{k}=?" for k in clean)
            params = list(clean.values()) + [now_str(), replace_id]
            conn.execute(
                f"UPDATE {table} SET {sets}, updated_at=? WHERE id=?",
                params,
            )
            conn.execute("DELETE FROM attachments WHERE table_name=? AND record_id=?", (table, replace_id))
            saved_id = replace_id

        for attachment in attachments:
            filename = str(attachment.get("filename") or "attachment")
            mime = str(
                attachment.get("mime_type")
                or mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            )
            raw = base64.b64decode(str(attachment.get("data_base64", "")), validate=True)
            conn.execute(
                "INSERT INTO attachments "
                "(table_name, record_id, filename, mime_type, is_identification, data, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    table,
                    saved_id,
                    filename,
                    mime,
                    int(bool(attachment.get("is_identification"))),
                    raw,
                    now_str(),
                ),
            )

        conn.commit()
        event("ENTRY_IMPORT_SUCCESS", f"table={table} | record_id={saved_id} | replaced={replace_id is not None}")
        return saved_id
    except Exception as exc:
        conn.rollback()
        log_exception("ENTRY_IMPORT_FAILED", exc)
        raise
    finally:
        conn.close()




# ============================================================
# Connection analysis
# ============================================================

CONNECTION_FIELD_RULES = {
    # field: (domestic_label, weight, minimum_similarity, mode)
    "rank_position": ("Rank / Position", 10, 0.92, "single"),
    "organization_faction": ("Organization / Faction", 30, 0.90, "single"),
    "faction_role": ("Faction Role", 15, 0.90, "single"),
    "political_alignment": ("Political Alignment", 12, 0.88, "single"),
    "home_base": ("Home Base", 16, 0.88, "single"),
    "known_locations": ("Known Locations", 18, 0.86, "multi"),
    "territory": ("Territory", 18, 0.86, "multi"),
    "known_associates": ("Known Associates", 28, 0.84, "multi"),
    "allies": ("Allies / Close Contacts", 24, 0.84, "multi"),
    "enemies": ("Enemies / Rivals", 20, 0.84, "multi"),
    "known_assets": ("Known Assets", 34, 0.84, "multi"),
    "known_alt_accounts": ("Known Alternate Accounts", 22, 0.88, "multi"),
    "activity_pattern": ("Activity Pattern", 12, 0.90, "single"),
    "communication_channels": ("Communication Channels", 24, 0.84, "multi"),
    "events_incidents": ("Events / Incidents", 14, 0.88, "multi"),
    "operations": ("Operations / Activities", 22, 0.84, "multi"),
    "influence_reach": ("Influence / Reach", 18, 0.86, "multi"),
    "military_role": ("Military Role", 15, 0.90, "single"),
    "economic_activity": ("Economic Activity", 14, 0.88, "multi"),
    "reputation": ("Reputation", 10, 0.90, "single"),
    "tags": ("Tags", 16, 0.82, "multi"),
    "source": ("Intelligence Source", 8, 0.92, "single"),
    "source_reliability": ("Source Reliability", 8, 0.92, "single"),
    "threat_level": ("Threat Level", 10, 0.94, "single"),
    "intelligence_confidence": ("Intelligence Confidence", 10, 0.94, "single"),
    # External-only fields use the same matching machinery.
    "affiliations": ("Affiliations / Foreign Organizations", 30, 0.88, "multi"),
    "contacts_associates": ("Contacts / Associates", 28, 0.84, "multi"),
    "allies_partners": ("Allies / Partners", 24, 0.84, "multi"),
    "enemies_rivals": ("Enemies / Rivals", 20, 0.84, "multi"),
    "alt_accounts": ("Alternate Accounts", 22, 0.88, "multi"),
    "travel_visits": ("Travel / Visits", 18, 0.86, "multi"),
    "diplomatic_political_activity": ("Diplomatic / Political Activity", 16, 0.88, "multi"),
    "military_activity": ("Military Activity", 18, 0.88, "multi"),
    "economic_trade_activity": ("Economic / Trade Activity", 16, 0.88, "multi"),
}

DOMAIN_FIELD_PREFIXES = {
    "Domestic": "domestic_",
    "External": "external_",
}


def normalize_for_match(value: str) -> str:
    """Normalize text for conservative identity-style matching."""
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[\W_]+", "", value, flags=re.UNICODE)
    return value


def split_match_values(value: str) -> list[str]:
    parts = re.split(r"[,;|\n]+", str(value or ""))
    return [part.strip() for part in parts if part.strip()]


def similarity_score(left: str, right: str) -> float:
    a_raw = str(left or "").strip()
    b_raw = str(right or "").strip()
    a = normalize_for_match(a_raw)
    b = normalize_for_match(b_raw)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # Conservative handling of numeric identifiers and numbered locations.
    # "Fort 1" vs "Fort 2" is normally not a typo, while "PlayerNmae" vs
    # "PlayerName" remains a high-confidence fuzzy match.
    digits_a = re.findall(r"\d+", a_raw)
    digits_b = re.findall(r"\d+", b_raw)
    if digits_a or digits_b:
        if bool(digits_a) != bool(digits_b):
            return min(SequenceMatcher(None, a, b).ratio(), 0.65)
        if digits_a != digits_b:
            base = SequenceMatcher(None, a, b).ratio()
            return min(base, 0.78)

    return SequenceMatcher(None, a, b).ratio()


def best_value_match(left: str, right: str, mode: str) -> tuple[float, str, str]:
    left_values = split_match_values(left) if mode == "multi" else [str(left or "").strip()]
    right_values = split_match_values(right) if mode == "multi" else [str(right or "").strip()]
    best = (0.0, "", "")
    for a in left_values:
        for b in right_values:
            score = similarity_score(a, b)
            if score > best[0]:
                best = (score, a, b)
    return best


def match_kind(score: float, left: str, right: str) -> str:
    if str(left).strip().casefold() == str(right).strip().casefold():
        return "Exact"
    if normalize_for_match(left) == normalize_for_match(right):
        return "Normalized"
    if score >= 0.95:
        return "Very likely typo"
    if score >= 0.90:
        return "Likely typo"
    return "Possible typo"


def shared_person_alias_evidence(first: dict, second: dict, domain: str) -> tuple[int, list[str]]:
    prefix = DOMAIN_FIELD_PREFIXES[domain]
    name_a = str(first.get("name") or "").strip()
    name_b = str(second.get("name") or "").strip()
    aliases_a = split_match_values(str(first.get("aliases") or ""))
    aliases_b = split_match_values(str(second.get("aliases") or ""))
    evidence: list[str] = []
    score = 0

    def mentions(candidate: str, pool: list[str]) -> bool:
        target = normalize_for_match(candidate)
        return bool(target) and any(target == normalize_for_match(x) or similarity_score(candidate, x) >= 0.96 for x in pool)

    # Use the correct field for the domain: "known_associates" for Domestic, "contacts_associates" for External
    assoc_field = "known_associates" if domain == "Domestic" else "contacts_associates"
    domestic_assoc = split_match_values(str(first.get(prefix + assoc_field) or ""))
    domestic_assoc_2 = split_match_values(str(second.get(prefix + assoc_field) or ""))

    if mentions(name_a, domestic_assoc_2) or mentions(name_b, domestic_assoc):
        score += 26
        evidence.append("Possible cross-reference through known associates")

    if any(mentions(name_a, aliases_b) for _ in [0]) or any(mentions(name_b, aliases_a) for _ in [0]):
        score += 18
        evidence.append("Alias matches another person's known alias")

    return score, evidence


def analyze_person_pair(first: dict, second: dict, domain: str = "Domestic", similarity_threshold: float = 0.88) -> dict[str, Any]:
    prefix = DOMAIN_FIELD_PREFIXES[domain]
    evidence = []
    score = 0
    for suffix, (label, weight, minimum, mode) in CONNECTION_FIELD_RULES.items():
        left_key = prefix + suffix
        right_key = prefix + suffix
        left = str(first.get(left_key) or "").strip()
        right = str(second.get(right_key) or "").strip()
        if not left or not right:
            continue
        similarity, left_value, right_value = best_value_match(left, right, mode)
        threshold = max(similarity_threshold, minimum)
        if similarity >= threshold:
            kind = match_kind(similarity, left_value, right_value)
            contribution = weight if similarity >= 0.999 else max(1, round(weight * similarity))
            score += contribution
            evidence.append({
                "field": label,
                "value_a": left_value,
                "value_b": right_value,
                "similarity": round(similarity * 100, 1),
                "kind": kind,
                "weight": contribution,
            })

    alias_score, alias_evidence = shared_person_alias_evidence(first, second, domain)
    score += alias_score
    for text in alias_evidence:
        evidence.append({
            "field": text,
            "value_a": "",
            "value_b": "",
            "similarity": 100.0,
            "kind": "Related",
            "weight": 18 if "Alias" in text else 26,
        })

    if not evidence:
        return {"score": 0, "strength": "None", "confidence": "Low", "evidence": []}

    score = min(100, score)

    if score >= 80:
        strength = "Critical"
    elif score >= 65:
        strength = "Strong"
    elif score >= 40:
        strength = "Moderate"
    elif score >= 20:
        strength = "Low"
    else:
        strength = "Weak"

    exact_count = sum(1 for item in evidence if item["kind"] in {"Exact", "Normalized"})
    typo_count = sum(1 for item in evidence if "typo" in item["kind"].lower())
    if exact_count >= 2 or (exact_count >= 1 and score >= 60):
        confidence = "High"
    elif typo_count >= 1 and exact_count == 0:
        confidence = "Medium"
    else:
        confidence = "Medium"

    return {
        "score": score,
        "strength": strength,
        "confidence": confidence,
        "evidence": evidence,
    }


def analyze_person_connections(persons: list[dict], similarity_threshold: float = 0.88, include_domains: tuple[str, ...] = ("Domestic", "External"), min_score: int = 20) -> list[dict]:
    results: list[dict] = []
    for index, first in enumerate(persons):
        for second in persons[index + 1:]:
            for domain in include_domains:
                result = analyze_person_pair(first, second, domain, similarity_threshold)
                if result["score"] >= min_score:
                    results.append({
                        "person_a": str(first.get("name") or "Unnamed"),
                        "person_b": str(second.get("name") or "Unnamed"),
                        "domain": domain,
                        **result,
                    })
    return sorted(results, key=lambda item: (-item["score"], item["person_a"].casefold(), item["person_b"].casefold(), item["domain"]))



# ============================================================
# Indirect network analysis
# ============================================================

def build_connection_graph(results: list[dict[str, Any]], min_score: int = 20) -> dict[str, list[dict[str, Any]]]:
    """Build an undirected graph from direct connection-analysis results."""
    graph: dict[str, list[dict[str, Any]]] = {}
    seen_edges: set[tuple[str, str, str]] = set()

    for result in results:
        if int(result.get("score", 0)) < min_score:
            continue
        a = str(result.get("person_a") or "")
        b = str(result.get("person_b") or "")
        domain = str(result.get("domain") or "")
        if not a or not b or a == b:
            continue

        edge_key = tuple(sorted((a, b))) + (domain,)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)

        edge = {
            "person_a": a,
            "person_b": b,
            "domain": domain,
            "score": int(result.get("score", 0)),
            "strength": str(result.get("strength", "Weak")),
            "confidence": str(result.get("confidence", "Low")),
            "evidence": list(result.get("evidence", [])),
        }
        graph.setdefault(a, []).append(edge)
        graph.setdefault(b, []).append(edge)

    return graph


def network_subgraph(
    results: list[dict[str, Any]],
    focus: str | None = None,
    max_hops: int = 2,
    min_score: int = 20,
) -> dict[str, Any]:
    """Return a focus-centered network subgraph, retaining edge metadata."""
    graph = build_connection_graph(results, min_score)
    if not graph:
        return {"nodes": [], "edges": [], "distances": {}}

    if focus and focus not in graph:
        return {"nodes": [], "edges": [], "distances": {}}

    if not focus:
        focus = max(graph, key=lambda node: len(graph[node]))

    max_hops = max(1, min(int(max_hops), 3))
    distances = {focus: 0}
    queue = [focus]

    while queue:
        current = queue.pop(0)
        current_distance = distances[current]
        if current_distance >= max_hops:
            continue
        for edge in graph.get(current, []):
            other = edge["person_b"] if edge["person_a"] == current else edge["person_a"]
            if other not in distances:
                distances[other] = current_distance + 1
                queue.append(other)

    nodes = sorted(distances, key=lambda n: (distances[n], n.casefold()))

    node_set = set(nodes)
    edges = []
    seen = set()
    for node in nodes:
        for edge in graph.get(node, []):
            a = edge["person_a"]
            b = edge["person_b"]
            if a not in node_set or b not in node_set:
                continue
            key = (min(a, b), max(a, b), edge["domain"])
            if key not in seen:
                seen.add(key)
                edges.append(edge)

    edges.sort(key=lambda e: (-int(e["score"]), e["person_a"].casefold(), e["person_b"].casefold()))
    return {"focus": focus, "nodes": nodes, "edges": edges, "distances": distances}


def find_network_path(
    results: list[dict[str, Any]],
    start: str,
    target: str,
    min_score: int = 20,
    max_hops: int = 4,
) -> dict[str, Any] | None:
    """Find the highest-scoring short path between two people."""
    graph = build_connection_graph(results, min_score)
    if start not in graph or target not in graph:
        return None

    queue = [(start, [start], [], 0)]
    best_depth: dict[str, int] = {start: 0}
    candidates = []

    while queue:
        current, nodes, edges, depth = queue.pop(0)
        if current == target:
            candidates.append((sum(int(e["score"]) for e in edges), nodes, edges))
            continue
        if depth >= max_hops:
            continue

        for edge in graph.get(current, []):
            other = edge["person_b"] if edge["person_a"] == current else edge["person_a"]
            if other in nodes:
                continue
            next_depth = depth + 1
            if next_depth > best_depth.get(other, 99):
                continue
            best_depth[other] = min(best_depth.get(other, 99), next_depth)
            queue.append((other, nodes + [other], edges + [edge], next_depth))

    if not candidates:
        return None

    score, nodes, edges = max(candidates, key=lambda item: (item[0], -len(item[1])))
    return {"nodes": nodes, "edges": edges, "score_sum": score}



# ============================================================
# UI
# ============================================================

def main(page: ft.Page):
    # Kein DBG mehr – alle Debug-Aufrufe wurden entfernt.
    event("APP_START", f"test={getattr(page, 'test', False)}")

    page.title = "CSB - Crusader Secret Bureau"
    page.window.width = 1280
    page.window.height = 860
    page.window.min_width = 1050
    page.window.min_height = 700
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = DARK_BG
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=GOLD, visual_density=ft.VisualDensity.COMPACT)

    # Native file services are used only for normal desktop operation.
    file_picker = None
    image_picker = None
    attachment_picker = None
    if not getattr(page, "test", False):
        file_picker = ft.FilePicker()
        image_picker = ft.FilePicker()
        attachment_picker = ft.FilePicker()
        page.services.append(file_picker)
        page.services.append(image_picker)
        page.services.append(attachment_picker)

    try:
        init_db()
    except Exception as exc:
        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    f"Database initialization failed.\n\n{type(exc).__name__}: {exc}\n\nSee:\n{LOG_PATH}",
                    color=TEXT_LIGHT,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )
        log_exception("APP_DATABASE_INIT_FATAL", exc)
        return

    selected_view = 0
    db_type = "persons"
    selected_record_id: int | None = None
    form_mode = "new"
    is_saving = False
    dirty = False

    # ---------- Common UI helpers ----------

    def notify(message: str, success: bool = True):
        event("UI_NOTIFICATION", "success" if success else "error")
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=TEXT_LIGHT),
            bgcolor=SUCCESS if success else DANGER,
            duration=2800,
        )
        page.snack_bar.open = True
        page.update()

    def mark_dirty(_=None):
        nonlocal dirty
        dirty = True

    def set_status(status_control: ft.Text, text: str, color=MUTED):
        status_control.value = text
        status_control.color = color

    def text_field(label: str, value: str = "", multiline: bool = False, key: str | None = None):
        kwargs = dict(
            label=label,
            value=value,
            border_color=GOLD,
            focused_border_color=GOLD_LIGHT,
            bgcolor=FIELD_BG,
            color=TEXT_LIGHT,
            label_style=ft.TextStyle(color=GOLD_LIGHT),
            on_change=mark_dirty,
        )
        if key:
            kwargs["key"] = key
        if multiline:
            kwargs.update(multiline=True, min_lines=3, max_lines=7)
        return ft.TextField(**kwargs)

    # ----------------------------------- [CRYPTO VIEW] ---------------------------------------------

    crypto_input = ft.TextField(
        label="Plain text / Cipher text",
        multiline=True,
        min_lines=8,
        max_lines=14,
        expand=True,
        border_color=GOLD,
        focused_border_color=GOLD_LIGHT,
        bgcolor=CARD_BG,
        color=TEXT_LIGHT,
    )
    crypto_pass = ft.TextField(
        label="Shared passphrase",
        password=True,
        can_reveal_password=True,
        width=420,
        border_color=GOLD,
        bgcolor=CARD_BG,
        color=TEXT_LIGHT,
    )
    crypto_output = ft.TextField(
        label="Result",
        multiline=True,
        min_lines=8,
        max_lines=14,
        expand=True,
        read_only=True,
        border_color=ACCENT,
        bgcolor=FIELD_BG,
        color=GOLD_LIGHT,
    )

    def do_encrypt(_):
        event("CRYPTO_ENCRYPT_CLICKED")
        try:
            if not (crypto_input.value or "").strip():
                raise ValueError("Please enter text.")
            crypto_output.value = encrypt_text(crypto_input.value.strip(), crypto_pass.value or "")
            page.update()
            event("CRYPTO_ENCRYPT_SUCCESS")
            notify("Encryption successful.")
        except Exception as exc:
            log_exception("CRYPTO_ENCRYPT_FAILED", exc)
            notify(f"Encryption failed: {exc}", False)

    def do_decrypt(_):
        event("CRYPTO_DECRYPT_CLICKED")
        try:
            if not (crypto_input.value or "").strip():
                raise ValueError("Please enter cipher text.")
            crypto_output.value = decrypt_text(crypto_input.value.strip(), crypto_pass.value or "")
            page.update()
            event("CRYPTO_DECRYPT_SUCCESS")
            notify("Decryption successful.")
        except InvalidToken:
            event("CRYPTO_DECRYPT_FAILED", "InvalidToken")
            notify("Decryption failed - wrong passphrase or invalid text.", False)
        except Exception as exc:
            log_exception("CRYPTO_DECRYPT_FAILED", exc)
            notify(f"Decryption failed: {exc}", False)

    def clear_crypto(_):
        crypto_input.value = ""
        crypto_output.value = ""
        page.update()

    crypto_view = ft.Container(
        expand=True,
        padding=30,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Row(
                    [ft.Icon(ft.Icons.LOCK, color=GOLD, size=28),
                     ft.Text("Encryption & Decryption", size=24, weight=ft.FontWeight.BOLD, color=GOLD)],
                    spacing=12,
                ),
                ft.Text(
                    "Use a shared passphrase. The application uses authenticated encryption for the message payload.",
                    size=13,
                    color=MUTED,
                ),
                crypto_pass,
                ft.Row([
                    ft.Button("Encrypt", icon=ft.Icons.LOCK_OUTLINE, bgcolor=GOLD, color=DARK_BG, on_click=do_encrypt),
                    ft.Button("Decrypt", icon=ft.Icons.LOCK_OPEN, bgcolor=ACCENT, color=TEXT_LIGHT, on_click=do_decrypt),
                    ft.TextButton("Clear", on_click=clear_crypto),
                ], spacing=10),
                ft.Row([
                    ft.Container(content=crypto_input, expand=True),
                    ft.Container(content=crypto_output, expand=True),
                ], expand=True, spacing=18),
            ],
        ),
    )

    # ----------------------------------- [DATABASE VIEW] ---------------------------------------------

    list_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
    form_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    db_toolbar_status = ft.Text("", size=12, color=MUTED)

    form_fields: dict[str, ft.TextField] = {}
    form_status = ft.Text("New record", size=12, color=MUTED)
    save_button_ref = {"control": None}

    multiline_keys = {
        "notes", "objective", "known_locations", "known_associates", "allies", "enemies",
        "known_assets", "known_alt_accounts", "communication_channels", "leadership_structure",
        "territory", "affiliated_organizations", "active_interests", "known_operations",
        "involved_persons", "target_organizations", "assets", "resources_needed", "risks",
        "success_criteria", "outcome",
        "domestic_known_locations", "domestic_territory", "domestic_known_associates",
        "domestic_allies", "domestic_enemies", "domestic_known_assets", "domestic_known_alt_accounts",
        "domestic_activity_pattern", "domestic_communication_channels", "domestic_events_incidents",
        "domestic_operations", "domestic_influence_reach", "domestic_military_role",
        "domestic_economic_activity", "domestic_reputation", "domestic_notes",
        "external_affiliations", "external_known_locations", "external_contacts_associates",
        "external_allies_partners", "external_enemies_rivals", "external_known_assets",
        "external_alt_accounts", "external_activity_pattern", "external_communication_channels",
        "external_travel_visits", "external_diplomatic_political_activity",
        "external_military_activity", "external_economic_trade_activity",
        "external_operations", "external_influence_reach", "external_reputation",
        "external_notes",
    }

    def table_title(table: str) -> str:
        return {
            "persons": "Person Intelligence Records",
            "organizations": "Organization Intelligence Records",
            "operations": "Operation Records",
        }[table]

    def table_fields(table: str) -> list[tuple[str, str, bool]]:
        if table == "persons":
            return [
                ("name", "Minecraft Username / Name *", True),
                ("aliases", "Aliases / Codenames", False),
                ("minecraft_uuid", "Minecraft UUID", False),
                ("discord_username", "Discord Username", False),
                ("discord_id", "Discord User ID", False),
                ("status", "Current Status", False),

                ("domestic_rank_position", "Rank / Position", False),
                ("domestic_organization_faction", "Organization / Faction", False),
                ("domestic_faction_role", "Faction Role", False),
                ("domestic_political_alignment", "Political Alignment", False),
                ("domestic_home_base", "Home Base / Main Base", False),
                ("domestic_known_locations", "Known Locations / Regions", False),
                ("domestic_territory", "Controlled / Claimed Territory", False),
                ("domestic_known_associates", "Known Associates", False),
                ("domestic_allies", "Allies / Close Contacts", False),
                ("domestic_enemies", "Enemies / Rivals", False),
                ("domestic_known_assets", "Known Assets", False),
                ("domestic_known_alt_accounts", "Known Alternate Accounts", False),
                ("domestic_last_seen", "Last Seen In-Game", False),
                ("domestic_activity_pattern", "Activity Pattern", False),
                ("domestic_communication_channels", "Communication Channels", False),
                ("domestic_events_incidents", "Known Domestic Events / Incidents", False),
                ("domestic_operations", "Known Domestic Operations / Activities", False),
                ("domestic_influence_reach", "Domestic Influence / Reach", False),
                ("domestic_military_role", "Domestic Military Role", False),
                ("domestic_economic_activity", "Domestic Economic Activity", False),
                ("domestic_reputation", "Domestic Reputation", False),
                ("domestic_source", "Intelligence Source", False),
                ("domestic_source_reliability", "Source Reliability", False),
                ("domestic_threat_level", "Domestic Threat Level", False),
                ("domestic_intelligence_confidence", "Domestic Intelligence Confidence", False),
                ("domestic_tags", "Domestic Tags (comma-separated)", False),
                ("domestic_notes", "Domestic Intelligence Notes", False),

                ("external_rank_position", "Rank / Position", False),
                ("external_organization_faction", "Organization / Faction", False),
                ("external_faction_role", "Faction Role", False),
                ("external_political_alignment", "Political Alignment", False),
                ("external_affiliations", "External Affiliations / Foreign Organizations", False),
                ("external_known_locations", "Known External Locations / Regions", False),
                ("external_home_base", "External Main Base / Residence", False),
                ("external_contacts_associates", "External Contacts / Associates", False),
                ("external_allies_partners", "External Allies / Partners", False),
                ("external_enemies_rivals", "External Enemies / Rivals", False),
                ("external_known_assets", "External Known Assets", False),
                ("external_alt_accounts", "External Alternate Accounts", False),
                ("external_activity_pattern", "External Activity Pattern", False),
                ("external_communication_channels", "External Communication Channels", False),
                ("external_travel_visits", "External Travel / Visits", False),
                ("external_diplomatic_political_activity", "Diplomatic / Political Activity", False),
                ("external_military_activity", "External Military Activity", False),
                ("external_economic_trade_activity", "External Economic / Trade Activity", False),
                ("external_operations", "External Operations / Activities", False),
                ("external_influence_reach", "External Influence / Reach", False),
                ("external_reputation", "External Reputation", False),
                ("external_source", "External Intelligence Source", False),
                ("external_source_reliability", "External Source Reliability", False),
                ("external_threat_level", "External Threat Level", False),
                ("external_intelligence_confidence", "External Intelligence Confidence", False),
                ("external_tags", "External Tags (comma-separated)", False),
                ("external_notes", "External Intelligence Notes", False),
            ]
        if table == "organizations":
            return [
                ("name", "Organization Name *", True),
                ("type", "Type", False),
                ("nation", "Nation / State", False),
                ("leader", "Leader / Head", False),
                ("leadership_structure", "Leadership Structure", False),
                ("headquarters", "Headquarters / Main Base", False),
                ("territory", "Controlled / Claimed Territory", False),
                ("discord_server", "Discord Server", False),
                ("public_contact", "Known Public Contact", False),
                ("member_count_estimate", "Estimated Member Count", False),
                ("military_strength", "Military Strength", False),
                ("economic_strength", "Economic Strength", False),
                ("diplomatic_status", "Diplomatic Status", False),
                ("allies", "Allies", False),
                ("enemies", "Enemies / Rivals", False),
                ("affiliated_organizations", "Affiliated Organizations", False),
                ("active_interests", "Known Interests / Goals", False),
                ("known_operations", "Known Operations / Activities", False),
                ("threat_level", "Threat Level", False),
                ("source", "Intelligence Source", False),
                ("source_reliability", "Source Reliability", False),
                ("intelligence_confidence", "Intelligence Confidence", False),
                ("tags", "Tags (comma-separated)", False),
                ("notes", "Notes", False),
            ]
        return [
            ("codename", "Codename *", True),
            ("status", "Status", False),
            ("priority", "Priority", False),
            ("classification", "Classification", False),
            ("phase", "Operation Phase", False),
            ("objective", "Objective", False),
            ("handler", "Handler / Responsible Officer", False),
            ("involved_persons", "Involved Persons", False),
            ("target_organizations", "Target Organizations", False),
            ("target_location", "Target Location / Region", False),
            ("start_date", "Start Date", False),
            ("end_date", "End Date", False),
            ("communication_channel", "Primary Communication Channel", False),
            ("discord_channel", "Discord Channel / Server", False),
            ("assets", "Assigned Assets", False),
            ("resources_needed", "Required Resources", False),
            ("cover_story", "Cover Story / Public Explanation", False),
            ("risks", "Known Risks", False),
            ("success_criteria", "Success Criteria", False),
            ("outcome", "Outcome / Result", False),
            ("source", "Intelligence Source", False),
            ("intelligence_confidence", "Intelligence Confidence", False),
            ("tags", "Tags (comma-separated)", False),
            ("notes", "Notes", False),
        ]

    def set_save_enabled(enabled: bool):
        button = save_button_ref["control"]
        if button is not None:
            button.disabled = not enabled

    def render_attachment_card(attachment: dict[str, Any], refresh_media):
        filename = attachment["filename"]
        mime = attachment["mime_type"] or "application/octet-stream"
        raw = attachment["data"]
        size_text = f"{len(raw) / 1024:.1f} KB"
        is_image = mime.startswith("image/")

        def save_temp_and_open(_):
            try:
                suffix = Path(filename).suffix
                tmp = Path(tempfile.gettempdir()) / f"csb_{attachment['id']}{suffix}"
                tmp.write_bytes(raw)
                os.startfile(str(tmp))  # Windows desktop target.
                event("ATTACHMENT_OPENED", f"attachment_id={attachment['id']}")
            except Exception as exc:
                log_exception("ATTACHMENT_OPEN_FAILED", exc)
                notify(f"Could not open attachment: {exc}", False)

        def remove_attachment(_):
            try:
                delete_attachment(int(attachment["id"]))
                refresh_media()
                notify("Attachment deleted.")
            except Exception as exc:
                log_exception("ATTACHMENT_DELETE_FAILED", exc)
                notify(f"Attachment deletion failed: {exc}", False)

        preview = ft.Container(
            width=66,
            height=66,
            bgcolor=FIELD_BG,
            border_radius=8,
            alignment=ft.Alignment.CENTER,
        )
        if is_image:
            encoded = base64.b64encode(raw).decode("ascii")
            preview.content = ft.Image(
                src=f"data:{mime};base64,{encoded}",
                width=60,
                height=60,
                fit="contain",
            )
        else:
            preview.content = ft.Icon(ft.Icons.ATTACH_FILE, color=GOLD, size=30)

        return ft.Container(
            bgcolor=CARD_BG,
            padding=8,
            border_radius=8,
            border=ft.border.Border.all(1, "#2A3545"),
            content=ft.Row([
                preview,
                ft.Column([
                    ft.Text(filename, size=13, color=TEXT_LIGHT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(("Identification image" if attachment["is_identification"] else "Attachment") + f" · {size_text}",
                            size=11, color=MUTED),
                ], expand=True, spacing=2),
                ft.Button("Open", on_click=save_temp_and_open),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=DANGER, tooltip="Delete", on_click=remove_attachment),
            ], spacing=8),
        )

    def build_media_panel(table: str, record_id: int):
        media_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        media_status = ft.Text("", size=11, color=MUTED)

        def refresh_media():
            media_column.controls.clear()
            attachments = fetch_attachments(table, record_id)
            identification = next((a for a in attachments if a["is_identification"]), None)
            other = [a for a in attachments if not a["is_identification"]]

            media_column.controls.append(
                ft.Text("Media & Attachments", size=15, weight=ft.FontWeight.BOLD, color=GOLD_LIGHT)
            )

            if identification:
                encoded = base64.b64encode(identification["data"]).decode("ascii")
                mime = identification["mime_type"] or "image/png"
                media_column.controls.append(
                    ft.Text("Identification Image", size=12, color=MUTED)
                )
                media_column.controls.append(
                    ft.Container(
                        width=320,
                        height=320,
                        bgcolor=FIELD_BG,
                        border_radius=10,
                        border=ft.border.Border.all(1, "#2A3545"),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Image(
                            src=f"data:{mime};base64,{encoded}",
                            width=300,
                            height=300,
                            fit="contain",
                        ),
                    )
                )
                media_status.value = f"Identification: {identification['filename']}"
            else:
                media_column.controls.append(
                    ft.Container(
                        width=320,
                        height=320,
                        bgcolor=FIELD_BG,
                        border_radius=10,
                        border=ft.border.Border.all(1, "#2A3545"),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column([
                            ft.Icon(ft.Icons.PERSON_OUTLINE, color="#5C6675", size=70),
                            ft.Text("No identification image", color=MUTED),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    )
                )
                media_status.value = "No identification image."

            media_column.controls.append(media_status)

            if other:
                media_column.controls.append(ft.Divider(color="#2A3545"))
                media_column.controls.append(
                    ft.Text(f"Attachments ({len(other)})", size=13, weight=ft.FontWeight.BOLD, color=GOLD_LIGHT)
                )
                for attachment in other:
                    media_column.controls.append(render_attachment_card(attachment, refresh_media))
            else:
                media_column.controls.append(ft.Text("No additional attachments.", size=12, color=MUTED))

            page.update()

        async def pick_identification(_):
            if image_picker is None:
                notify("File selection is available in normal desktop mode.", False)
                return
            try:
                event("IDENTIFICATION_PICKER_OPENED", f"table={table} | record_id={record_id}")
                files = await image_picker.pick_files(
                    dialog_title="Select Identification Image",
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                )
                if not files:
                    event("IDENTIFICATION_SELECTION_CANCELLED")
                    return
                path = files[0].path
                if not path:
                    raise ValueError("The selected file does not provide a local path.")
                save_attachment(table, record_id, path, True)
                refresh_media()
                notify("Identification image saved.")
            except Exception as exc:
                log_exception("IDENTIFICATION_IMAGE_FAILED", exc)
                notify(f"Identification image failed: {exc}", False)

        async def pick_attachments(_):
            if attachment_picker is None:
                notify("File selection is available in normal desktop mode.", False)
                return
            try:
                event("ATTACHMENT_PICKER_OPENED", f"table={table} | record_id={record_id}")
                files = await attachment_picker.pick_files(
                    dialog_title="Add Record Attachments",
                    allow_multiple=True,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["png", "jpg", "jpeg", "webp", "gif", "pdf", "txt", "json", "csv"],
                )
                if not files:
                    return
                count = 0
                for selected in files:
                    if selected.path:
                        save_attachment(table, record_id, selected.path, False)
                        count += 1
                refresh_media()
                notify(f"{count} attachment(s) saved.")
            except Exception as exc:
                log_exception("ATTACHMENTS_FAILED", exc)
                notify(f"Attachment error: {exc}", False)

        refresh_media()
        return ft.Column([
            media_column,
            ft.Row([
                ft.Button("Set Identification Image", icon=ft.Icons.IMAGE, on_click=pick_identification),
                ft.Button("Add Attachments", icon=ft.Icons.ATTACH_FILE, on_click=pick_attachments),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], expand=True)

    def load_list():
        event("RECORD_LIST_REFRESH", f"table={db_type}")
        list_column.controls.clear()
        rows = fetch_records(db_type)
        if not rows:
            list_column.controls.append(ft.Text("No entries yet.", color=MUTED, italic=True))
        else:
            for row in rows:
                identity = row["codename"] if db_type == "operations" else row["name"]
                subtitle_fields = ["domestic_rank_position", "domestic_organization_faction", "domestic_threat_level", "domestic_tags"] if db_type == "persons" else (
                    ["type", "nation", "threat_level", "tags"] if db_type == "organizations" else
                    ["status", "priority", "target_location", "tags"]
                )
                preview = "  ·  ".join(
                    str(row[f]) for f in subtitle_fields
                    if f in row and row[f]
                )

                def edit(_e, rid=row["id"]):
                    open_edit_form(rid)

                def remove(_e, rid=row["id"]):
                    confirm_delete(rid)

                list_column.controls.append(
                    ft.Container(
                        bgcolor=CARD_BG,
                        padding=10,
                        border_radius=8,
                        border=ft.border.Border.all(1, "#2A3545"),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(identity, size=15, color=GOLD_LIGHT, weight=ft.FontWeight.BOLD),
                                ft.Text(preview or "No summary available", size=11, color=MUTED,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ], expand=True, spacing=2),
                            ft.IconButton(icon=ft.Icons.EDIT, icon_color=GOLD, tooltip="Edit", on_click=edit),
                            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=DANGER, tooltip="Delete", on_click=remove),
                        ]),
                    )
                )
        page.update()

    def person_field_sections():
        fields = table_fields("persons")
        basic_keys = {"name", "aliases", "minecraft_uuid", "discord_username", "discord_id", "status"}
        domestic = [f for f in fields if f[0].startswith("domestic_")]
        external = [f for f in fields if f[0].startswith("external_")]
        basic = [f for f in fields if f[0] in basic_keys]
        return [
            ("Basic Information", basic),
            ("Domestic Intelligence", domestic),
            ("External Intelligence", external),
        ]

    def clear_form():
        nonlocal selected_record_id, form_mode, dirty
        selected_record_id = None
        form_mode = "new"
        dirty = False
        form_fields.clear()
        form_column.controls.clear()

        fields_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)
        if db_type == "persons":
            for section_title, section_fields in person_field_sections():
                fields_column.controls.append(
                    ft.Text(section_title, size=15, weight=ft.FontWeight.BOLD, color=GOLD)
                )
                for key, label, required in section_fields:
                    field = text_field(label, "", multiline=key in multiline_keys, key=f"field_{key}")
                    form_fields[key] = field
                    fields_column.controls.append(field)
        else:
            for key, label, required in table_fields(db_type):
                field = text_field(label, "", multiline=key in multiline_keys, key=f"field_{key}")
                form_fields[key] = field
                fields_column.controls.append(field)

        save_button = ft.Button(
            "Save New Record",
            icon=ft.Icons.SAVE,
            bgcolor=GOLD,
            color=DARK_BG,
            on_click=lambda _e: perform_save(),
        )
        save_button_ref["control"] = save_button

        form_column.controls.extend([
            ft.Row([
                ft.Text("New Entry", size=18, weight=ft.FontWeight.BOLD, color=GOLD),
                ft.Container(expand=True),
                form_status,
            ]),
            ft.Container(
                bgcolor=FIELD_BG,
                border_radius=8,
                padding=10,
                content=ft.Text(
                    "Enter the core record first. Identification images and attachments are available after saving.",
                    size=12,
                    color=MUTED,
                ),
            ),
            ft.Container(
                expand=True,
                bgcolor=PANEL_BG,
                border_radius=8,
                padding=10,
                content=fields_column,
            ),
            ft.Row([
                save_button,
                ft.Button("Clear", on_click=lambda _e: clear_form()),
            ], spacing=10),
        ])
        page.update()
        event("NEW_RECORD_FORM_OPENED", f"table={db_type}")

    def open_edit_form(record_id: int):
        nonlocal selected_record_id, form_mode, dirty
        row = fetch_record(db_type, record_id)
        if not row:
            notify("The record no longer exists.", False)
            load_list()
            clear_form()
            return

        selected_record_id = record_id
        form_mode = "edit"
        dirty = False
        form_fields.clear()
        form_column.controls.clear()

        media_panel = build_media_panel(db_type, record_id)
        fields_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)

        if db_type == "persons":
            for section_title, section_fields in person_field_sections():
                fields_column.controls.append(
                    ft.Text(section_title, size=15, weight=ft.FontWeight.BOLD, color=GOLD)
                )
                for key, label, required in section_fields:
                    field = text_field(label, str(row.get(key) or ""), multiline=key in multiline_keys, key=f"field_{key}")
                    form_fields[key] = field
                    fields_column.controls.append(field)
        else:
            for key, label, required in table_fields(db_type):
                field = text_field(label, str(row.get(key) or ""), multiline=key in multiline_keys, key=f"field_{key}")
                form_fields[key] = field
                fields_column.controls.append(field)

        form_status.value = f"Loaded · ID {record_id}"
        form_status.color = SUCCESS

        save_button = ft.Button(
            "Save Changes",
            icon=ft.Icons.SAVE,
            bgcolor=GOLD,
            color=DARK_BG,
            on_click=lambda _e: perform_save(),
        )
        save_button_ref["control"] = save_button

        form_column.controls.extend([
            ft.Row([
                ft.Text(
                    f"Edit: {row.get('name') or row.get('codename')}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=GOLD,
                ),
                ft.Container(expand=True),
                form_status,
            ]),
            ft.Row([
                ft.Container(
                    expand=True,
                    bgcolor=PANEL_BG,
                    border_radius=8,
                    padding=10,
                    content=fields_column,
                ),
                ft.Container(
                    width=360,
                    bgcolor=PANEL_BG,
                    border_radius=8,
                    padding=10,
                    content=media_panel,
                ),
            ], expand=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([
                save_button,
                ft.Button("Close", on_click=lambda _e: maybe_close_form()),
            ], spacing=10),
        ])
        page.update()
        event("EDIT_RECORD_OPENED", f"table={db_type} | record_id={record_id}")

    def values_from_form() -> dict[str, str]:
        values = {}
        for key, label, required in table_fields(db_type):
            value = (form_fields[key].value or "").strip()
            if required and not value:
                raise ValueError(f"{label} is required.")
            values[key] = value
        return values

    def perform_save():
        nonlocal is_saving, dirty, selected_record_id
        if is_saving:
            event("RECORD_SAVE_IGNORED", "already_saving")
            return

        try:
            values = values_from_form()
        except Exception as exc:
            form_status.value = "Not saved"
            form_status.color = DANGER
            page.update()
            notify(str(exc), False)
            return

        is_saving = True
        set_save_enabled(False)
        form_status.value = "Saving..."
        form_status.color = GOLD
        page.update()

        entry_id = selected_record_id
        mode = "update" if entry_id is not None else "insert"
        event("RECORD_SAVE_STARTED", f"table={db_type} | mode={mode} | id={entry_id}")

        try:
            saved_id = save_record(db_type, entry_id, values)
            dirty = False
            selected_record_id = saved_id

            # Refresh the list from SQLite, then reload the record from SQLite.
            load_list()
            saved_row = fetch_record(db_type, saved_id)
            if not saved_row:
                raise RuntimeError("Save completed, but the record could not be reloaded.")

            if entry_id is None:
                notify("Record created successfully.")
                open_edit_form(saved_id)
            else:
                form_status.value = f"Saved · {now_str()}"
                form_status.color = SUCCESS
                notify("Changes saved successfully.")
                # Rebuild the editor with a fresh record and fresh media state.
                open_edit_form(saved_id)

        except Exception as exc:
            form_status.value = "Save failed"
            form_status.color = DANGER
            log_exception("PERFORM_SAVE_FAILED", exc)
            notify(f"Save failed: {exc}", False)
        finally:
            is_saving = False
            set_save_enabled(True)
            page.update()

    def maybe_close_form():
        if dirty:
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Unsaved changes"),
                content=ft.Text("This record has unsaved changes. Close without saving?"),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: page.pop_dialog()),
                    ft.TextButton("Close Without Saving", on_click=lambda _e: close_without_saving()),
                ],
            )
            page.show_dialog(dialog)
        else:
            clear_form()

    def close_without_saving():
        page.pop_dialog()
        clear_form()

    def confirm_delete(record_id: int):
        row = fetch_record(db_type, record_id)
        if not row:
            load_list()
            return
        identity = row.get("codename") if db_type == "operations" else row.get("name")
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete record"),
            content=ft.Text(f"Delete '{identity}' permanently? Its stored attachments will also be deleted."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _e: page.pop_dialog()),
                ft.Button("Delete", bgcolor=DANGER, color=TEXT_LIGHT,
                          on_click=lambda _e: do_delete(record_id)),
            ],
        )
        page.show_dialog(dialog)

    def do_delete(record_id: int):
        try:
            page.pop_dialog()
            delete_record(db_type, record_id)
            if selected_record_id == record_id:
                clear_form()
            load_list()
            notify("Record deleted.")
        except Exception as exc:
            log_exception("DELETE_UI_FAILED", exc)
            notify(f"Delete failed: {exc}", False)

    def switch_db_type(table: str):
        nonlocal db_type
        db_type = table
        event("DATABASE_VIEW_SWITCHED", table)
        load_list()
        clear_form()

    def start_export_record(record_id: int):
        if file_picker is None:
            notify("File export is available in normal desktop mode.", False)
            return

        async def runner():
            try:
                row = fetch_record(db_type, record_id)
                if not row:
                    raise ValueError("The record no longer exists.")
                title = row.get("codename") or row.get("name") or "entry"
                safe = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in title).strip() or "entry"
                path = await file_picker.save_file(
                    dialog_title="Export CSB Entry",
                    file_name=f"{safe}.csbentry",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["csbentry"],
                )
                if path:
                    export_entry(db_type, record_id, path)
                    notify("Entry exported successfully.")
            except Exception as exc:
                log_exception("ENTRY_EXPORT_UI_FAILED", exc)
                notify(f"Export failed: {exc}", False)

        page.run_task(runner)

    async def start_import(_=None):
        if file_picker is None:
            notify("File import is available in normal desktop mode.", False)
            return
        try:
            event("ENTRY_IMPORT_CLICKED")
            files = await file_picker.pick_files(
                dialog_title="Import CSB Entry",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csbentry", "json"],
            )
            if not files:
                return
            path = files[0].path
            if not path:
                raise ValueError("The selected file does not provide a local path.")
            table, entry, attachments = import_entry(path)
            key = record_identity(table)
            identity = str(entry.get(key, "")).strip()
            conn = get_connection()
            try:
                existing = conn.execute(
                    f"SELECT id FROM {table} WHERE lower({key})=lower(?) LIMIT 1",
                    (identity,),
                ).fetchone()
            finally:
                conn.close()

            def keep_existing(_e):
                page.pop_dialog()
                notify("Existing record kept.")

            def replace_existing(_e):
                try:
                    page.pop_dialog()
                    write_imported_entry(table, entry, attachments, int(existing["id"]) if existing else None)
                    switch_db_type(table)
                    notify("Record imported successfully.")
                except Exception as exc:
                    log_exception("IMPORT_REPLACE_UI_FAILED", exc)
                    notify(f"Import failed: {exc}", False)

            if existing:
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Record already exists"),
                    content=ft.Text(
                        f"A {table[:-1] if table.endswith('s') else table} with the same {key} already exists.\n\n"
                        "Replace the existing record with the imported record?"
                    ),
                    actions=[
                        ft.TextButton("Keep Existing", on_click=keep_existing),
                        ft.Button("Replace", on_click=replace_existing),
                    ],
                )
                page.show_dialog(dialog)
            else:
                write_imported_entry(table, entry, attachments, None)
                switch_db_type(table)
                notify("Entry imported successfully.")
        except Exception as exc:
            log_exception("ENTRY_IMPORT_UI_FAILED", exc)
            notify(f"Import failed: {exc}", False)

    async def start_database_export(_=None):
        if file_picker is None:
            notify("Database export is available in normal desktop mode.", False)
            return
        try:
            path = await file_picker.save_file(
                dialog_title="Export CSB Database",
                file_name="csb_database.csbdb",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csbdb"],
            )
            if path:
                export_database_copy(path)
                event("DATABASE_EXPORT_SUCCESS", path)
                notify("Database exported successfully.")
        except Exception as exc:
            log_exception("DATABASE_EXPORT_FAILED", exc)
            notify(f"Database export failed: {exc}", False)

    persons_button = ft.Button("Persons", bgcolor=GOLD, color=DARK_BG, on_click=lambda _e: switch_db_type("persons"))
    orgs_button = ft.Button("Organizations", bgcolor=CARD_BG, color=TEXT_LIGHT, on_click=lambda _e: switch_db_type("organizations"))
    ops_button = ft.Button("Operations", bgcolor=CARD_BG, color=TEXT_LIGHT, on_click=lambda _e: switch_db_type("operations"))

    def refresh_db_buttons():
        mapping = {"persons": persons_button, "organizations": orgs_button, "operations": ops_button}
        for name, button in mapping.items():
            if name == db_type:
                button.bgcolor = GOLD
                button.color = DARK_BG
            else:
                button.bgcolor = CARD_BG
                button.color = TEXT_LIGHT

    db_view = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.FOLDER_SHARED, color=GOLD, size=28),
                    ft.Text("Records / Database", size=24, weight=ft.FontWeight.BOLD, color=GOLD),
                    ft.Container(expand=True),
                    ft.Text(str(DB_PATH), size=10, color=MUTED),
                ], spacing=10),
                ft.Row([
                    persons_button,
                    orgs_button,
                    ops_button,
                    ft.Container(expand=True),
                    ft.Button("New Entry", icon=ft.Icons.ADD, bgcolor=GOLD, color=DARK_BG, on_click=lambda _e: clear_form()),
                    ft.Button("Import Entry", icon=ft.Icons.UPLOAD_FILE, on_click=lambda e: page.run_task(start_import, e)),
                    ft.Button("Export Database", icon=ft.Icons.DOWNLOAD, on_click=lambda e: page.run_task(start_database_export, e)),
                ], spacing=8),
                db_toolbar_status,
                ft.Row([
                    ft.Container(
                        expand=2,
                        bgcolor=CARD_BG,
                        border_radius=10,
                        padding=12,
                        content=ft.Column([
                            ft.Text("Entries", size=15, weight=ft.FontWeight.BOLD, color=GOLD_LIGHT),
                            list_column,
                        ], expand=True),
                    ),
                    ft.Container(
                        expand=4,
                        bgcolor=CARD_BG,
                        border_radius=10,
                        padding=15,
                        content=form_column,
                    ),
                ], expand=True, spacing=15),
            ],
        ),
    )

    # ----------------------------------- [DATA INTAKE] ---------------------------------------------

    intake_search = ft.TextField(
        label="Search persons",
        prefix_icon=ft.Icons.SEARCH,
        bgcolor=CARD_BG,
        color=TEXT_LIGHT,
        border_color=GOLD,
    )
    intake_area = ft.Dropdown(
        label="Intelligence Area",
        options=[
            ft.DropdownOption("domestic", "Domestic Intelligence"),
            ft.DropdownOption("external", "External Intelligence"),
        ],
        value="domestic",
        bgcolor=CARD_BG,
        color=TEXT_LIGHT,
        border_color=GOLD,
    )
    intake_person = ft.Dropdown(
        label="Select person",
        options=[],
        bgcolor=CARD_BG,
        color=TEXT_LIGHT,
        border_color=GOLD,
    )
    intake_text = ft.TextField(
        label="Intelligence / quick note",
        multiline=True,
        min_lines=9,
        max_lines=16,
        bgcolor=FIELD_BG,
        color=TEXT_LIGHT,
        border_color=GOLD,
    )
    intake_selected_path: str | None = None
    intake_image_status = ft.Text("No image selected.", size=12, color=MUTED)

    def refresh_intake_people(_=None):
        try:
            term = (intake_search.value or "").strip().casefold()
            rows = fetch_records("persons")
            visible = [
                row for row in rows
                if not term or term in str(row["name"]).casefold()
            ]
            intake_person.options = [
                ft.DropdownOption(str(row["id"]), str(row["name"]))
                for row in visible
            ]
            if intake_person.value and not any(
                option.key == intake_person.value for option in intake_person.options
            ):
                intake_person.value = None
            event("DATA_INTAKE_PERSON_LIST_READY", f"total={len(rows)} | visible={len(visible)}")
            page.update()
        except Exception as exc:
            log_exception("DATA_INTAKE_LIST_FAILED", exc)
            notify(f"Could not refresh person list: {exc}", False)

    def on_intake_search(_):
        refresh_intake_people()

    intake_search.on_change = on_intake_search

    async def pick_intake_image(_):
        nonlocal intake_selected_path
        if image_picker is None:
            notify("File selection is available in normal desktop mode.", False)
            return
        try:
            event("DATA_INTAKE_IMAGE_BUTTON_CLICKED")
            files = await image_picker.pick_files(
                dialog_title="Select Intake Image",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
            )
            if not files:
                return
            path = files[0].path
            if not path:
                raise ValueError("The selected image does not provide a local path.")
            intake_selected_path = path
            intake_image_status.value = f"Selected: {Path(path).name}"
            event("DATA_INTAKE_IMAGE_SELECTED", Path(path).name)
            page.update()
        except Exception as exc:
            log_exception("DATA_INTAKE_IMAGE_FAILED", exc)
            notify(f"Image selection failed: {exc}", False)

    def save_intake(_):
        nonlocal intake_selected_path
        event("DATA_INTAKE_SAVE_STARTED")
        try:
            if not intake_person.value:
                raise ValueError("Please select a person.")
            note = (intake_text.value or "").strip()
            if not note and not intake_selected_path:
                raise ValueError("Enter a note or select an image.")

            person_id = int(intake_person.value)
            conn = get_connection()
            try:
                row = conn.execute("SELECT notes FROM persons WHERE id=?", (person_id,)).fetchone()
                if not row:
                    raise ValueError("The selected person no longer exists.")
                existing = (row["notes"] or "").strip()
                if note:
                    notes_column = "domestic_notes" if (intake_area.value or "domestic") == "domestic" else "external_notes"
                    current_row = conn.execute(
                        f"SELECT {notes_column} FROM persons WHERE id=?",
                        (person_id,),
                    ).fetchone()
                    current = str(current_row[0] or "").strip()
                    block = f"[{now_str()}] {note}"
                    updated = f"{current}\n{block}".strip() if current else block
                    conn.execute(
                        f"UPDATE persons SET {notes_column}=?, updated_at=? WHERE id=?",
                        (updated, now_str(), person_id),
                    )
                conn.commit()
            finally:
                conn.close()

            if intake_selected_path:
                save_attachment("persons", person_id, intake_selected_path, False)

            intake_text.value = ""
            intake_selected_path = None
            intake_image_status.value = "No image selected."
            refresh_intake_people()
            event("DATA_INTAKE_SAVE_SUCCESS", f"person_id={person_id}")
            notify("Intelligence added to the selected person.")
        except Exception as exc:
            log_exception("DATA_INTAKE_SAVE_FAILED", exc)
            notify(f"Data Intake failed: {exc}", False)

    intake_view = ft.Container(
        expand=True,
        padding=30,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.BOLT, color=GOLD, size=28),
                    ft.Text("Data Intake", size=24, weight=ft.FontWeight.BOLD, color=GOLD),
                ], spacing=12),
                ft.Text(
                    "Rapidly attach notes or images to an existing person record. The person list is refreshed from SQLite whenever this view is entered.",
                    size=13,
                    color=MUTED,
                ),
                ft.Row([intake_search, intake_person, intake_area], spacing=12),
                intake_text,
                ft.Row([
                    ft.Button("Add Image", icon=ft.Icons.IMAGE, on_click=lambda e: page.run_task(pick_intake_image, e)),
                    intake_image_status,
                    ft.Container(expand=True),
                    ft.Button("Add to Record", icon=ft.Icons.SAVE, bgcolor=GOLD, color=DARK_BG, on_click=save_intake),
                ], spacing=10),
            ],
        ),
    )

    # ============================================================
    # CONNECTIONS – rein textbasiert
    # ============================================================

    # Ergebnis-Textfeld (wird auch global verwendet)
    result_text = ft.TextField(
        multiline=True,
        read_only=True,
        expand=True,
        bgcolor=FIELD_BG,
        color=TEXT_LIGHT,
        border_color=GOLD,
        text_style=ft.TextStyle(size=13, font_family="Consolas"),
        value="No analysis run yet. Switch to this view to start analysis.",
    )

    def run_connections_analysis():
        """Führt die Verbindungsanalyse mit festen Standardparametern durch und aktualisiert result_text."""
        event("CONNECTION_ANALYSIS_AUTO_STARTED")
        try:
            persons = fetch_records("persons")
            if not persons:
                result_text.value = "No person records found. Please add some records first."
                return

            # Feste Parameter: beide Domains, Threshold 0.88, Min-Score 20
            domains = ("Domestic", "External")
            similarity_threshold = 0.88
            min_score = 20

            results = analyze_person_connections(
                persons,
                similarity_threshold=similarity_threshold,
                include_domains=domains,
                min_score=min_score,
            )

            # Ergebnis als Text aufbereiten
            lines = []
            if not results:
                lines.append("No connections found with the selected thresholds.")
            else:
                for res in results:
                    lines.append(f"{res['person_a']} ↔ {res['person_b']}  [{res['domain']}]  Score: {res['score']}  ({res['strength']})")
                    for item in res["evidence"]:
                        field = item["field"]
                        sim = item["similarity"]
                        if item["value_a"] and item["value_b"]:
                            lines.append(f"  - {field}: '{item['value_a']}' ↔ '{item['value_b']}' ({sim}%)  +{item['weight']}")
                        else:
                            lines.append(f"  - {field} (Cross-reference) +{item['weight']}")
                    lines.append("-" * 50)

            result_text.value = "\n".join(lines)
            event("CONNECTION_ANALYSIS_AUTO_DONE", f"records={len(persons)} | results={len(results)}")
        except Exception as exc:
            log_exception("CONNECTION_ANALYSIS_AUTO_FAILED", exc)
            result_text.value = f"Analysis failed: {type(exc).__name__}: {exc}"

    connections_view = ft.Container(
        expand=True,
        padding=30,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.HUB, color=GOLD, size=28),
                    ft.Text("Connection Analysis (text only)", size=24, weight=ft.FontWeight.BOLD, color=GOLD),
                ], spacing=12),
                ft.Text(
                    "All direct Domestic and External connections are automatically analyzed "
                    "with default thresholds (similarity ≥ 0.88, minimum score 20).",
                    size=13,
                    color=MUTED,
                ),
                ft.Container(
                    expand=True,
                    bgcolor=FIELD_BG,
                    padding=12,
                    border_radius=10,
                    border=ft.border.Border.all(1, "#2A3545"),
                    content=result_text,
                ),
            ],
        ),
    )

    # ----------------------------------- [NAVIGATION] ---------------------------------------------

    content_area = ft.Container(expand=True, content=crypto_view)

    def change_view(index: int):
        nonlocal selected_view
        if index == selected_view:
            return
        selected_view = index
        event("NAVIGATION", str(index))

        if index == 0:
            content_area.content = crypto_view
        elif index == 1:
            content_area.content = db_view
            refresh_db_buttons()
            load_list()
            if form_mode == "new":
                clear_form()
        elif index == 2:
            content_area.content = intake_view
            refresh_intake_people()
            intake_search.value = intake_search.value or ""
        else:  # index == 3
            content_area.content = connections_view
            run_connections_analysis()

        rail.selected_index = index
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=90,
        min_extended_width=180,
        group_alignment=-0.85,
        bgcolor="#0A0E14",
        indicator_color=GOLD,
        selected_label_text_style=ft.TextStyle(color=GOLD, weight=ft.FontWeight.BOLD),
        unselected_label_text_style=ft.TextStyle(color="#888"),
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.LOCK_OUTLINE, selected_icon=ft.Icons.LOCK, label="Crypto"),
            ft.NavigationRailDestination(icon=ft.Icons.FOLDER_OUTLINED, selected_icon=ft.Icons.FOLDER, label="Records"),
            ft.NavigationRailDestination(icon=ft.Icons.BOLT_OUTLINED, selected_icon=ft.Icons.BOLT, label="Data Intake"),
            ft.NavigationRailDestination(icon=ft.Icons.HUB_OUTLINED, selected_icon=ft.Icons.HUB, label="Connections"),
        ],
        on_change=lambda e: change_view(e.control.selected_index),
    )

    header = ft.Container(
        bgcolor="#0A0E14",
        padding=ft.padding.Padding.symmetric(vertical=12, horizontal=20),
        border=ft.border.Border.only(bottom=ft.BorderSide(1, "#1F2A3A")),
        content=ft.Row([
            ft.Icon(ft.Icons.SHIELD, color=GOLD, size=26),
            ft.Text("CRUSADER SECRET BUREAU", size=18, weight=ft.FontWeight.BOLD, color=GOLD, font_family="Georgia"),
            ft.Container(expand=True),
            ft.Text("Stoneworks · CSB", size=12, color="#666"),
        ]),
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                ft.Row([
                    rail,
                    ft.VerticalDivider(width=1, color="#1F2A3A"),
                    content_area,
                ], expand=True, spacing=0),
            ],
        )
    )

    # Initial state.
    refresh_db_buttons()
    load_list()
    clear_form()
    event("APP_UI_READY")


if __name__ == "__main__":
    ft.run(main)
