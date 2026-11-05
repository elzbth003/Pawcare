import os
import sqlite3
from datetime import datetime

DEFAULT_DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pawcare.db")
)


def get_db_path(custom_path=None):
    return custom_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path=None):
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency with multiple gunicorn workers
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    """Initializes the database schema and seeds initial data atomically if not already seeded."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pet_name TEXT NOT NULL,
                    pet_type TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    owner_phone TEXT NOT NULL,
                    owner_email TEXT,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    service TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Scheduled',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

        # Atomically claim the initial seed using a PRIMARY KEY constraint
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO system_metadata (key, value) VALUES ('seeded', 'true');")
                seed_sample_data(conn)
        except sqlite3.IntegrityError:
            # Already seeded by another worker/process
            pass
    finally:
        conn.close()


def seed_sample_data(conn):
    """Seeds realistic clinic data so the dashboard is immediately functional."""
    sample_records = [
        (
            "Max", "Dog (Golden Retriever)", "Sarah Jenkins", "555-0142",
            "sarah.j@example.com", "2026-11-05", "10:00",
            "Annual Wellness Exam & Vaccinations", "Scheduled",
            "Friendly pup. Needs rabies booster."
        ),
        (
            "Luna", "Cat (Siamese)", "David Miller", "555-0188",
            "david.m@example.com", "2026-11-05", "11:30",
            "Dental Cleaning", "Completed",
            "Tartar removal completed smoothly. Recommend soft food for 2 days."
        ),
        (
            "Rocky", "Dog (German Shepherd)", "Elena Rostova", "555-0199",
            "elena.r@example.com", "2026-11-05", "14:00",
            "Limping / Orthopedic Checkup", "Scheduled",
            "Slight limp on rear-right paw after park play."
        ),
        (
            "Bella", "Rabbit (Holland Lop)", "Michael Chang", "555-0123",
            "mchang@example.com", "2026-11-04", "09:15",
            "Nail Trimming & Ear Check", "Completed",
            "Ears are clean, nails trimmed."
        ),
        (
            "Milo", "Cat (Domestic Shorthair)", "Amanda Lee", "555-0177",
            "amanda.l@example.com", "2026-11-06", "15:30",
            "Kitten Core Vaccination", "Scheduled",
            "First round of FVRCP vaccination."
        ),
        (
            "Charlie", "Dog (Beagle)", "Robert Wilson", "555-0164",
            "rwilson@example.com", "2026-11-03", "16:00",
            "Allergy & Skin Consultation", "Cancelled",
            "Owner rescheduled due to work trip."
        ),
    ]

    with conn:
        conn.executemany("""
            INSERT INTO appointments (
                pet_name, pet_type, owner_name, owner_phone,
                owner_email, appointment_date, appointment_time,
                service, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_records)


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def get_stats(db_path=None):
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments;")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled';")
        scheduled = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed';")
        completed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled';")
        cancelled = cursor.fetchone()[0]

        return {
            "total": total,
            "scheduled": scheduled,
            "completed": completed,
            "cancelled": cancelled
        }
    finally:
        conn.close()


def get_appointments(search=None, status=None, db_path=None):
    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM appointments WHERE 1=1"
        params = []

        if status and status.strip() and status != "All":
            query += " AND status = ?"
            params.append(status.strip())

        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query += """ AND (
                pet_name LIKE ? OR
                pet_type LIKE ? OR
                owner_name LIKE ? OR
                owner_phone LIKE ? OR
                service LIKE ? OR
                notes LIKE ?
            )"""
            params.extend([search_term] * 6)

        query += " ORDER BY appointment_date DESC, appointment_time DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_appointment_by_id(appointment_id, db_path=None):
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE id = ?;", (appointment_id,))
        row = cursor.fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def create_appointment(data, db_path=None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO appointments (
                    pet_name, pet_type, owner_name, owner_phone,
                    owner_email, appointment_date, appointment_time,
                    service, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data["pet_name"].strip(),
                data["pet_type"].strip(),
                data["owner_name"].strip(),
                data["owner_phone"].strip(),
                data.get("owner_email", "").strip() if data.get("owner_email") else "",
                data["appointment_date"].strip(),
                data["appointment_time"].strip(),
                data["service"].strip(),
                data.get("status", "Scheduled").strip(),
                data.get("notes", "").strip() if data.get("notes") else ""
            ))
            new_id = cursor.lastrowid
        return get_appointment_by_id(new_id, db_path)
    finally:
        conn.close()


def update_appointment(appointment_id, data, db_path=None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE appointments
                SET pet_name = ?,
                    pet_type = ?,
                    owner_name = ?,
                    owner_phone = ?,
                    owner_email = ?,
                    appointment_date = ?,
                    appointment_time = ?,
                    service = ?,
                    status = ?,
                    notes = ?
                WHERE id = ?;
            """, (
                data["pet_name"].strip(),
                data["pet_type"].strip(),
                data["owner_name"].strip(),
                data["owner_phone"].strip(),
                data.get("owner_email", "").strip() if data.get("owner_email") else "",
                data["appointment_date"].strip(),
                data["appointment_time"].strip(),
                data["service"].strip(),
                data.get("status", "Scheduled").strip(),
                data.get("notes", "").strip() if data.get("notes") else "",
                appointment_id
            ))
            if cursor.rowcount == 0:
                return None
        return get_appointment_by_id(appointment_id, db_path)
    finally:
        conn.close()


def update_appointment_status(appointment_id, status, db_path=None):
    valid_statuses = {"Scheduled", "Completed", "Cancelled"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Allowed values: {valid_statuses}")

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE appointments
                SET status = ?
                WHERE id = ?;
            """, (status, appointment_id))
            if cursor.rowcount == 0:
                return None
        return get_appointment_by_id(appointment_id, db_path)
    finally:
        conn.close()


def delete_appointment(appointment_id, db_path=None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM appointments WHERE id = ?;", (appointment_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()
