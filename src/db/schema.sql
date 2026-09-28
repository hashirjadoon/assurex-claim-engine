CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  full_name TEXT, email TEXT, phone TEXT,
  role TEXT NOT NULL CHECK(role IN ('customer','service_employee','reviewer','admin')),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
  product_id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id),
  product_name TEXT, category TEXT, brand TEXT, model_number TEXT,
  serial_number TEXT UNIQUE, purchase_date TEXT, purchase_price REAL, retailer TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS warranties (
  warranty_id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL REFERENCES products(product_id),
  warranty_type TEXT DEFAULT 'standard', provider TEXT,
  start_date TEXT, duration_days INTEGER, expiry_date TEXT
);
CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  user_id INTEGER REFERENCES users(user_id),
  product_id TEXT REFERENCES products(product_id),
  fault_type TEXT, fault_description TEXT, damage_type TEXT,
  fault_date TEXT, claim_date TEXT,
  repair_count INTEGER, repair_authorized INTEGER, previous_replacement INTEGER,
  serial_on_document TEXT,
  has_receipt INTEGER, has_warranty_card INTEGER, has_product_image INTEGER,
  is_duplicate INTEGER, status TEXT, card_path TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
  doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim_id TEXT REFERENCES claims(claim_id),
  doc_type TEXT, filename TEXT, file_path TEXT, sha256 TEXT,
  uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim_id TEXT REFERENCES claims(claim_id),
  python_class TEXT, py_conf_valid REAL, py_conf_invalid REAL, py_conf_manual REAL,
  gtm_class TEXT, gtm_conf_valid REAL, gtm_conf_invalid REAL, gtm_conf_manual REAL,
  class_match INTEGER, confidence_difference REAL, consistency_status TEXT,
  rule_status TEXT, rules_json TEXT, contradictions_json TEXT,
  final_decision TEXT, explanation_json TEXT,
  python_model_version TEXT, gtm_model_version TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reviews (
  review_id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim_id TEXT REFERENCES claims(claim_id),
  reviewer_id INTEGER REFERENCES users(user_id),
  action TEXT, comment TEXT, override_decision TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER, action TEXT, entity TEXT, entity_id TEXT, details TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notifications (
  notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);