import sqlite3
import json
import os
from datetime import datetime, date
from io import BytesIO

from fpdf import FPDF

from atulya_accounting_erp.utils import (
    get_db_path, parse_date, format_date, format_indian_number,
    format_indian_rupees, calculate_gst, pdf_heading, pdf_subheading,
    pdf_text, pdf_table_header, pdf_table_row, pdf_line,
)

CHART_OF_ACCOUNTS = [
    {"code": "10001", "name": "Cash in Hand", "group": "Current Assets", "type": "Asset", "opening": 0.0},
    {"code": "10002", "name": "Bank Account", "group": "Current Assets", "type": "Asset", "opening": 0.0},
    {"code": "10003", "name": "Accounts Receivable", "group": "Current Assets", "type": "Asset", "opening": 0.0},
    {"code": "10004", "name": "Inventory", "group": "Current Assets", "type": "Asset", "opening": 0.0},
    {"code": "10005", "name": "Prepaid Expenses", "group": "Current Assets", "type": "Asset", "opening": 0.0},
    {"code": "10101", "name": "Furniture & Fixtures", "group": "Fixed Assets", "type": "Asset", "opening": 0.0},
    {"code": "10102", "name": "Computers & Peripherals", "group": "Fixed Assets", "type": "Asset", "opening": 0.0},
    {"code": "10103", "name": "Vehicles", "group": "Fixed Assets", "type": "Asset", "opening": 0.0},
    {"code": "10104", "name": "Buildings", "group": "Fixed Assets", "type": "Asset", "opening": 0.0},
    {"code": "10105", "name": "Accumulated Depreciation", "group": "Fixed Assets", "type": "Asset", "opening": 0.0},
    {"code": "10201", "name": "Investments", "group": "Investments", "type": "Asset", "opening": 0.0},
    {"code": "20001", "name": "Accounts Payable", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20002", "name": "Short Term Loans", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20003", "name": "GST Payable", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20004", "name": "TDS Payable", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20005", "name": "Outstanding Expenses", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20006", "name": "Advance from Customers", "group": "Current Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20101", "name": "Bank Loans", "group": "Long Term Liabilities", "type": "Liability", "opening": 0.0},
    {"code": "20201", "name": "Capital Account", "group": "Equity", "type": "Equity", "opening": 0.0},
    {"code": "20202", "name": "Drawings", "group": "Equity", "type": "Equity", "opening": 0.0},
    {"code": "20203", "name": "Retained Earnings", "group": "Equity", "type": "Equity", "opening": 0.0},
    {"code": "30001", "name": "Sales Revenue", "group": "Revenue", "type": "Income", "opening": 0.0},
    {"code": "30002", "name": "Other Income", "group": "Revenue", "type": "Income", "opening": 0.0},
    {"code": "30003", "name": "Discount Received", "group": "Revenue", "type": "Income", "opening": 0.0},
    {"code": "40001", "name": "Purchases", "group": "Direct Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40002", "name": "Direct Expenses", "group": "Direct Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40003", "name": "Cost of Goods Sold", "group": "Direct Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40101", "name": "Salaries & Wages", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40102", "name": "Rent & Utilities", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40103", "name": "Electricity Charges", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40104", "name": "Office Expenses", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40105", "name": "Depreciation", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40106", "name": "Discount Allowed", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40107", "name": "Commission Paid", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40108", "name": "Interest Paid", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40109", "name": "Tax Expenses", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
    {"code": "40110", "name": "Miscellaneous Expenses", "group": "Indirect Expenses", "type": "Expense", "opening": 0.0},
]


def _connect():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database(data_dir=None):
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        from atulya_accounting_erp.utils import set_db_path
        set_db_path(os.path.join(data_dir, "erp_data.db"))

    conn = _connect()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Asset','Liability','Equity','Income','Expense')),
            opening_balance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_number TEXT UNIQUE NOT NULL,
            entry_date TEXT NOT NULL,
            description TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS journal_entry_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            debit_amount REAL NOT NULL DEFAULT 0,
            credit_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            unit TEXT NOT NULL DEFAULT 'nos',
            opening_stock REAL NOT NULL DEFAULT 0,
            rate REAL NOT NULL DEFAULT 0,
            hsn_code TEXT DEFAULT '',
            gst_rate REAL NOT NULL DEFAULT 18,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            movement_date TEXT NOT NULL,
            movement_type TEXT NOT NULL CHECK(movement_type IN ('IN','OUT')),
            quantity REAL NOT NULL,
            rate REAL NOT NULL DEFAULT 0,
            reference TEXT DEFAULT '',
            ref_type TEXT DEFAULT '',
            ref_id INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (item_id) REFERENCES inventory_items(id)
        );

        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_type TEXT NOT NULL CHECK(bill_type IN ('invoice','quote','credit_note')),
            bill_number TEXT UNIQUE NOT NULL,
            bill_date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_address TEXT DEFAULT '',
            customer_gst TEXT DEFAULT '',
            customer_state TEXT DEFAULT '',
            items_json TEXT NOT NULL DEFAULT '[]',
            subtotal REAL NOT NULL DEFAULT 0,
            tax_type TEXT NOT NULL DEFAULT 'intra',
            gst_rate REAL NOT NULL DEFAULT 18,
            cgst_amount REAL NOT NULL DEFAULT 0,
            sgst_amount REAL NOT NULL DEFAULT 0,
            igst_amount REAL NOT NULL DEFAULT 0,
            total_tax REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT UNIQUE NOT NULL,
            po_date TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            vendor_address TEXT DEFAULT '',
            vendor_gst TEXT DEFAULT '',
            vendor_state TEXT DEFAULT '',
            items_json TEXT NOT NULL DEFAULT '[]',
            subtotal REAL NOT NULL DEFAULT 0,
            tax_type TEXT NOT NULL DEFAULT 'intra',
            gst_rate REAL NOT NULL DEFAULT 18,
            cgst_amount REAL NOT NULL DEFAULT 0,
            sgst_amount REAL NOT NULL DEFAULT 0,
            igst_amount REAL NOT NULL DEFAULT 0,
            total_tax REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS grn_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_number TEXT UNIQUE NOT NULL,
            po_number TEXT NOT NULL,
            grn_date TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            items_json TEXT NOT NULL DEFAULT '[]',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    existing = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if existing == 0:
        for acct in CHART_OF_ACCOUNTS:
            cursor.execute(
                "INSERT INTO accounts (code, name, group_name, type, opening_balance) VALUES (?, ?, ?, ?, ?)",
                (acct["code"], acct["name"], acct["group"], acct["type"], acct["opening"]),
            )

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                   ("company_name", "My Company"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                   ("company_address", ""))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                   ("company_gst", ""))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                   ("company_state", ""))

    conn.commit()
    conn.close()
    return True


def get_setting(key):
    conn = _connect()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else ""


def set_setting(key, value):
    conn = _connect()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def add_account(code, name, group_name, acct_type, opening=0.0):
    valid_types = ("Asset", "Liability", "Equity", "Income", "Expense")
    if acct_type not in valid_types:
        raise ValueError(f"Type must be one of {valid_types}")
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO accounts (code, name, group_name, type, opening_balance) VALUES (?, ?, ?, ?, ?)",
            (code, name, group_name, acct_type, opening),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Account code {code} already exists")
    conn.close()


def get_accounts():
    conn = _connect()
    rows = conn.execute("SELECT * FROM accounts ORDER BY code").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_account_id(code_or_name):
    conn = _connect()
    row = conn.execute(
        "SELECT id FROM accounts WHERE code = ? OR name = ?", (code_or_name, code_or_name)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def add_journal_entry(entry_date, description, lines):
    if not lines:
        raise ValueError("Journal entry must have at least one line")

    total_debit = sum(l.get("debit", 0) or 0 for l in lines)
    total_credit = sum(l.get("credit", 0) or 0 for l in lines)

    if abs(total_debit - total_credit) > 0.01:
        raise ValueError(f"Debits ({total_debit:.2f}) must equal Credits ({total_credit:.2f})")

    conn = _connect()
    date_obj = parse_date(entry_date)
    date_str = format_date(date_obj)
    year = date_obj.year
    seq = conn.execute("SELECT COUNT(*) FROM journal_entries WHERE entry_date LIKE ?", (f"{year}%",)).fetchone()[0] + 1
    entry_number = f"JE-{year}-{seq:04d}"

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO journal_entries (entry_number, entry_date, description) VALUES (?, ?, ?)",
        (entry_number, date_str, description),
    )
    je_id = cursor.lastrowid

    for line in lines:
        account_id = line["account_id"]
        debit = round(line.get("debit", 0) or 0, 2)
        credit = round(line.get("credit", 0) or 0, 2)
        cursor.execute(
            "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
            (je_id, account_id, debit, credit),
        )

    conn.commit()
    conn.close()
    return entry_number


def get_journal_entries(start_date=None, end_date=None):
    conn = _connect()
    query = "SELECT * FROM journal_entries WHERE 1=1"
    params = []
    if start_date:
        query += " AND entry_date >= ?"
        params.append(format_date(parse_date(start_date)))
    if end_date:
        query += " AND entry_date <= ?"
        params.append(format_date(parse_date(end_date)))
    query += " ORDER BY entry_date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_journal_entry_lines(journal_entry_id):
    conn = _connect()
    rows = conn.execute(
        """SELECT jel.*, a.code, a.name, a.group_name
           FROM journal_entry_lines jel
           JOIN accounts a ON a.id = jel.account_id
           WHERE jel.journal_entry_id = ?
           ORDER BY jel.id""",
        (journal_entry_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ledger(account_code_or_name, start_date=None, end_date=None):
    acct = find_account(account_code_or_name)
    if not acct:
        raise ValueError(f"Account not found: {account_code_or_name}")
    account_id = acct["id"]

    conn = _connect()
    query = """
        SELECT je.entry_date, je.entry_number, je.description,
               jel.debit_amount, jel.credit_amount
        FROM journal_entry_lines jel
        JOIN journal_entries je ON je.id = jel.journal_entry_id
        WHERE jel.account_id = ?
    """
    params = [account_id]
    if start_date:
        query += " AND je.entry_date >= ?"
        params.append(format_date(parse_date(start_date)))
    if end_date:
        query += " AND je.entry_date <= ?"
        params.append(format_date(parse_date(end_date)))
    query += " ORDER BY je.entry_date ASC, je.id ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    balance = acct["opening_balance"]
    entries = []
    for r in rows:
        d = dict(r)
        if acct["type"] in ("Asset", "Expense"):
            balance += d["debit_amount"] - d["credit_amount"]
        else:
            balance += d["credit_amount"] - d["debit_amount"]
        d["running_balance"] = round(balance, 2)
        entries.append(d)

    return {"account": acct, "entries": entries, "closing_balance": round(balance, 2)}


def find_account(code_or_name):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM accounts WHERE code = ? OR name = ?", (code_or_name, code_or_name)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_trial_balance(as_on_date=None):
    conn = _connect()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY code").fetchall()
    result = []
    for acct in accounts:
        acct = dict(acct)
        query = """
            SELECT COALESCE(SUM(jel.debit_amount), 0) as total_debit,
                   COALESCE(SUM(jel.credit_amount), 0) as total_credit
            FROM journal_entry_lines jel
            JOIN journal_entries je ON je.id = jel.journal_entry_id
            WHERE jel.account_id = ?
        """
        params = [acct["id"]]
        if as_on_date:
            query += " AND je.entry_date <= ?"
            params.append(format_date(parse_date(as_on_date)))
        totals = conn.execute(query, params).fetchone()

        total_debit = totals["total_debit"]
        total_credit = totals["total_credit"]
        opening = acct["opening_balance"]

        if acct["type"] in ("Asset", "Expense"):
            balance = opening + total_debit - total_credit
        else:
            balance = opening + total_credit - total_debit

        if abs(balance) > 0.005:
            if balance > 0:
                if acct["type"] in ("Asset", "Expense"):
                    dr = round(balance, 2)
                    cr = 0.0
                else:
                    dr = 0.0
                    cr = round(balance, 2)
            else:
                if acct["type"] in ("Asset", "Expense"):
                    dr = 0.0
                    cr = round(abs(balance), 2)
                else:
                    dr = round(abs(balance), 2)
                    cr = 0.0
        else:
            dr, cr = 0.0, 0.0

        result.append({
            "code": acct["code"],
            "name": acct["name"],
            "group_name": acct["group_name"],
            "type": acct["type"],
            "debit": dr,
            "credit": cr,
        })

    conn.close()
    return result


def get_profit_loss(start_date, end_date):
    conn = _connect()
    date_start = format_date(parse_date(start_date))
    date_end = format_date(parse_date(end_date))

    income_accounts = conn.execute(
        "SELECT * FROM accounts WHERE type = 'Income' ORDER BY code"
    ).fetchall()
    expense_accounts = conn.execute(
        "SELECT * FROM accounts WHERE type = 'Expense' ORDER BY code"
    ).fetchall()

    def get_balance(account_id):
        row = conn.execute(
            """SELECT COALESCE(SUM(jel.debit_amount), 0) as dr,
                      COALESCE(SUM(jel.credit_amount), 0) as cr
               FROM journal_entry_lines jel
               JOIN journal_entries je ON je.id = jel.journal_entry_id
               WHERE jel.account_id = ? AND je.entry_date >= ? AND je.entry_date <= ?""",
            (account_id, date_start, date_end),
        ).fetchone()
        return round(row["cr"] - row["dr"], 2)

    incomes = []
    total_income = 0.0
    for acct in income_accounts:
        bal = get_balance(acct["id"])
        if abs(bal) > 0.005:
            incomes.append({"code": acct["code"], "name": acct["name"], "amount": bal})
            total_income += bal

    expenses = []
    total_expense = 0.0
    for acct in expense_accounts:
        bal = get_balance(acct["id"])
        if abs(bal) > 0.005:
            expenses.append({"code": acct["code"], "name": acct["name"], "amount": bal})
            total_expense += bal

    net_profit = round(total_income - total_expense, 2)

    conn.close()
    return {
        "incomes": incomes,
        "total_income": total_income,
        "expenses": expenses,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "start_date": start_date,
        "end_date": end_date,
    }


def get_balance_sheet(as_on_date=None):
    conn = _connect()
    date_limit = format_date(parse_date(as_on_date)) if as_on_date else format_date(date.today())

    accounts = conn.execute("SELECT * FROM accounts ORDER BY code").fetchall()

    def get_balance_upto(account_id, acct_type):
        row = conn.execute(
            """SELECT COALESCE(SUM(jel.debit_amount), 0) as dr,
                      COALESCE(SUM(jel.credit_amount), 0) as cr
               FROM journal_entry_lines jel
               JOIN journal_entries je ON je.id = jel.journal_entry_id
               WHERE jel.account_id = ? AND je.entry_date <= ?""",
            (account_id, date_limit),
        ).fetchone()
        dr = row["dr"]
        cr = row["cr"]
        if acct_type in ("Asset", "Expense"):
            return round(dr - cr, 2)
        return round(cr - dr, 2)

    def get_balance_before(account_id, acct_type):
        row = conn.execute(
            """SELECT COALESCE(SUM(jel.debit_amount), 0) as dr,
                      COALESCE(SUM(jel.credit_amount), 0) as cr
               FROM journal_entry_lines jel
               JOIN journal_entries je ON je.id = jel.journal_entry_id
               WHERE jel.account_id = ? AND je.entry_date < ?""",
            (account_id, date_limit),
        ).fetchone()
        dr = row["dr"]
        cr = row["cr"]
        if acct_type in ("Asset", "Expense"):
            return round(dr - cr, 2)
        return round(cr - dr, 2)

    assets = []
    total_assets = 0.0
    liabilities = []
    total_liabilities = 0.0
    equities = []
    total_equity = 0.0

    for acct_dict in accounts:
        acct = dict(acct_dict)
        bal = acct["opening_balance"] + get_balance_upto(acct["id"], acct["type"])
        if abs(bal) < 0.005:
            continue

        if acct["type"] == "Asset":
            assets.append({"code": acct["code"], "name": acct["name"], "group": acct["group_name"], "amount": round(bal, 2)})
            total_assets += bal
        elif acct["type"] == "Liability":
            liabilities.append({"code": acct["code"], "name": acct["name"], "group": acct["group_name"], "amount": round(bal, 2)})
            total_liabilities += bal
        elif acct["type"] == "Equity":
            if acct["name"] != "Retained Earnings":
                equities.append({"code": acct["code"], "name": acct["name"], "group": acct["group_name"], "amount": round(bal, 2)})
                total_equity += bal

    pl_before = get_profit_loss("2000-01-01", date_limit)
    retained = pl_before["net_profit"]

    retained_row = conn.execute("SELECT id FROM accounts WHERE name = 'Retained Earnings'").fetchone()
    if retained_row and abs(retained) > 0.005:
        equities.append({"code": "20203", "name": "Retained Earnings (Current P&L)", "group": "Equity", "amount": round(retained, 2)})
        total_equity += retained

    conn.close()
    return {
        "assets": assets,
        "total_assets": round(total_assets, 2),
        "liabilities": liabilities,
        "total_liabilities": round(total_liabilities, 2),
        "equities": equities,
        "total_equity": round(total_equity, 2),
        "as_on_date": date_limit,
    }


def add_inventory_item(code, name, unit="nos", opening_stock=0, rate=0.0, hsn_code="", gst_rate=18):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO inventory_items (code, name, unit, opening_stock, rate, hsn_code, gst_rate) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, unit, opening_stock, rate, hsn_code, gst_rate),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Item code {code} already exists")
    conn.close()


def get_inventory_items():
    conn = _connect()
    items = conn.execute("SELECT * FROM inventory_items ORDER BY code").fetchall()
    conn.close()
    result = []
    for item in items:
        d = dict(item)
        d["current_stock"] = get_item_stock(d["id"])
        result.append(d)
    return result


def get_item_stock(item_id):
    conn = _connect()
    ins = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM stock_movements WHERE item_id = ? AND movement_type = 'IN'",
        (item_id,),
    ).fetchone()[0]
    outs = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM stock_movements WHERE item_id = ? AND movement_type = 'OUT'",
        (item_id,),
    ).fetchone()[0]
    conn.close()
    return round(ins - outs, 3)


def add_stock_movement(item_id, movement_date, movement_type, quantity, rate=0.0, reference=""):
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if movement_type == "OUT":
        current = get_item_stock(item_id)
        if quantity > current:
            raise ValueError(f"Insufficient stock: have {current}, need {quantity}")

    date_str = format_date(parse_date(movement_date))
    conn = _connect()
    conn.execute(
        "INSERT INTO stock_movements (item_id, movement_date, movement_type, quantity, rate, reference) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, date_str, movement_type, quantity, rate, reference),
    )
    conn.commit()

    if movement_type == "OUT" and rate > 0:
        item = conn.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,)).fetchone()
        if item:
            fifo_cost = get_fifo_cost(item_id, quantity)
            if fifo_cost > 0:
                cogs_account = conn.execute("SELECT id FROM accounts WHERE name = 'Cost of Goods Sold'").fetchone()
                inventory_account = conn.execute("SELECT id FROM accounts WHERE name = 'Inventory'").fetchone()
                if cogs_account and inventory_account:
                    year = parse_date(date_str).year
                    seq = conn.execute("SELECT COUNT(*) FROM journal_entries WHERE entry_date LIKE ?",
                                       (f"{year}%",)).fetchone()[0] + 1
                    entry_number = f"JE-{year}-{seq:04d}"
                    conn.execute(
                        "INSERT INTO journal_entries (entry_number, entry_date, description) VALUES (?, ?, ?)",
                        (entry_number, date_str, f"COGS for {item['name']} - {reference}"),
                    )
                    je_id = conn.lastrowid
                    conn.execute(
                        "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                        (je_id, cogs_account["id"], fifo_cost, 0),
                    )
                    conn.execute(
                        "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                        (je_id, inventory_account["id"], 0, fifo_cost),
                    )
                    conn.commit()
    conn.close()


def get_fifo_cost(item_id, quantity):
    conn = _connect()
    stock_ins = conn.execute(
        """SELECT id, quantity, rate FROM stock_movements
           WHERE item_id = ? AND movement_type = 'IN'
           ORDER BY movement_date ASC, id ASC""",
        (item_id,),
    ).fetchall()

    remaining = quantity
    total_cost = 0.0
    for si in stock_ins:
        used_qty = min(remaining, si["quantity"])
        total_cost += used_qty * si["rate"]
        remaining -= used_qty
        if remaining <= 0:
            break

    conn.close()
    return round(total_cost, 2)


def get_stock_movements(item_id=None, start_date=None, end_date=None):
    conn = _connect()
    query = """SELECT sm.*, i.name as item_name, i.code as item_code
               FROM stock_movements sm
               JOIN inventory_items i ON i.id = sm.item_id
               WHERE 1=1"""
    params = []
    if item_id:
        query += " AND sm.item_id = ?"
        params.append(item_id)
    if start_date:
        query += " AND sm.movement_date >= ?"
        params.append(format_date(parse_date(start_date)))
    if end_date:
        query += " AND sm.movement_date <= ?"
        params.append(format_date(parse_date(end_date)))
    query += " ORDER BY sm.movement_date DESC, sm.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_bill(bill_type, bill_date, customer_name, customer_address="", customer_gst="",
             customer_state="", items=None, tax_type="intra", gst_rate=18,
             discount=0, status="draft", notes=""):
    if items is None:
        items = []
    if not items:
        raise ValueError("Bill must have at least one item")

    date_obj = parse_date(bill_date)
    date_str = format_date(date_obj)
    year = date_obj.year
    prefix = {"invoice": "INV", "quote": "QTN", "credit_note": "CN"}[bill_type]

    conn = _connect()
    seq = conn.execute("SELECT COUNT(*) FROM bills WHERE bill_type = ? AND bill_date LIKE ?",
                       (bill_type, f"{year}%")).fetchone()[0] + 1
    bill_number = f"{prefix}-{year}-{seq:04d}"

    subtotal = 0.0
    processed_items = []
    for item in items:
        rate = item.get("rate", 0)
        qty = item.get("quantity", 1)
        amount = round(rate * qty, 2)
        subtotal += amount
        processed_items.append({
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "hsn": item.get("hsn", ""),
            "quantity": qty,
            "unit": item.get("unit", "nos"),
            "rate": rate,
            "amount": amount,
        })

    subtotal = round(subtotal, 2)
    discount_amount = round(subtotal * discount / 100, 2) if discount > 0 else 0.0
    taxable_amount = round(subtotal - discount_amount, 2)
    gst = calculate_gst(taxable_amount, gst_rate, tax_type)
    grand_total = round(taxable_amount + gst["total"], 2)

    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO bills (bill_type, bill_number, bill_date, customer_name, customer_address,
           customer_gst, customer_state, items_json, subtotal, tax_type, gst_rate,
           cgst_amount, sgst_amount, igst_amount, total_tax, discount, grand_total, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (bill_type, bill_number, date_str, customer_name, customer_address,
         customer_gst, customer_state, json.dumps(processed_items), subtotal,
         tax_type, gst_rate, gst["cgst"], gst["sgst"], gst["igst"], gst["total"],
         discount_amount, grand_total, status, notes),
    )
    bill_id = cursor.lastrowid

    if bill_type == "invoice" and status.lower() == "confirmed":
        sales_account = conn.execute("SELECT id FROM accounts WHERE name = 'Sales Revenue'").fetchone()
        receivable_account = conn.execute("SELECT id FROM accounts WHERE name = 'Accounts Receivable'").fetchone()
        gst_payable_account = conn.execute("SELECT id FROM accounts WHERE name = 'GST Payable'").fetchone()

        if sales_account and receivable_account:
            year = date_obj.year
            seq2 = conn.execute("SELECT COUNT(*) FROM journal_entries WHERE entry_date LIKE ?",
                                (f"{year}%",)).fetchone()[0] + 1
            entry_number = f"JE-{year}-{seq2:04d}"
            conn.execute(
                "INSERT INTO journal_entries (entry_number, entry_date, description) VALUES (?, ?, ?)",
                (entry_number, date_str, f"Sales - {bill_number} - {customer_name}"),
            )
            je_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                (je_id, receivable_account["id"], grand_total, 0),
            )
            conn.execute(
                "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                (je_id, sales_account["id"], 0, taxable_amount),
            )
            if gst_payable_account:
                if tax_type == "intra":
                    conn.execute(
                        "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                        (je_id, gst_payable_account["id"], 0, gst["cgst"] + gst["sgst"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
                        (je_id, gst_payable_account["id"], 0, gst["igst"]),
                    )
            conn.commit()

    conn.commit()
    conn.close()
    return bill_number


def get_bills(bill_type=None, start_date=None, end_date=None):
    conn = _connect()
    query = "SELECT * FROM bills WHERE 1=1"
    params = []
    if bill_type:
        query += " AND bill_type = ?"
        params.append(bill_type)
    if start_date:
        query += " AND bill_date >= ?"
        params.append(format_date(parse_date(start_date)))
    if end_date:
        query += " AND bill_date <= ?"
        params.append(format_date(parse_date(end_date)))
    query += " ORDER BY bill_date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items_json"])
        result.append(d)
    return result


def generate_invoice_pdf(bill_id):
    conn = _connect()
    bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    conn.close()
    if not bill:
        raise ValueError(f"Bill not found: {bill_id}")
    bill = dict(bill)
    items = json.loads(bill["items_json"])

    pdf = FPDF()
    pdf.add_page()

    company = get_setting("company_name") or "Your Company"
    company_addr = get_setting("company_address") or ""
    company_gst = get_setting("company_gst") or ""

    pdf_heading(pdf, company, 18)
    if company_addr:
        pdf_text(pdf, "Address", company_addr, 9)
    if company_gst:
        pdf_text(pdf, "GSTIN", company_gst, 9)
    pdf.ln(4)

    pdf_heading(pdf, "TAX INVOICE", 14)

    pdf_subheading(pdf, f"Invoice No: {bill['bill_number']}", 11)
    pdf_text(pdf, "Date", bill["bill_date"], 10)
    pdf_text(pdf, "Customer", bill["customer_name"], 10)
    if bill["customer_address"]:
        pdf_text(pdf, "Address", bill["customer_address"], 10)
    if bill["customer_gst"]:
        pdf_text(pdf, "GSTIN", bill["customer_gst"], 10)
    pdf.ln(4)

    col_widths = [10, 60, 15, 25, 25, 30]
    pdf_table_header(pdf, ["#", "Item", "HSN", "Qty", "Rate", "Amount"], col_widths)

    for i, item in enumerate(items, 1):
        pdf_table_row(pdf, [
            str(i),
            item.get("name", ""),
            item.get("hsn", ""),
            f"{item['quantity']} {item.get('unit', '')}",
            format_indian_number(item["rate"]),
            format_indian_number(item["amount"]),
        ], col_widths)

    pdf_line(pdf)
    pdf_text(pdf, "Subtotal", format_indian_rupees(bill["subtotal"]), 10)
    if bill["discount"] > 0:
        pdf_text(pdf, "Discount", format_indian_rupees(bill["discount"]), 10)
    if bill["cgst_amount"] > 0:
        pdf_text(pdf, f"CGST", format_indian_rupees(bill["cgst_amount"]), 10)
    if bill["sgst_amount"] > 0:
        pdf_text(pdf, f"SGST", format_indian_rupees(bill["sgst_amount"]), 10)
    if bill["igst_amount"] > 0:
        pdf_text(pdf, f"IGST", format_indian_rupees(bill["igst_amount"]), 10)
    pdf_text(pdf, "Total Tax", format_indian_rupees(bill["total_tax"]), 10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Grand Total: {format_indian_rupees(bill['grand_total'])}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    if bill["notes"]:
        pdf.ln(4)
        pdf_text(pdf, "Notes", bill["notes"], 9)

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw.encode("latin-1")


def generate_quote_pdf(bill_id):
    conn = _connect()
    bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    conn.close()
    if not bill:
        raise ValueError(f"Quote not found: {bill_id}")
    bill = dict(bill)
    items = json.loads(bill["items_json"])

    pdf = FPDF()
    pdf.add_page()

    company = get_setting("company_name") or "Your Company"
    company_addr = get_setting("company_address") or ""
    company_gst = get_setting("company_gst") or ""

    pdf_heading(pdf, company, 18)
    if company_addr:
        pdf_text(pdf, "Address", company_addr, 9)
    if company_gst:
        pdf_text(pdf, "GSTIN", company_gst, 9)
    pdf.ln(4)

    pdf_heading(pdf, "QUOTATION", 14)

    pdf_subheading(pdf, f"Quote No: {bill['bill_number']}", 11)
    pdf_text(pdf, "Date", bill["bill_date"], 10)
    pdf_text(pdf, "Customer", bill["customer_name"], 10)
    if bill["customer_address"]:
        pdf_text(pdf, "Address", bill["customer_address"], 10)
    pdf.ln(4)

    col_widths = [10, 60, 15, 25, 25, 30]
    pdf_table_header(pdf, ["#", "Item", "HSN", "Qty", "Rate", "Amount"], col_widths)

    for i, item in enumerate(items, 1):
        pdf_table_row(pdf, [
            str(i),
            item.get("name", ""),
            item.get("hsn", ""),
            f"{item['quantity']} {item.get('unit', '')}",
            format_indian_number(item["rate"]),
            format_indian_number(item["amount"]),
        ], col_widths)

    pdf_line(pdf)
    pdf_text(pdf, "Subtotal", format_indian_rupees(bill["subtotal"]), 10)
    pdf_text(pdf, "Total Tax", format_indian_rupees(bill["total_tax"]), 10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Total: {format_indian_rupees(bill['grand_total'])}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    if bill["notes"]:
        pdf.ln(4)
        pdf_text(pdf, "Notes", bill["notes"], 9)

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw.encode("latin-1")


def generate_credit_note_pdf(bill_id):
    conn = _connect()
    bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    conn.close()
    if not bill:
        raise ValueError(f"Credit note not found: {bill_id}")
    bill = dict(bill)
    items = json.loads(bill["items_json"])

    pdf = FPDF()
    pdf.add_page()

    company = get_setting("company_name") or "Your Company"
    pdf_heading(pdf, company, 18)

    company_addr = get_setting("company_address") or ""
    company_gst = get_setting("company_gst") or ""
    if company_addr:
        pdf_text(pdf, "Address", company_addr, 9)
    if company_gst:
        pdf_text(pdf, "GSTIN", company_gst, 9)
    pdf.ln(4)

    pdf_heading(pdf, "CREDIT NOTE", 14)

    pdf_subheading(pdf, f"Credit Note No: {bill['bill_number']}", 11)
    pdf_text(pdf, "Date", bill["bill_date"], 10)
    pdf_text(pdf, "Customer", bill["customer_name"], 10)
    pdf.ln(4)

    col_widths = [10, 60, 15, 25, 25, 30]
    pdf_table_header(pdf, ["#", "Item", "HSN", "Qty", "Rate", "Amount"], col_widths)

    for i, item in enumerate(items, 1):
        pdf_table_row(pdf, [
            str(i),
            item.get("name", ""),
            item.get("hsn", ""),
            f"{item['quantity']} {item.get('unit', '')}",
            format_indian_number(item["rate"]),
            format_indian_number(item["amount"]),
        ], col_widths)

    pdf_line(pdf)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Credit Amount: {format_indian_rupees(bill['grand_total'])}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    if bill["notes"]:
        pdf.ln(4)
        pdf_text(pdf, "Reason", bill["notes"], 9)

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw.encode("latin-1")


def generate_invoice_excel(bill_id):
    import xlsxwriter
    conn = _connect()
    bill = conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
    conn.close()
    if not bill:
        raise ValueError(f"Bill not found: {bill_id}")
    bill = dict(bill)
    items = json.loads(bill["items_json"])

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    bold = workbook.add_format({"bold": True})
    money = workbook.add_format({"num_format": "₹ #,##0.00"})
    sheet = workbook.add_worksheet("Invoice")

    sheet.write(0, 0, get_setting("company_name") or "Your Company", bold)
    sheet.write(1, 0, f"Invoice: {bill['bill_number']}")
    sheet.write(2, 0, f"Date: {bill['bill_date']}")
    sheet.write(3, 0, f"Customer: {bill['customer_name']}")
    sheet.write(4, 0, f"GSTIN: {bill['customer_gst']}")
    sheet.write(6, 0, "Item", bold)
    sheet.write(6, 1, "HSN", bold)
    sheet.write(6, 2, "Qty", bold)
    sheet.write(6, 3, "Rate", bold)
    sheet.write(6, 4, "Amount", bold)

    for i, item in enumerate(items):
        row = 7 + i
        sheet.write(row, 0, item.get("name", ""))
        sheet.write(row, 1, item.get("hsn", ""))
        sheet.write(row, 2, item["quantity"])
        sheet.write(row, 3, item["rate"])
        sheet.write(row, 4, item["amount"])

    footer_row = 7 + len(items) + 1
    sheet.write(footer_row, 3, "Subtotal", bold)
    sheet.write(footer_row, 4, bill["subtotal"], money)
    if bill["discount"] > 0:
        footer_row += 1
        sheet.write(footer_row, 3, "Discount", bold)
        sheet.write(footer_row, 4, bill["discount"], money)
    if bill["cgst_amount"] > 0:
        footer_row += 1
        sheet.write(footer_row, 3, "CGST", bold)
        sheet.write(footer_row, 4, bill["cgst_amount"], money)
    if bill["sgst_amount"] > 0:
        footer_row += 1
        sheet.write(footer_row, 3, "SGST", bold)
        sheet.write(footer_row, 4, bill["sgst_amount"], money)
    if bill["igst_amount"] > 0:
        footer_row += 1
        sheet.write(footer_row, 3, "IGST", bold)
        sheet.write(footer_row, 4, bill["igst_amount"], money)
    footer_row += 1
    sheet.write(footer_row, 3, "Grand Total", bold)
    sheet.write(footer_row, 4, bill["grand_total"], money)

    workbook.close()
    return output.getvalue()


def add_purchase_order(po_date, vendor_name, vendor_address="", vendor_gst="",
                       vendor_state="", items=None, tax_type="intra", gst_rate=18,
                       discount=0, status="pending", notes=""):
    if items is None:
        items = []
    if not items:
        raise ValueError("Purchase order must have at least one item")

    date_obj = parse_date(po_date)
    date_str = format_date(date_obj)
    year = date_obj.year

    conn = _connect()
    seq = conn.execute("SELECT COUNT(*) FROM purchases WHERE po_date LIKE ?",
                       (f"{year}%",)).fetchone()[0] + 1
    po_number = f"PO-{year}-{seq:04d}"

    subtotal = 0.0
    processed_items = []
    for item in items:
        rate = item.get("rate", 0)
        qty = item.get("quantity", 1)
        amount = round(rate * qty, 2)
        subtotal += amount
        processed_items.append({
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "hsn": item.get("hsn", ""),
            "quantity": qty,
            "unit": item.get("unit", "nos"),
            "rate": rate,
            "amount": amount,
        })

    subtotal = round(subtotal, 2)
    discount_amount = round(subtotal * discount / 100, 2) if discount > 0 else 0.0
    taxable_amount = round(subtotal - discount_amount, 2)
    gst = calculate_gst(taxable_amount, gst_rate, tax_type)
    grand_total = round(taxable_amount + gst["total"], 2)

    conn.execute(
        """INSERT INTO purchases (po_number, po_date, vendor_name, vendor_address,
           vendor_gst, vendor_state, items_json, subtotal, tax_type, gst_rate,
           cgst_amount, sgst_amount, igst_amount, total_tax, discount, grand_total, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (po_number, date_str, vendor_name, vendor_address,
         vendor_gst, vendor_state, json.dumps(processed_items), subtotal,
         tax_type, gst_rate, gst["cgst"], gst["sgst"], gst["igst"], gst["total"],
         discount_amount, grand_total, status, notes),
    )
    conn.commit()
    conn.close()
    return po_number


def get_purchase_orders():
    conn = _connect()
    rows = conn.execute("SELECT * FROM purchases ORDER BY po_date DESC, id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items_json"])
        result.append(d)
    return result


def add_grn(grn_date, po_number, vendor_name, items=None, notes=""):
    if items is None:
        items = []
    if not items:
        raise ValueError("GRN must have at least one item")

    date_obj = parse_date(grn_date)
    date_str = format_date(date_obj)
    year = date_obj.year

    conn = _connect()
    seq = conn.execute("SELECT COUNT(*) FROM grn_records WHERE grn_date LIKE ?",
                       (f"{year}%",)).fetchone()[0] + 1
    grn_number = f"GRN-{year}-{seq:04d}"

    conn.execute(
        "INSERT INTO grn_records (grn_number, po_number, grn_date, vendor_name, items_json, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (grn_number, po_number, date_str, vendor_name, json.dumps(items), notes),
    )
    grn_id = conn.lastrowid

    for item in items:
        item_code = item.get("code", "")
        qty = item.get("quantity", 0)
        rate = item.get("rate", 0)
        if qty > 0:
            inv_item = conn.execute(
                "SELECT id FROM inventory_items WHERE code = ?", (item_code,)
            ).fetchone()
            if inv_item:
                conn.execute(
                    "INSERT INTO stock_movements (item_id, movement_date, movement_type, quantity, rate, reference, ref_type, ref_id) VALUES (?, ?, 'IN', ?, ?, ?, 'GRN', ?)",
                    (inv_item["id"], date_str, qty, rate, grn_number, grn_id),
                )

    purchase_account = conn.execute("SELECT id FROM accounts WHERE name = 'Purchases'").fetchone()
    payable_account = conn.execute("SELECT id FROM accounts WHERE name = 'Accounts Payable'").fetchone()
    if purchase_account and payable_account:
        seq2 = conn.execute("SELECT COUNT(*) FROM journal_entries WHERE entry_date LIKE ?",
                            (f"{year}%",)).fetchone()[0] + 1
        entry_number = f"JE-{year}-{seq2:04d}"
        conn.execute(
            "INSERT INTO journal_entries (entry_number, entry_date, description) VALUES (?, ?, ?)",
            (entry_number, date_str, f"Purchase - {grn_number} - {vendor_name}"),
        )
        je_id = conn.lastrowid
        total_amount = sum(item.get("quantity", 0) * item.get("rate", 0) for item in items)
        conn.execute(
            "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
            (je_id, purchase_account["id"], total_amount, 0),
        )
        conn.execute(
            "INSERT INTO journal_entry_lines (journal_entry_id, account_id, debit_amount, credit_amount) VALUES (?, ?, ?, ?)",
            (je_id, payable_account["id"], 0, total_amount),
        )

    conn.commit()
    conn.close()
    return grn_number


def get_grns():
    conn = _connect()
    rows = conn.execute("SELECT * FROM grn_records ORDER BY grn_date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_purchase_register(start_date=None, end_date=None):
    conn = _connect()
    query = "SELECT * FROM purchases WHERE 1=1"
    params = []
    if start_date:
        query += " AND po_date >= ?"
        params.append(format_date(parse_date(start_date)))
    if end_date:
        query += " AND po_date <= ?"
        params.append(format_date(parse_date(end_date)))
    query += " ORDER BY po_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items_json"])
        result.append(d)
    return result


def get_gst_report(start_date, end_date, report_type="sales"):
    conn = _connect()
    date_start = format_date(parse_date(start_date))
    date_end = format_date(parse_date(end_date))

    if report_type == "sales":
        rows = conn.execute(
            "SELECT * FROM bills WHERE bill_type = 'invoice' AND bill_date >= ? AND bill_date <= ? ORDER BY bill_date ASC",
            (date_start, date_end),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM purchases WHERE po_date >= ? AND po_date <= ? ORDER BY po_date ASC",
            (date_start, date_end),
        ).fetchall()

    conn.close()
    result = []
    total_taxable = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_igst = 0.0
    total_amount = 0.0

    for r in rows:
        d = dict(r)
        if report_type == "sales":
            taxable = d["subtotal"] - d["discount"]
            party = d["customer_name"]
            gstin = d["customer_gst"]
            state = d["customer_state"]
            inv_no = d["bill_number"]
            inv_date = d["bill_date"]
        else:
            taxable = d["subtotal"] - d["discount"]
            party = d["vendor_name"]
            gstin = d["vendor_gst"]
            state = d["vendor_state"]
            inv_no = d["po_number"]
            inv_date = d["po_date"]

        result.append({
            "invoice_no": inv_no,
            "date": inv_date,
            "party_name": party,
            "gstin": gstin,
            "state": state,
            "taxable_value": round(taxable, 2),
            "cgst": d["cgst_amount"],
            "sgst": d["sgst_amount"],
            "igst": d["igst_amount"],
            "total_tax": d["total_tax"],
            "grand_total": d["grand_total"],
        })
        total_taxable += taxable
        total_cgst += d["cgst_amount"]
        total_sgst += d["sgst_amount"]
        total_igst += d["igst_amount"]
        total_amount += d["grand_total"]

    return {
        "entries": result,
        "total_taxable": round(total_taxable, 2),
        "total_cgst": round(total_cgst, 2),
        "total_sgst": round(total_sgst, 2),
        "total_igst": round(total_igst, 2),
        "total_tax": round(total_cgst + total_sgst + total_igst, 2),
        "total_amount": round(total_amount, 2),
    }


def get_ageing_report(as_on_date=None, ageing_type="receivable"):
    if as_on_date is None:
        as_on_date = format_date(date.today())
    else:
        as_on_date = format_date(parse_date(as_on_date))

    conn = _connect()

    if ageing_type == "receivable":
        account_name = "Accounts Receivable"
        source_table = "bills"
        type_filter = "invoice"
        party_col = "customer_name"
        date_col = "bill_date"
        amount_col = "grand_total"
        status_filter = " AND status = 'confirmed'"
    else:
        account_name = "Accounts Payable"
        source_table = "purchases"
        type_filter = None
        party_col = "vendor_name"
        date_col = "po_date"
        amount_col = "grand_total"
        status_filter = ""

    acct = conn.execute("SELECT id FROM accounts WHERE name = ?", (account_name,)).fetchone()
    if not acct:
        conn.close()
        return {"entries": [], "totals": {}}

    base_query = f"SELECT DISTINCT {party_col} as party FROM {source_table} WHERE 1=1"
    base_params = []
    if type_filter:
        base_query += f" AND bill_type = ?"
        base_params.append(type_filter)
    base_query += status_filter

    parties = conn.execute(base_query, base_params).fetchall()
    entries = []
    total_0_30 = 0.0
    total_31_60 = 0.0
    total_61_90 = 0.0
    total_91_plus = 0.0
    total_outstanding = 0.0

    for p in parties:
        party = p["party"]
        query = f"""
            SELECT COALESCE(SUM({amount_col}), 0) as outstanding,
                   MIN({date_col}) as oldest_date
            FROM {source_table}
            WHERE {party_col} = ?
        """
        q_params = [party]
        if type_filter:
            query += f" AND bill_type = ?"
            q_params.append(type_filter)
        query += status_filter

        row = conn.execute(query, q_params).fetchone()
        outstanding = round(row["outstanding"], 2)
        if outstanding <= 0:
            continue

        oldest = row["oldest_date"]
        if oldest:
            days = (parse_date(as_on_date) - parse_date(oldest)).days
        else:
            days = 0

        if days <= 30:
            bucket = "0-30"
            total_0_30 += outstanding
        elif days <= 60:
            bucket = "31-60"
            total_31_60 += outstanding
        elif days <= 90:
            bucket = "61-90"
            total_61_90 += outstanding
        else:
            bucket = "91+"
            total_91_plus += outstanding

        total_outstanding += outstanding

        entries.append({
            "party": party,
            "outstanding": outstanding,
            "days_overdue": days,
            "bucket": bucket,
        })

    conn.close()
    entries.sort(key=lambda x: x["days_overdue"], reverse=True)

    return {
        "entries": entries,
        "totals": {
            "0-30": round(total_0_30, 2),
            "31-60": round(total_31_60, 2),
            "61-90": round(total_61_90, 2),
            "91+": round(total_91_plus, 2),
            "total": round(total_outstanding, 2),
        },
    }


def get_daybook(book_date):
    date_str = format_date(parse_date(book_date))

    conn = _connect()
    entries = conn.execute(
        """SELECT je.* FROM journal_entries je WHERE je.entry_date = ? ORDER BY je.id""",
        (date_str,),
    ).fetchall()
    conn.close()

    result = []
    for je in entries:
        je = dict(je)
        lines = get_journal_entry_lines(je["id"])
        je["lines"] = lines
        result.append(je)
    return result


def generate_po_pdf(po_id):
    conn = _connect()
    po = conn.execute("SELECT * FROM purchases WHERE id = ?", (po_id,)).fetchone()
    conn.close()
    if not po:
        raise ValueError(f"Purchase order not found: {po_id}")
    po = dict(po)
    items = json.loads(po["items_json"])

    pdf = FPDF()
    pdf.add_page()

    company = get_setting("company_name") or "Your Company"
    company_addr = get_setting("company_address") or ""
    company_gst = get_setting("company_gst") or ""

    pdf_heading(pdf, company, 18)
    if company_addr:
        pdf_text(pdf, "Address", company_addr, 9)
    pdf.ln(4)

    pdf_heading(pdf, "PURCHASE ORDER", 14)

    pdf_subheading(pdf, f"PO No: {po['po_number']}", 11)
    pdf_text(pdf, "Date", po["po_date"], 10)
    pdf_text(pdf, "Vendor", po["vendor_name"], 10)
    if po["vendor_address"]:
        pdf_text(pdf, "Address", po["vendor_address"], 10)
    if po["vendor_gst"]:
        pdf_text(pdf, "GSTIN", po["vendor_gst"], 10)
    pdf.ln(4)

    col_widths = [10, 60, 15, 25, 25, 30]
    pdf_table_header(pdf, ["#", "Item", "HSN", "Qty", "Rate", "Amount"], col_widths)

    for i, item in enumerate(items, 1):
        pdf_table_row(pdf, [
            str(i),
            item.get("name", ""),
            item.get("hsn", ""),
            f"{item['quantity']} {item.get('unit', '')}",
            format_indian_number(item["rate"]),
            format_indian_number(item["amount"]),
        ], col_widths)

    pdf_line(pdf)
    pdf_text(pdf, "Subtotal", format_indian_rupees(po["subtotal"]), 10)
    if po["discount"] > 0:
        pdf_text(pdf, "Discount", format_indian_rupees(po["discount"]), 10)
    pdf_text(pdf, "Total Tax", format_indian_rupees(po["total_tax"]), 10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Grand Total: {format_indian_rupees(po['grand_total'])}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    if po["notes"]:
        pdf.ln(4)
        pdf_text(pdf, "Notes", po["notes"], 9)

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw.encode("latin-1")
