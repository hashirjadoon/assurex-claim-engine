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


def seed_demo_data():
    import uuid
    import json
    from datetime import date, timedelta
    from pathlib import Path
    from src.ml.predict import predict_claim
    from src.ml.gtm_client import classify_card
    from src.rules_engine.warranty_rules import validate_claim
    from src.rules_engine.contradiction_checks import detect_contradictions
    from src.decision.final_decision import make_final_decision
    from src.cards.generate_card import render

    uid = query("SELECT user_id FROM users WHERE username='demo'")[0]["user_id"]

    def make_product(cat, name, days_ago, warranty_days):
        pid = f"PRD-D{uuid.uuid4().hex[:6].upper()}"
        pdate = (date.today() - timedelta(days=days_ago)).isoformat()
        execute("INSERT INTO products (product_id,user_id,product_name,category,brand,model_number,serial_number,purchase_date,purchase_price,retailer) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, uid, name, cat, "DemoBrand", "M100", f"SN-D{uuid.uuid4().hex[:8].upper()}", pdate, 500.0, "DemoStore"))
        exp = (date.fromisoformat(pdate) + timedelta(days=warranty_days)).isoformat()
        execute("INSERT INTO warranties (product_id,provider,start_date,duration_days,expiry_date) VALUES (?,?,?,?,?)",
                (pid, "DemoBrand", pdate, warranty_days, exp))
        return pid, pdate, exp

    def submit(pid, pdate, exp, cat, fault, desc, fault_days_ago, claim_days_ago,
               repair_count, repair_auth, prev_repl, serial_match, has_r, has_w, has_p, is_dup):
        cid = f"CLM-D{uuid.uuid4().hex[:7].upper()}"
        claim_date = (date.today() - timedelta(days=claim_days_ago)).isoformat()
        fault_date = (date.today() - timedelta(days=fault_days_ago)).isoformat()
        prod = query("SELECT product_name, serial_number FROM products WHERE product_id=?", (pid,))[0]
        record = {
            "claim_id": cid, "product_id": pid, "product_category": cat, "product_name": prod["product_name"],
            "serial_number": prod["serial_number"], "purchase_date": pdate, "purchase_price": 500.0,
            "warranty_start_date": pdate,
            "warranty_duration_days": (date.fromisoformat(exp) - date.fromisoformat(pdate)).days,
            "warranty_expiry_date": exp, "fault_occurrence_date": fault_date, "fault_type": fault,
            "fault_description": desc, "damage_type": "Manufacturing Defect",
            "claim_submission_date": claim_date,
            "product_age_days": (date.fromisoformat(claim_date) - date.fromisoformat(pdate)).days,
            "has_receipt": has_r, "has_warranty_card": has_w, "has_product_image": has_p,
            "serial_number_match": serial_match, "repair_count": repair_count,
            "repair_authorized": repair_auth, "previous_replacement": prev_repl, "is_duplicate_claim": is_dup,
        }
        py = predict_claim(record)
        card_path = Path(f"data/uploads/cards/{cid}.png")
        card_path.parent.mkdir(parents=True, exist_ok=True)
        render(record, "#FFFFFF", 16, 6).save(card_path)
        gtm = classify_card(str(card_path))
        rules = validate_claim(record)
        contra = detect_contradictions(record)
        result = make_final_decision(py, gtm, rules, contra)
        status = {"Likely Valid": "Approved", "Likely Invalid": "Rejected",
                  "Manual Review Required": "Manual Review"}[result["final_decision"]]
        execute("INSERT INTO claims (claim_id,user_id,product_id,fault_type,fault_description,damage_type,fault_date,claim_date,repair_count,repair_authorized,previous_replacement,serial_on_document,has_receipt,has_warranty_card,has_product_image,is_duplicate,status,card_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, uid, pid, fault, desc, "Manufacturing Defect", fault_date, claim_date, repair_count,
                 int(repair_auth), int(prev_repl), record["serial_number"], int(has_r), int(has_w), int(has_p),
                 int(is_dup), status, str(card_path)))
        pc, gc = py["confidences"], gtm["confidences"]
        execute("INSERT INTO predictions (claim_id,python_class,py_conf_valid,py_conf_invalid,py_conf_manual,gtm_class,gtm_conf_valid,gtm_conf_invalid,gtm_conf_manual,class_match,confidence_difference,consistency_status,rule_status,rules_json,contradictions_json,final_decision,explanation_json,python_model_version,gtm_model_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, py["predicted_class"], pc["Valid"], pc["Invalid"], pc["ManualReview"], gtm["predicted_class"],
                 gc["Valid"], gc["Invalid"], gc["ManualReview"], int(result["consistency"]["class_match"]),
                 result["consistency"]["confidence_difference"], result["consistency"]["consistency_status"],
                 rules["status"], json.dumps(rules), json.dumps(contra), result["final_decision"],
                 json.dumps(result["explanation"]), "GradientBoosting v1.0.0", "TeachableMachine v1.0"))

    pid, pdate, exp = make_product("Electronics", "Smart TV", 100, 730)
    submit(pid, pdate, exp, "Electronics", "Screen Malfunction", "Screen Malfunction reported by customer during normal use.", 5, 2, 0, True, False, True, True, True, True, False)

    pid, pdate, exp = make_product("Electronics", "Laptop", 800, 365)
    submit(pid, pdate, exp, "Electronics", "Battery Failure", "Battery Failure reported by customer.", 5, 2, 0, True, False, True, True, True, True, False)

    pid, pdate, exp = make_product("Appliances", "Washing Machine", 100, 730)
    submit(pid, pdate, exp, "Appliances", "Rust/Corrosion", "Rust/Corrosion - not covered under warranty terms.", 5, 2, 0, True, False, True, True, True, True, False)

    pid, pdate, exp = make_product("Furniture", "Office Chair", 100, 365)
    submit(pid, pdate, exp, "Furniture", "Joint/Hinge Failure", "Joint/Hinge Failure reported by customer.", 5, 2, 0, True, False, True, False, True, True, False)

    pid, pdate, exp = make_product("Appliances", "Refrigerator", 200, 1095)
    submit(pid, pdate, exp, "Appliances", "Compressor Fault", "Compressor Fault reported by customer.", 5, 2, 2, False, False, True, True, True, True, False)

    pid, pdate, exp = make_product("Electronics", "Tablet", 50, 730)
    submit(pid, pdate, exp, "Electronics", "Charging Port Issue", "Charging Port Issue reported by customer.", 5, 2, 0, True, False, True, True, True, True, True)


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
        seed_demo_data()