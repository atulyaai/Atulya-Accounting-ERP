# Atulya ERP

> **A free, local-first business operating system for Indian enterprises and growing shops.** 📒📦

![Atulya - One-click business automation](assets/atulya-hero.png)

![Status](https://img.shields.io/badge/status-roadmap-f59e0b)
![Focus](https://img.shields.io/badge/focus-accounting%20%7C%20inventory%20%7C%20operations-14b8a6)
![Platforms](https://img.shields.io/badge/planned-desktop%20%7C%20web%20%7C%20server-2563eb)

Atulya ERP is planned as a standalone accounting and operations product: customers, vendors, items, sales, purchases, inventory, ledgers and business reports in a system the business controls.

> 🚧 This repository currently describes the architecture and delivery roadmap. It is not yet an installable ERP.

## 🎯 Modules

| Module | First useful workflows |
|---|---|
| Accounts | Chart of accounts, vouchers, ledgers, trial balance and P&L |
| Sales | Quotations, orders, tax invoices, credit notes and outstanding balances |
| Purchases | RFQ, vendor quotes, PO, GRN and bill tracking |
| Inventory | Items, batches, warehouses, movement and reorder alerts |
| Banking | Statement import, payment matching and reconciliation reports |
| Tax | GST-ready transaction records and exportable tax working data |
| Reports | Excel/PDF exports, dashboards and month-end packs |

## ⚡ Planned One-Click Setup

- Windows `.exe`, macOS `.dmg`, Linux AppImage and Docker server deployment.
- Local SQLite database for a single business; PostgreSQL option for multi-user deployment.
- Demo company and guided import from Excel on first run.
- Backup/restore wizard and exports in open formats.

## 🏗️ Architecture

```mermaid
flowchart LR
    UI["Desktop / Browser UI"] --> API["ERP API"]
    API --> DOMAIN["Accounts · Sales · Purchase · Stock"]
    DOMAIN --> LEDGER["Double-Entry Ledger Engine"]
    DOMAIN --> DB[("SQLite / PostgreSQL")]
    DOMAIN --> EXPORT["Excel · PDF · JSON Exports"]
    EXPORT --> GST["Atulya GST"]
    EXPORT --> INV["Atulya Invoice"]
```

## 🗺️ Roadmap

| Phase | Delivery |
|---|---|
| 1 | Company, parties, items, invoices and PDF/Excel outputs |
| 2 | Purchase cycle, inventory movement and payment tracking |
| 3 | Double-entry vouchers, ledgers, trial balance and reports |
| 4 | Tax working exports, reconciliation tools and import/export bridges |
| 5 | Multi-user controls, approvals, audit logs and release packaging |

## 🔐 Design Rules

- Data ownership stays with the business.
- Every financial action must be traceable and reversible through entries, never hidden edits.
- GST or external-system submission happens only through validated, authorized workflows.
- Import/export compatibility will be documented without claiming endorsement by any third-party ERP provider.

## 🔗 Independent Atulya Projects

This is a standalone product. Discover other independent Atulya repositories: [Automation Hub](https://github.com/atulyaai/Atulya-Automation-Hub) · [GST](https://github.com/atulyaai/Atulya-GST-Suite) · [SAP](https://github.com/atulyaai/Atulya-SAP-Automations) · [Office](https://github.com/atulyaai/Atulya-Office) · [HR](https://github.com/atulyaai/Atulya-HR-Suite) · [DataClean](https://github.com/atulyaai/Atulya-Data-Scruber) · [Invoice](https://github.com/atulyaai/Atulya-Invoice) · [Convert](https://github.com/atulyaai/Atulya-All-File-Converter) · [Host](https://github.com/atulyaai/Atulya-Launch)

## 📜 License

MIT planned for the open-source core.
