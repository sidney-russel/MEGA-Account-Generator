import csv
import os
import threading
import logging
import sys

def get_app_path():
    """Get the absolute path to the application directory."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

CSV_FILE = os.path.join(get_app_path(), "accounts.csv")
HEADER = ["Email", "Password", "Storage Used", "Free Storage", "Session Status", "Tags", "Mail.tm Password", "Mail.tm ID"]

# Global lock for thread-safe access
lock = threading.Lock()

def initialize_csv():
    """Ensure CSV exists with correct header."""
    with lock:
        if not os.path.exists(CSV_FILE):
             with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(HEADER)

def csv_exists():
    """Check if the CSV file exists."""
    with lock:
        return os.path.exists(CSV_FILE)

def _read_rows():
    """Read rows from CSV. Caller MUST hold the lock."""
    rows = []
    try:
        try:
            with open(CSV_FILE, "r", encoding='utf-8') as f:
                rows = list(csv.reader(f))
        except UnicodeDecodeError:
            with open(CSV_FILE, "r", encoding='latin-1') as f:
                rows = list(csv.reader(f))
    except FileNotFoundError:
        return []
    except Exception as e:
        logging.error(f"Error reading CSV: {e}")
        return []

    if not rows:
        return []

    data_rows = []
    if rows[0] and "email" in rows[0][0].lower():
        data_rows = rows[1:]
    else:
        data_rows = rows

    normalized_rows = []
    for row in data_rows:
        if not row:
            continue
        
        if len(row) == 7:
            row.insert(5, "")
        
        while len(row) < 8:
            row.append("")
            
        normalized_rows.append(row)

    return normalized_rows

def _write_rows(rows):
    """Write rows to CSV. Caller MUST hold the lock."""
    try:
        with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            writer.writerows(rows)
        return True
    except Exception as e:
        logging.error(f"Error writing CSV: {e}")
        return False

def read_accounts():
    """
    Read all accounts from CSV.
    Automatically handles encoding issues and row normalization (migration).
    Returns a list of rows (lists).
    """
    initialize_csv()
    with lock:
        return _read_rows()

def write_accounts(rows):
    """
    Write all rows to CSV, replacing existing content.
    Args:
        rows: List of rows (lists). Header is NOT expected in input rows.
    """
    with lock:
        return _write_rows(rows)

def append_account(row):
    """
    Append a single account to the CSV.
    Args:
        row: List representing the account data.
    """
    initialize_csv()
    
    while len(row) < 8:
        row.append("")
    if len(row) > 8:
        row = row[:8]

    with lock:
        try:
            with open(CSV_FILE, "a", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            return True
        except Exception as e:
            logging.error(f"Error appending to CSV: {e}")
            return False

def update_account(email, col_index, new_value):
    """
    Atomically update a specific cell for a specific account.
    Uses a single lock acquisition for the entire read-modify-write cycle.
    """
    with lock:
        rows = _read_rows()
        updated = False
        for row in rows:
            if row[0] == email:
                if len(row) > col_index:
                    row[col_index] = new_value
                    updated = True
                    break
        
        if updated:
            return _write_rows(rows)
        return False

def count_accounts():
    """Return the number of accounts in the CSV (excluding header)."""
    with lock:
        rows = _read_rows()
        return len(rows)

def email_exists(email):
    """Check if an email already exists in the CSV (thread-safe, O(n))."""
    with lock:
        rows = _read_rows()
        for row in rows:
            if row[0] == email:
                return True
        return False

def get_existing_emails():
    """Get a set of all existing emails (thread-safe)."""
    with lock:
        rows = _read_rows()
        return {row[0] for row in rows}
