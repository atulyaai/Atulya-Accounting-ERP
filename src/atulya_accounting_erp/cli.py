import os
import sys
import json
from datetime import date

import click

from atulya_accounting_erp import __version__
from atulya_accounting_erp.core import (
    init_database, add_account, get_accounts, find_account,
    add_journal_entry, get_journal_entries, get_journal_entry_lines,
    get_ledger, get_trial_balance, get_profit_loss, get_balance_sheet,
    add_inventory_item, get_inventory_items, add_stock_movement,
    get_stock_movements, add_bill, get_bills,
    generate_invoice_pdf, generate_quote_pdf, generate_credit_note_pdf,
    generate_invoice_excel, add_purchase_order, get_purchase_orders,
    add_grn, get_grns, get_purchase_register,
    get_gst_report, get_ageing_report, get_daybook,
    generate_po_pdf,
)
from atulya_accounting_erp.utils import (
    format_indian_number, format_indian_rupees, display_date,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="Atulya ERP")
def main():
    pass


main.epilog = "Run 'atulya-erp COMMAND --help' for more information."


@main.command()
@click.option("--dir", "-d", default=None, help="Directory to store ERP data (default: ~/.atulya-erp)")
def init(dir):
    """Initialize new ERP data store with sample chart of accounts."""
    try:
        init_database(data_dir=dir)
        if dir:
            click.echo(f"Initialized ERP database at {os.path.join(dir, 'erp_data.db')}")
        else:
            click.echo("Initialized ERP database with default chart of accounts.")
        click.echo("Sample accounts created: Cash, Bank, Accounts Receivable, etc.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def accounts():
    """Manage accounts and financial statements."""
    pass


@accounts.command()
@click.argument("account")
@click.option("--from", "-f", "start_date", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--to", "-t", "end_date", default=None, help="End date (YYYY-MM-DD)")
def ledger(account, start_date, end_date):
    """Show ledger for an account (by code or name)."""
    try:
        data = get_ledger(account, start_date, end_date)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    acct = data["account"]
    click.echo(f"\n{'='*70}")
    click.echo(f"LEDGER: {acct['name']} ({acct['code']})")
    click.echo(f"Group: {acct['group_name']}  |  Type: {acct['type']}")
    click.echo(f"Opening Balance: {format_indian_rupees(acct['opening_balance'])}")
    click.echo(f"{'='*70}")
    click.echo(f"{'Date':<14} {'Entry':<16} {'Description':<20} {'Debit':<12} {'Credit':<12} {'Balance':<12}")
    click.echo("-" * 86)

    for entry in data["entries"]:
        click.echo(
            f"{display_date(entry['entry_date']):<14} "
            f"{entry['entry_number']:<16} "
            f"{entry['description'][:18]:<20} "
            f"{format_indian_number(entry['debit_amount']):<12} "
            f"{format_indian_number(entry['credit_amount']):<12} "
            f"{format_indian_number(entry['running_balance']):<12}"
        )

    click.echo("-" * 86)
    click.echo(f"{'Closing Balance:':<62} {format_indian_rupees(data['closing_balance'])}")


@accounts.command()
@click.option("--on", "-o", "as_on_date", default=None, help="As on date (YYYY-MM-DD)")
def trial_balance(as_on_date):
    """Generate trial balance."""
    data = get_trial_balance(as_on_date)
    click.echo(f"\n{'='*60}")
    click.echo("TRIAL BALANCE")
    if as_on_date:
        click.echo(f"As on: {display_date(as_on_date)}")
    click.echo(f"{'='*60}")
    click.echo(f"{'Code':<8} {'Account':<30} {'Debit':<12} {'Credit':<12}")
    click.echo("-" * 62)

    total_dr = 0.0
    total_cr = 0.0
    for row in data:
        if row["debit"] > 0 or row["credit"] > 0:
            click.echo(
                f"{row['code']:<8} {row['name']:<30} {format_indian_number(row['debit']):<12} {format_indian_number(row['credit']):<12}"
            )
            total_dr += row["debit"]
            total_cr += row["credit"]

    click.echo("-" * 62)
    click.echo(f"{'':<8} {'TOTAL':<30} {format_indian_number(total_dr):<12} {format_indian_number(total_cr):<12}")
    click.echo(f"{'':<8} {'Difference:':<30} {format_indian_number(abs(total_dr - total_cr)):<12}")


@accounts.command()
@click.option("--from", "-f", "start_date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--to", "-t", "end_date", required=True, help="End date (YYYY-MM-DD)")
def pl(start_date, end_date):
    """Generate Profit & Loss statement."""
    data = get_profit_loss(start_date, end_date)
    click.echo(f"\n{'='*55}")
    click.echo(f"PROFIT & LOSS STATEMENT")
    click.echo(f"Period: {display_date(data['start_date'])} to {display_date(data['end_date'])}")
    click.echo(f"{'='*55}")

    click.echo(f"\nINCOME:")
    click.echo(f"{'Code':<8} {'Account':<30} {'Amount':<12}")
    click.echo("-" * 50)
    for inc in data["incomes"]:
        click.echo(f"{inc['code']:<8} {inc['name']:<30} {format_indian_rupees(inc['amount']):<12}")
    click.echo("-" * 50)
    click.echo(f"{'':<8} {'Total Income':<30} {format_indian_rupees(data['total_income']):<12}")

    click.echo(f"\nEXPENSES:")
    click.echo(f"{'Code':<8} {'Account':<30} {'Amount':<12}")
    click.echo("-" * 50)
    for exp in data["expenses"]:
        click.echo(f"{exp['code']:<8} {exp['name']:<30} {format_indian_rupees(exp['amount']):<12}")
    click.echo("-" * 50)
    click.echo(f"{'':<8} {'Total Expenses':<30} {format_indian_rupees(data['total_expense']):<12}")

    click.echo(f"\n{'='*55}")
    if data["net_profit"] >= 0:
        click.echo(f"NET PROFIT: {format_indian_rupees(data['net_profit'])}")
    else:
        click.echo(f"NET LOSS: {format_indian_rupees(abs(data['net_profit']))}")


@accounts.command()
@click.option("--on", "-o", "as_on_date", default=None, help="As on date (YYYY-MM-DD)")
def balance_sheet(as_on_date):
    """Generate Balance Sheet."""
    data = get_balance_sheet(as_on_date)
    click.echo(f"\n{'='*55}")
    click.echo("BALANCE SHEET")
    click.echo(f"As on: {display_date(data['as_on_date'])}")
    click.echo(f"{'='*55}")

    click.echo(f"\nEQUITY & LIABILITIES:")
    click.echo(f"{'Code':<8} {'Account':<30} {'Amount':<12}")
    click.echo("-" * 50)
    for eq in data["equities"]:
        click.echo(f"{eq['code']:<8} {eq['name']:<30} {format_indian_rupees(eq['amount']):<12}")
    click.echo("-" * 50)
    click.echo(f"{'':<8} {'Total Equity':<30} {format_indian_rupees(data['total_equity']):<12}")

    click.echo("")
    for li in data["liabilities"]:
        click.echo(f"{li['code']:<8} {li['name']:<30} {format_indian_rupees(li['amount']):<12}")
    click.echo("-" * 50)
    click.echo(f"{'':<8} {'Total Liabilities':<30} {format_indian_rupees(data['total_liabilities']):<12}")
    click.echo("-" * 50)
    total_eq_li = data["total_equity"] + data["total_liabilities"]
    click.echo(f"{'':<8} {'TOTAL':<30} {format_indian_rupees(total_eq_li):<12}")

    click.echo(f"\nASSETS:")
    click.echo(f"{'Code':<8} {'Account':<30} {'Amount':<12}")
    click.echo("-" * 50)
    for asset in data["assets"]:
        click.echo(f"{asset['code']:<8} {asset['name']:<30} {format_indian_rupees(asset['amount']):<12}")
    click.echo("-" * 50)
    click.echo(f"{'':<8} {'TOTAL ASSETS':<30} {format_indian_rupees(data['total_assets']):<12}")

    click.echo(f"\n{'='*55}")
    diff = round(total_eq_li - data["total_assets"], 2)
    click.echo(f"Difference (Balancing Figure): {format_indian_rupees(diff)}")


@accounts.command()
@click.option("--date", "-d", "entry_date", required=True, help="Entry date (YYYY-MM-DD)")
@click.option("--desc", "-n", "description", required=True, help="Description")
@click.option("--lines", "-l", "lines_json", required=True,
              help='JSON array: [{"account":"Cash","debit":1000},{"account":"Sales Revenue","credit":1000}]')
def journal(entry_date, description, lines_json):
    """Add a journal entry (double-entry)."""
    try:
        raw_lines = json.loads(lines_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    lines = []
    for raw in raw_lines:
        acct = find_account(raw["account"])
        if not acct:
            click.echo(f"Error: Account '{raw['account']}' not found", err=True)
            sys.exit(1)
        lines.append({
            "account_id": acct["id"],
            "debit": raw.get("debit", 0),
            "credit": raw.get("credit", 0),
        })

    try:
        entry_number = add_journal_entry(entry_date, description, lines)
        click.echo(f"Journal entry created: {entry_number}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def inventory():
    """Manage inventory items and stock."""
    pass


@inventory.command(name="list")
def inventory_list():
    """List all inventory items with stock levels."""
    items = get_inventory_items()
    if not items:
        click.echo("No inventory items found.")
        return

    click.echo(f"\n{'Code':<10} {'Name':<30} {'Unit':<8} {'Stock':<12} {'Rate':<12} {'GST':<6}")
    click.echo("-" * 78)
    for item in items:
        click.echo(
            f"{item['code']:<10} {item['name']:<30} {item['unit']:<8} "
            f"{format_indian_number(item['current_stock']):<12} "
            f"{format_indian_rupees(item['rate']):<12} "
            f"{item['gst_rate']}%"
        )


@inventory.command()
@click.option("--code", "-c", required=True, help="Item code")
@click.option("--name", "-n", required=True, help="Item name")
@click.option("--unit", "-u", default="nos", help="Unit of measure")
@click.option("--stock", "-s", "opening_stock", type=float, default=0, help="Opening stock quantity")
@click.option("--rate", "-r", type=float, default=0, help="Rate/price")
@click.option("--hsn", default="", help="HSN/SAC code")
@click.option("--gst", "gst_rate", type=float, default=18, help="GST rate percentage")
def add(code, name, unit, opening_stock, rate, hsn, gst_rate):
    """Add an item to inventory."""
    try:
        add_inventory_item(code, name, unit, opening_stock, rate, hsn, gst_rate)
        click.echo(f"Added inventory item: {code} - {name}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@inventory.command()
@click.option("--code", "-c", required=True, help="Item code")
def stock(code):
    """Check stock levels for an item."""
    items = get_inventory_items()
    for item in items:
        if item["code"] == code:
            click.echo(f"{item['name']} ({item['code']}): {format_indian_number(item['current_stock'])} {item['unit']}")
            click.echo(f"Rate: {format_indian_rupees(item['rate'])}")
            return
    click.echo(f"Item not found: {code}", err=True)
    sys.exit(1)


@inventory.command()
@click.option("--code", "-c", default=None, help="Item code to filter")
@click.option("--from", "-f", "start_date", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--to", "-t", "end_date", default=None, help="End date (YYYY-MM-DD)")
def movement(code, start_date, end_date):
    """Show stock movement report."""
    item_id = None
    if code:
        acct = find_account(code)
        if not acct:
            for item in get_inventory_items():
                if item["code"] == code:
                    item_id = item["id"]
                    break
        if not item_id:
            click.echo(f"Item not found: {code}", err=True)
            sys.exit(1)

    movements = get_stock_movements(item_id, start_date, end_date)
    if not movements:
        click.echo("No stock movements found.")
        return

    click.echo(f"\n{'Date':<14} {'Type':<6} {'Item':<25} {'Qty':<12} {'Rate':<12} {'Ref':<20}")
    click.echo("-" * 89)
    for m in movements:
        click.echo(
            f"{display_date(m['movement_date']):<14} {m['movement_type']:<6} "
            f"{m['item_name']:<25} {format_indian_number(m['quantity']):<12} "
            f"{format_indian_rupees(m['rate']):<12} {m['reference']:<20}"
        )


@main.group()
def billing():
    """Generate invoices, quotes, and credit notes."""
    pass


@billing.command()
@click.option("--customer", "-c", required=True, help="Customer name")
@click.option("--address", "-a", default="", help="Customer address")
@click.option("--gstin", "-g", default="", help="Customer GSTIN")
@click.option("--state", "-s", default="", help="Customer state")
@click.option("--items", "-i", "items_json", required=True,
              help='JSON: [{"name":"Item","hsn":"","quantity":1,"rate":100,"unit":"nos"}]')
@click.option("--date", "-d", "bill_date", default=None, help="Invoice date (YYYY-MM-DD)")
@click.option("--tax", "-t", "tax_type", default="intra", type=click.Choice(["intra", "inter"]),
              help="Tax type (intra/inter-state)")
@click.option("--gst", "gst_rate", type=float, default=18, help="GST rate percentage")
@click.option("--discount", "-dsc", type=float, default=0, help="Discount percentage")
@click.option("--status", default="draft", help="Status (draft/confirmed)")
@click.option("--notes", default="", help="Additional notes")
@click.option("--output", "-o", default=None, help="Save PDF to file")
def invoice(bill_date, customer, address, gstin, state, items_json,
            tax_type, gst_rate, discount, status, notes, output):
    """Generate an invoice (PDF/Excel)."""
    if bill_date is None:
        bill_date = str(date.today())

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    try:
        bill_no = add_bill("invoice", bill_date, customer, address, gstin, state,
                           items, tax_type, gst_rate, discount, status, notes)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    bills = get_bills("invoice")
    bill_id = next(b for b in bills if b["bill_number"] == bill_no)["id"]

    pdf_bytes = generate_invoice_pdf(bill_id)
    if output:
        with open(output, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Invoice {bill_no} saved to {output}")
    else:
        out_name = f"{bill_no}.pdf"
        with open(out_name, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Invoice {bill_no} generated -> {out_name}")


@billing.command()
@click.option("--customer", "-c", required=True, help="Customer name")
@click.option("--address", "-a", default="", help="Customer address")
@click.option("--gstin", "-g", default="", help="Customer GSTIN")
@click.option("--items", "-i", "items_json", required=True,
              help='JSON: [{"name":"Item","hsn":"","quantity":1,"rate":100}]')
@click.option("--date", "-d", "bill_date", default=None, help="Quote date")
@click.option("--tax", "-t", "tax_type", default="intra", type=click.Choice(["intra", "inter"]))
@click.option("--gst", "gst_rate", type=float, default=18, help="GST rate")
@click.option("--discount", "-dsc", type=float, default=0)
@click.option("--notes", default="")
@click.option("--output", "-o", default=None, help="Save PDF to file")
def quote(bill_date, customer, address, gstin, items_json,
          tax_type, gst_rate, discount, notes, output):
    """Generate a quotation."""
    if bill_date is None:
        bill_date = str(date.today())

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    try:
        bill_no = add_bill("quote", bill_date, customer, address, gstin, "",
                           items, tax_type, gst_rate, discount, "draft", notes)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    bills = get_bills("quote")
    bill_id = next(b for b in bills if b["bill_number"] == bill_no)["id"]

    pdf_bytes = generate_quote_pdf(bill_id)
    if output:
        with open(output, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Quote {bill_no} saved to {output}")
    else:
        out_name = f"{bill_no}.pdf"
        with open(out_name, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Quote {bill_no} generated -> {out_name}")


@billing.command()
@click.option("--customer", "-c", required=True, help="Customer name")
@click.option("--items", "-i", "items_json", required=True,
              help='JSON: [{"name":"Item","quantity":1,"rate":100}]')
@click.option("--date", "-d", "bill_date", default=None, help="Credit note date")
@click.option("--reason", "-r", "notes", default="", help="Reason for credit note")
@click.option("--output", "-o", default=None, help="Save PDF to file")
def credit_note(bill_date, customer, items_json, notes, output):
    """Generate a credit note."""
    if bill_date is None:
        bill_date = str(date.today())

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    try:
        bill_no = add_bill("credit_note", bill_date, customer, "", "", "",
                           items, "intra", 18, 0, "draft", notes)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    bills = get_bills("credit_note")
    bill_id = next(b for b in bills if b["bill_number"] == bill_no)["id"]

    pdf_bytes = generate_credit_note_pdf(bill_id)
    if output:
        with open(output, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Credit note {bill_no} saved to {output}")
    else:
        out_name = f"{bill_no}.pdf"
        with open(out_name, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"Credit note {bill_no} generated -> {out_name}")


@billing.command(name="list")
def billing_list():
    """List all bills (invoices, quotes, credit notes)."""
    for btype in ("invoice", "quote", "credit_note"):
        bills = get_bills(btype)
        if bills:
            click.echo(f"\n--- {btype.upper()}S ---")
            click.echo(f"{'No':<20} {'Date':<14} {'Customer':<25} {'Amount':<14} {'Status':<12}")
            click.echo("-" * 85)
            for b in bills:
                click.echo(
                    f"{b['bill_number']:<20} {display_date(b['bill_date']):<14} "
                    f"{b['customer_name']:<25} {format_indian_rupees(b['grand_total']):<14} "
                    f"{b['status']:<12}"
                )


@main.group()
def purchases():
    """Manage purchases, POs, and GRNs."""
    pass


@purchases.command()
@click.option("--vendor", "-v", required=True, help="Vendor name")
@click.option("--address", "-a", default="", help="Vendor address")
@click.option("--gstin", "-g", default="", help="Vendor GSTIN")
@click.option("--state", "-s", default="", help="Vendor state")
@click.option("--items", "-i", "items_json", required=True,
              help='JSON: [{"name":"Item","hsn":"","quantity":1,"rate":100}]')
@click.option("--date", "-d", "po_date", default=None, help="PO date")
@click.option("--tax", "-t", "tax_type", default="intra", type=click.Choice(["intra", "inter"]))
@click.option("--gst", "gst_rate", type=float, default=18)
@click.option("--discount", "-dsc", type=float, default=0)
@click.option("--status", default="pending", help="Status (pending/approved/received)")
@click.option("--notes", default="")
@click.option("--output", "-o", default=None, help="Save PDF to file")
def po(po_date, vendor, address, gstin, state, items_json,
       tax_type, gst_rate, discount, status, notes, output):
    """Generate a purchase order."""
    if po_date is None:
        po_date = str(date.today())

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    try:
        po_no = add_purchase_order(po_date, vendor, address, gstin, state,
                                   items, tax_type, gst_rate, discount, status, notes)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    pos = get_purchase_orders()
    po_id = next(p for p in pos if p["po_number"] == po_no)["id"]

    pdf_bytes = generate_po_pdf(po_id)
    if output:
        with open(output, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"PO {po_no} saved to {output}")
    else:
        out_name = f"{po_no}.pdf"
        with open(out_name, "wb") as f:
            f.write(pdf_bytes)
        click.echo(f"PO {po_no} generated -> {out_name}")


@purchases.command()
@click.option("--po", "-p", "po_number", required=True, help="Purchase order number")
@click.option("--vendor", "-v", required=True, help="Vendor name")
@click.option("--items", "-i", "items_json", required=True,
              help='JSON: [{"code":"ITEM01","quantity":10,"rate":100}]')
@click.option("--date", "-d", "grn_date", default=None, help="GRN date")
@click.option("--notes", default="")
def grn(grn_date, po_number, vendor, items_json, notes):
    """Record a goods receipt note (adds to inventory)."""
    if grn_date is None:
        grn_date = str(date.today())

    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON: {e}", err=True)
        sys.exit(1)

    try:
        grn_no = add_grn(grn_date, po_number, vendor, items, notes)
        click.echo(f"GRN {grn_no} recorded. Stock updated.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@purchases.command()
@click.option("--from", "-f", "start_date", default=None, help="Start date")
@click.option("--to", "-t", "end_date", default=None, help="End date")
def register(start_date, end_date):
    """Purchase register report."""
    data = get_purchase_register(start_date, end_date)
    if not data:
        click.echo("No purchase orders found.")
        return

    click.echo(f"\n{'PO No':<16} {'Date':<14} {'Vendor':<25} {'Amount':<14} {'Status':<12}")
    click.echo("-" * 81)
    total = 0.0
    for po in data:
        click.echo(
            f"{po['po_number']:<16} {display_date(po['po_date']):<14} "
            f"{po['vendor_name']:<25} {format_indian_rupees(po['grand_total']):<14} "
            f"{po['status']:<12}"
        )
        total += po["grand_total"]
    click.echo("-" * 81)
    click.echo(f"{'TOTAL':<55} {format_indian_rupees(total):<14}")


@main.group()
def reports():
    """Generate reports: GST, ageing, daybook."""
    pass


@reports.command()
@click.option("--from", "-f", "start_date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--to", "-t", "end_date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--type", "-y", "report_type", default="sales",
              type=click.Choice(["sales", "purchase"]), help="Report type")
def gst(start_date, end_date, report_type):
    """GST-compliant sales/purchase report."""
    data = get_gst_report(start_date, end_date, report_type)

    click.echo(f"\n{'='*100}")
    click.echo(f"GST {'SALES' if report_type == 'sales' else 'PURCHASE'} REPORT")
    click.echo(f"Period: {display_date(start_date)} to {display_date(end_date)}")
    click.echo(f"{'='*100}")

    if not data["entries"]:
        click.echo("No entries found.")
        return

    click.echo(
        f"{'Invoice':<18} {'Date':<12} {'Party':<22} {'GSTIN':<18} "
        f"{'Taxable':<12} {'CGST':<10} {'SGST':<10} {'IGST':<10} {'Total':<12}"
    )
    click.echo("-" * 124)

    for e in data["entries"]:
        click.echo(
            f"{e['invoice_no']:<18} {display_date(e['date']):<12} "
            f"{e['party_name']:<22} {e['gstin']:<18} "
            f"{format_indian_number(e['taxable_value']):<12} "
            f"{format_indian_number(e['cgst']):<10} "
            f"{format_indian_number(e['sgst']):<10} "
            f"{format_indian_number(e['igst']):<10} "
            f"{format_indian_number(e['grand_total']):<12}"
        )

    click.echo("-" * 124)
    click.echo(
        f"{'':<58} {format_indian_number(data['total_taxable']):<12} "
        f"{format_indian_number(data['total_cgst']):<10} "
        f"{format_indian_number(data['total_sgst']):<10} "
        f"{format_indian_number(data['total_igst']):<10} "
        f"{format_indian_number(data['total_amount']):<12}"
    )


@reports.command()
@click.option("--on", "-o", "as_on_date", default=None, help="As on date (YYYY-MM-DD)")
@click.option("--type", "-t", "ageing_type", default="receivable",
              type=click.Choice(["receivable", "payable"]), help="Ageing type")
def ageing(as_on_date, ageing_type):
    """Accounts receivable/payable ageing."""
    data = get_ageing_report(as_on_date, ageing_type)

    title = "RECEIVABLE" if ageing_type == "receivable" else "PAYABLE"
    click.echo(f"\n{'='*70}")
    click.echo(f"ACCOUNTS {title} AGEING")
    if as_on_date:
        click.echo(f"As on: {display_date(as_on_date)}")
    click.echo(f"{'='*70}")

    if not data["entries"]:
        click.echo("No entries found.")
        return

    click.echo(f"\n{'Party':<30} {'Outstanding':<14} {'Days':<8} {'Bucket':<10}")
    click.echo("-" * 62)

    for e in data["entries"]:
        click.echo(
            f"{e['party']:<30} {format_indian_rupees(e['outstanding']):<14} "
            f"{e['days_overdue']:<8} {e['bucket']:<10}"
        )

    click.echo("\nBucket Summary:")
    click.echo(f"  0-30 days:  {format_indian_rupees(data['totals']['0-30'])}")
    click.echo(f"  31-60 days: {format_indian_rupees(data['totals']['31-60'])}")
    click.echo(f"  61-90 days: {format_indian_rupees(data['totals']['61-90'])}")
    click.echo(f"  91+ days:   {format_indian_rupees(data['totals']['91+'])}")
    click.echo(f"  TOTAL:      {format_indian_rupees(data['totals']['total'])}")


@reports.command()
@click.option("--date", "-d", "report_date", default=None, help="Date (YYYY-MM-DD)")
def daybook(report_date):
    """Day book / cash book for a given date."""
    if report_date is None:
        report_date = str(date.today())

    entries = get_daybook(report_date)
    click.echo(f"\n{'='*60}")
    click.echo(f"DAY BOOK - {display_date(report_date)}")
    click.echo(f"{'='*60}")

    if not entries:
        click.echo("No journal entries for this date.")
        return

    for je in entries:
        click.echo(f"\n{je['entry_number']} | {je['description']}")
        click.echo(f"{'Account':<30} {'Debit':<12} {'Credit':<12}")
        click.echo("-" * 54)
        for line in je["lines"]:
            click.echo(
                f"{line['name']:<30} "
                f"{format_indian_number(line['debit_amount']):<12} "
                f"{format_indian_number(line['credit_amount']):<12}"
            )
        click.echo("-" * 54)
        total_dr = sum(l["debit_amount"] for l in je["lines"])
        total_cr = sum(l["credit_amount"] for l in je["lines"])
        click.echo(f"{'Total':<30} {format_indian_number(total_dr):<12} {format_indian_number(total_cr):<12}")


if __name__ == "__main__":
    main()
