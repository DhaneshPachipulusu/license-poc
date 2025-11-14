# db.py (very simple sqlite wrapper)
import sqlite3
from typing import Optional
import json


DB = 'licenses.db'


def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS licenses (
    id TEXT PRIMARY KEY,
    customer TEXT,
    machine_id TEXT,
    license_json TEXT,
    revoked INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()




def save_license(license_id: str, customer: str, machine_id: str, license_obj: dict):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('REPLACE INTO licenses (id, customer, machine_id, license_json, revoked) VALUES (?, ?, ?, ?, ?)',
    (license_id, customer, machine_id, json.dumps(license_obj), 0))
    conn.commit()
    conn.close()




def get_license_by_machine(machine_id: str) -> Optional[dict]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT license_json, revoked FROM licenses WHERE machine_id = ?', (machine_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
        obj = json.loads(row[0])
        obj['revoked'] = bool(row[1])
        return obj




def revoke_license(license_id: str):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('UPDATE licenses SET revoked = 1 WHERE id = ?', (license_id,))
    conn.commit()
    conn.close()