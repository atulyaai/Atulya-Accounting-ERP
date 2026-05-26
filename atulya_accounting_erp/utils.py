import re
import os
from datetime import datetime, date


DB_PATH = None


def get_db_path():
    if DB_PATH is not None:
        return DB_PATH
    user_dir = os.path.expanduser("~")
    app_dir = os.path.join(user_dir, ".atulya-erp")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "erp_data.db")


def set_db_path(path):
    global DB_PATH
    DB_PATH = path


def validate_date(date_str):
    if isinstance(date_str, (datetime, date)):
        return True
    if not isinstance(date_str, str):
        return False
    patterns = [
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{2}-\d{2}-\d{4}$",
        r"^\d{2}/\d{2}/\d{4}$",
    ]
    return any(re.match(p, date_str) for p in patterns)


def parse_date(date_str):
    if isinstance(date_str, (datetime, date)):
        if isinstance(date_str, datetime):
            return date_str.date()
        return date_str
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def format_date(date_obj):
    if isinstance(date_obj, str):
        date_obj = parse_date(date_obj)
    return date_obj.strftime("%Y-%m-%d") if hasattr(date_obj, "strftime") else str(date_obj)


def display_date(date_obj):
    if isinstance(date_obj, str):
        date_obj = parse_date(date_obj)
    return date_obj.strftime("%d-%m-%Y") if hasattr(date_obj, "strftime") else str(date_obj)


def format_indian_number(value):
    if value is None:
        return "0.00"
    negative = False
    if value < 0:
        negative = True
        value = abs(value)

    integer_part = int(value)
    decimal_part = int(round((value - integer_part) * 100))

    int_str = str(integer_part)
    if len(int_str) <= 3:
        result = int_str
    else:
        last_three = int_str[-3:]
        rest = int_str[:-3]
        rest_groups = []
        while len(rest) > 2:
            rest_groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            rest_groups.append(rest)
        rest_groups.reverse()
        result = ",".join(rest_groups) + "," + last_three

    decimal_str = f"{decimal_part:02d}"
    formatted = f"{result}.{decimal_str}"
    if negative:
        formatted = f"({formatted})"
    return formatted


def format_indian_rupees(value):
    return f"Rs. {format_indian_number(value)}"


def calculate_gst(amount, rate=18, tax_type="intra"):
    if tax_type == "intra":
        cgst = amount * rate / 2 / 100
        sgst = amount * rate / 2 / 100
        igst = 0.0
    else:
        cgst = 0.0
        sgst = 0.0
        igst = amount * rate / 100
    return {"cgst": round(cgst, 2), "sgst": round(sgst, 2), "igst": round(igst, 2), "total": round(cgst + sgst + igst, 2)}


def calculate_tds(amount, rate=10):
    return round(amount * rate / 100, 2)


def pdf_heading(pdf, text, size=16):
    pdf.set_font("Helvetica", "B", size)
    pdf.cell(0, 10, text, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def pdf_subheading(pdf, text, size=12):
    pdf.set_font("Helvetica", "B", size)
    pdf.cell(0, 8, text, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def pdf_text(pdf, label, value, size=10):
    pdf.set_font("Helvetica", "", size)
    pdf.cell(0, 6, f"{label}: {value}", align="L", new_x="LMARGIN", new_y="NEXT")


def pdf_table_header(pdf, headers, col_widths, size=9):
    pdf.set_font("Helvetica", "B", size)
    pdf.set_fill_color(220, 220, 220)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, align="C", fill=True)
    pdf.ln()


def pdf_table_row(pdf, cells, col_widths, size=9):
    pdf.set_font("Helvetica", "", size)
    for i, cell in enumerate(cells):
        pdf.cell(col_widths[i], 7, str(cell), border=1, align="C" if i > 0 else "L")
    pdf.ln()


def pdf_line(pdf):
    y = pdf.get_y()
    pdf.line(10, y, 200, y)
    pdf.ln(3)
