import hashlib
import secrets
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "database" / "assurex.db"
SCHEMA_PATH = ROOT / "src" / "db" / "schema.sql"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def query(sql, params=()):
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _hash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000).hex()


def create_user(username, password, role, full_name="", email="", phone=""):
    if query("SELECT 1 FROM users WHERE username=?", (username,)):
        return False
    salt = secrets.token_hex(16)
    execute("INSERT INTO users (username, password_hash, salt, full_name, email, phone, role) "
            "VALUES (?,?,?,?,?,?,?)",
            (username, _hash(password, salt), salt, full_name, email, phone, role))
    return True


def verify_user(username, password):
    rows = query("SELECT * FROM users WHERE username=?", (username,))
    if rows and _hash(password, rows[0]["salt"]) == rows[0]["password_hash"]:
        return rows[0]
    return None


def log_action(user_id, action, entity="", entity_id="", details=""):
    execute("INSERT INTO audit_log (user_id, action, entity, entity_id, details) VALUES (?,?,?,?,?)",
            (user_id, action, entity, entity_id, details))


def notify(user_id, message):
    execute("INSERT INTO notifications (user_id, message) VALUES (?,?)", (user_id, message))


def claim_overview(where="1=1", params=()):
    return query(
        "SELECT c.claim_id, c.user_id, c.product_id, pd.category, pd.serial_number, c.fault_type, "
        "c.fault_description, c.claim_date, c.created_at, c.status, c.is_duplicate, c.card_path, "
        "pr.final_decision, pr.python_class, pr.gtm_class, pr.class_match, pr.confidence_difference, "
        "pr.consistency_status, pr.rule_status, pr.py_conf_valid, pr.py_conf_invalid, pr.py_conf_manual, "
        "pr.gtm_conf_valid, pr.gtm_conf_invalid, pr.gtm_conf_manual, pr.explanation_json, "
        "pr.contradictions_json, pr.python_model_version, pr.gtm_model_version "
        "FROM claims c LEFT JOIN products pd ON pd.product_id = c.product_id "
        "LEFT JOIN predictions pr ON pr.claim_id = c.claim_id "
        "WHERE " + where + " ORDER BY c.created_at DESC", params)


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()
    if empty:
        create_user("admin", "Admin@123", "admin", "Default Admin")
        create_user("reviewer", "Review@123", "reviewer", "Default Reviewer")
        create_user("demo", "Demo@123", "customer", "Demo Customer")