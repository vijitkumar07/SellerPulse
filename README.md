# SellerPulse — Seller Operations & Payout Intelligence

SellerPulse is a full-stack marketplace operations solution built to monitor seller performance, order fulfillment, disputes, commissions, and payout eligibility. It uses synthetic marketplace data to demonstrate business-rule validation, payout reconciliation, anomaly detection, and data-quality auditing.

## Problem Statement

Online marketplaces coordinate thousands of sellers, product listings, orders, shipments, disputes, commissions, and payouts. As transaction volumes increase, maintaining data consistency and enforcing business rules becomes increasingly complex.

Premature payouts, duplicate commission deductions, missing dispute deductions, suspended sellers with active listings, and incorrect payout totals can create financial discrepancies and operational risks.

**SellerPulse addresses these challenges through relational data modelling, conditional business rules, payout reconciliation, anomaly detection, and validation reports.** It provides a structured way to identify operational exceptions and records that may require further investigation.

## Solution and Requirement Coverage

| Business requirement | SellerPulse implementation |
|---|---|
| Monitor seller operations | Seller, listing, order, fulfillment, and review records |
| Manage marketplace orders | Orders, order lines, and seller-order relationships |
| Support multi-seller orders | `order_sellers` bridge table |
| Track order fulfillment | Fulfillment records linked to order-line data |
| Manage disputes and chargebacks | Dispute records and payout deduction fields |
| Apply commission rules | Commission rules and commission calculations |
| Validate payout eligibility | Delivery and hold-window checks |
| Detect operational exceptions | Five targeted anomaly scenarios |
| Preserve event traceability | `entity_events` lifecycle-history table |
| Document data fields and relationships | Data dictionary and schema documentation |
| Validate data quality | Data-quality and export-validation reports |
| Separate known anomaly labels | Dedicated `data/ground_truth.json` |
| Support repeatable data generation | Fixed seed and source manifest |
| Test core business logic | Automated Pytest suite |

The solution is designed around the supplied marketplace workflow. Validation claims are limited to the checks and evidence documented in the repository.

## Key Features

- Seller operations and marketplace dashboard
- Payout and commission reconciliation
- Detection of financial and operational anomalies
- FastAPI endpoints for dashboard metrics and anomaly records
- SQLite relational database using SQLAlchemy
- Synthetic marketplace data for reproducible testing
- Data dictionary, schema documentation, and validation reports
- Automated tests for business rules and anomaly detection

## Technology Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI, Uvicorn
- **Database:** SQLite, SQLAlchemy
- **Testing:** Pytest
- **Version Control:** Git and GitHub

## Anomaly Detection

SellerPulse covers five required negative scenarios:

1. **Premature payout:** Payout occurs before delivery or the required hold-release condition.
2. **Duplicate commission:** Commission is deducted more than once.
3. **Suspended seller with an active listing:** Seller status conflicts with listing activity.
4. **Missing dispute deduction:** A required dispute amount is not deducted from the payout.
5. **Payout total mismatch:** The recorded payout differs from its expected line-level calculation.

These scenarios represent deliberate exceptions in the synthetic dataset. Anomaly findings identify potential issues for review; they do not independently establish fraud.

## Project Structure

```text
SellerPulse/
├── backend/
├── frontend/
├── data/
├── docs/
├── scripts/
├── tests/
├── README.md
├── PROMPT_HISTORY.md
└── .gitignore
```

## Setup and Installation

The following instructions are intended for Windows using PowerShell.

### 1. Install prerequisites

Install the following software:

- **Python 3.12.x:** [Download Python](https://www.python.org/downloads/)
- **Node.js 20.x:** [Download Node.js](https://nodejs.org/)
- **Git:** [Download Git](https://git-scm.com/)

During Python installation, enable **Add Python to PATH**.

Verify the installations:

```powershell
python --version
python -m pip --version
node --version
npm --version
git --version
```

The development environment used Python 3.12.0, Node.js 20.18.3, and npm 10.8.2. Reopen the terminal if a newly installed command is not recognized.

### 2. Clone the repository

Open PowerShell or the VS Code terminal:

```powershell
git clone https://github.com/vijitkumar07/SellerPulse.git
cd SellerPulse
```

Optionally, open the project in VS Code:

```powershell
code .
```

Run backend commands from the repository root unless otherwise specified.

### 3. Create and activate the Python environment

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the following in the same terminal and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install backend dependencies

Upgrade pip and install the dependencies declared by the project:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip check
```

The backend dependency set includes FastAPI, Uvicorn, Pytest, HTTPX, and SQLAlchemy. Package versions are specified in the project's dependency files.

### 5. Initialize the database

From the repository root, run:

```powershell
python -m backend.app.init_db
```

This initializes the SQLite database and creates the application's database tables.

### 6. Generate synthetic marketplace data

Run:

```powershell
python -m backend.app.seed --scale full --seed 4242
```

Wait for data generation to finish before starting the backend.

The fixed seed supports reproducible data generation using the configured generator.

### 7. Start the backend

From the repository root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

Keep this terminal running.

- **Backend:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 8. Install frontend dependencies

Open a second terminal in VS Code. Keep the backend terminal running.

Navigate to the frontend directory:

```powershell
cd frontend
```

Install the frontend dependencies:

```powershell
npm install
```

Wait for installation to complete.

### 9. Start the frontend

In the same frontend terminal, run:

```powershell
npm run dev
```

Open the local URL displayed by Vite, normally [http://localhost:5173](http://localhost:5173).

Keep both terminals running while using the application:

- Terminal 1: FastAPI backend
- Terminal 2: React frontend

## Database Schema

SellerPulse uses 12 relational tables:

`sellers`, `product_listings`, `orders`, `order_sellers`, `order_lines`, `fulfillments`, `customer_reviews`, `disputes`, `commission_rules`, `payouts`, `payout_lines`, and `entity_events`.

The schema documentation describes table definitions, keys, relationships, and cardinality. The data dictionary provides field-level information and validation guidance.

See [docs/SCHEMA.md](docs/SCHEMA.md) for the complete schema.

## Synthetic Data and Dataset Coverage

The recorded full dataset contains the following entity counts:

| Entity | Records |
|---|---:|
| Sellers | 2,000 |
| Product listings | 20,000 |
| Orders | 100,000 |
| Order lines | 166,667 |
| Seller-level orders | 166,667 |
| Fulfillments | 166,667 |
| Customer reviews | 10,000 |
| Disputes | 10,000 |
| Commission rules | 2 |
| Payouts | 18,129 |
| Payout lines | 18,129 |
| Entity events | 524,650 |

These figures are the counts recorded in the source manifest. The dataset is synthetic and is intended for development, testing, and demonstration rather than representing real marketplace transactions.

The generation workflow is designed to support interconnected marketplace records, split orders, fulfillment, reviews, disputes, commission rules, reserve holds, seller suspension, and payout eligibility.

## Validation and Testing

The repository includes validation artifacts, data exports, a source manifest, separate ground-truth labels, and automated tests.

The documented validation work covers:

- Primary-key presence and uniqueness checks
- Foreign-key integrity for audited relationships
- Data dictionary consistency
- Payout arithmetic and reconciliation checks
- Detection of the five seeded anomaly scenarios
- Dataset counts and SHA-256 checksums

The recorded data dictionary audit reports 12 tables and 73 fields with a passing result. The data-quality audit reports no errors and no orphan references among the relationships it checked.

The documented test run passed all eight tests, covering the five anomaly scenarios, finding structure, duplicate findings, hold-window logic, commission calculation, net payout calculation, and invalid deductions.

Run the tests from the repository root with the Python virtual environment activated:

```powershell
python -m pytest -v
```

Supporting reports are available in `data/exports/`, with dataset metadata in `data/source_manifest.json`.

**Reproducibility note:** A fixed seed and recorded checksums support repeatability, but matching row counts alone do not prove that every artifact came from the same database snapshot. A clean regeneration and checksum comparison are needed to independently establish end-to-end reproducibility.

## Ground Truth and Evaluation

Known anomaly labels are maintained separately in `data/ground_truth.json`. This separation is intended to support evaluation without directly supplying ground-truth labels as ordinary detector input features.

The validation reports and automated tests provide evidence for the checks performed. Their scope should not be interpreted as proof that every possible business rule or real-world exception is covered.

## Screenshots

![SellerPulse Screenshot 1](docs/image1.png)

![SellerPulse Screenshot 2](docs/image2.png)

![SellerPulse Screenshot 3](docs/image3.png)

![SellerPulse Screenshot 4](docs/image4.png)

![SellerPulse Screenshot 5](docs/image5.png)

![SellerPulse Screenshot 6](docs/image6.png)

![SellerPulse Screenshot 7](docs/image7.png)

![SellerPulse Screenshot 8](docs/image8.png)

## AI Assistance

AI tools were used during development to help with problem-solving, debugging, and documentation. The prompts and relevant development notes are available in [PROMPT_HISTORY.md](PROMPT_HISTORY.md).

I reviewed the suggested changes and worked on validating the project through its code, data checks, and tests. I am responsible for the final implementation and for explaining the decisions made during development.

## Limitations and Security

SellerPulse uses synthetic marketplace data, so no real seller or customer information is involved. The anomaly checks are designed to flag suspicious records for further review, not to automatically determine fraud.

The project is built as a demonstration of marketplace operations and payout validation. Before using it in a real production environment, additional testing, security controls, and operational safeguards would be needed.

Credentials, API keys, environment files, local databases, and unnecessary backup files should not be committed to the public repository.

## Author

**Vijit Kumar**

[GitHub Repository](https://github.com/vijitkumar07/SellerPulse)