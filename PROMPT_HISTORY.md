# SellerPulse — AI Prompt History and Usage Disclosure

**Project:** SellerPulse
**Author:** Vijit Kumar 
**Document:** AI Prompt History, Assistance Disclosure, and Review Record
**Dataset:** Synthetic Marketplace Dataset
**Random Seed:** 4242

---

## 1. Purpose and Scope

This document records the use of AI assistance throughout the SellerPulse project, from interpreting the problem statement to preparing the final submission.

The project workflow involved understanding marketplace operations, identifying entities and relationships, designing synthetic data, documenting anomaly scenarios, reviewing data-quality results, and preparing the application and its supporting documentation.

AI assistance was used selectively for technical guidance, implementation support, troubleshooting, validation interpretation, and documentation.

**Prompt-history integrity:** Exact prompts are reproduced where their wording is available in the project conversation. Where the original wording is unavailable, entries are explicitly identified as reconstructed prompt summaries. These summaries describe the assistance requested but are not presented as verbatim historical transcripts. This document is not a complete export of every AI conversation.

## 2. Project Lifecycle and Prompt History

### 2.1 Understanding the Problem Statement

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help me understand the SellerPulse business problem, identify its core operational workflows, and translate the requirements into a practical technical implementation plan."

**Objective**

Understand how seller service levels, product listings, orders, fulfillment, customer reviews, disputes, commissions, and payouts relate to one another in a marketplace environment.

**AI assistance**

- Organizing the business requirements into technical workstreams.
- Identifying the core entities and operational relationships.
- Highlighting the importance of data integrity, lifecycle tracking, financial reconciliation, and anomaly identification.
- Structuring the implementation and documentation tasks.

**Project decisions**

The implementation was organized around a relational data model, synthetic marketplace data, application functionality, validation artifacts, and reviewer-facing documentation.

**Review responsibility**

The project author remains responsible for ensuring that the implementation reflects the supplied requirements and for identifying any incomplete or unsupported functionality.

### 2.2 Designing the Database Schema

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help design a relational database schema for a marketplace monitoring application. Identify the entities, primary keys, foreign keys, optional relationships, bridge tables, lifecycle information, and constraints needed to support the business workflows."

**Objective**

Translate the business requirements into a structured relational model.

**AI assistance**

- Exploring entity relationships and cardinality.
- Identifying the role of bridge tables in multi-seller orders.
- Considering nullable foreign keys and optional relationships.
- Documenting lifecycle history and effective-dated commission rules.
- Identifying useful integrity constraints.

**Project decisions**

The implemented schema includes 12 tables:

1. `sellers`
2. `product_listings`
3. `orders`
4. `order_sellers`
5. `order_lines`
6. `fulfillments`
7. `customer_reviews`
8. `disputes`
9. `commission_rules`
10. `payouts`
11. `payout_lines`
12. `entity_events`

The `order_sellers` table represents seller participation in orders. The `entity_events` table records lifecycle events using entity type and identifier fields.

**Review and validation**

The SQLAlchemy models and available schema audits were used as the basis for documenting the implemented tables and relationships.

**Trade-off**

A relational model provides clear integrity boundaries and queryable relationships, while the event-history table uses a polymorphic reference rather than a conventional foreign key to a single entity table.

### 2.3 Designing the Synthetic Dataset

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help design a deterministic synthetic marketplace dataset with configurable scale, stable identifiers, valid entity relationships, and a fixed random seed. Include enough records to exercise marketplace operations and financial reconciliation."

**Objective**

Create a reproducible dataset that supports realistic operational workflows and anomaly scenarios without relying on real customer or seller records.

**AI assistance**

- Planning dataset scale and table coverage.
- Considering deterministic identifiers and fixed-seed generation.
- Identifying foreign-key and arithmetic consistency checks.
- Organizing dataset provenance and export documentation.

**Project configuration**

The documented full-scale dataset uses random seed `4242` and includes the following target or recorded table counts in the source manifest:

| Table                     | Recorded rows |
| ------------------------- | ------------: |
| Sellers                   |         2,000 |
| Product listings          |        20,000 |
| Orders                    |       100,000 |
| Order lines               |       166,667 |
| Order-seller associations |       166,667 |
| Fulfillments              |       166,667 |
| Customer reviews          |        10,000 |
| Disputes                  |        10,000 |
| Commission rules          |             2 |
| Payouts                   |        16,639 |
| Payout lines              |        16,639 |
| Entity events             |       293,306 |

**Implementation reference**

The source manifest records the generation command:

`python -m backend.app.seed --scale full --seed 4242`

**Review and validation**

The project author reviewed the available table counts, source manifest, generator checksums, SQL export checksum, and exported CSV checksums.

**Trade-off**

The dataset was preserved during final documentation checks rather than regenerated destructively. Reproducibility claims must be based on verified artifacts, not on the fixed seed alone.

### 2.4 Defining Marketplace Anomaly Scenarios

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help define five synthetic marketplace anomaly scenarios involving premature payouts, duplicate commission, suspended sellers with active listings, missing dispute deductions, and payout total mismatches. Keep ground-truth labels separate from ordinary model input features."

**Objective**

Represent specific operational and financial failures in a controlled synthetic environment.

**Scenarios documented**

1. **Payout before delivery or hold release:** A payout occurs before the required delivery or hold-release condition is satisfied.
2. **Commission applied twice:** Commission is deducted more than once for the relevant transaction.
3. **Suspended seller with an active listing:** A seller's account is suspended while a listing remains active.
4. **Dispute not deducted:** An eligible dispute amount is missing from the relevant payout calculation.
5. **Payout total mismatch:** The payout header does not reconcile with its associated payout-line amounts.

**AI assistance**

- Describing the anomaly conditions.
- Identifying relevant relationships and financial fields.
- Suggesting ways to document the expected conditions and validation evidence.

**Project decision**

Anomaly labels are maintained separately in `data/ground_truth.json`, rather than being embedded in ordinary model input features.

**Review responsibility**

The author must verify that each scenario is represented by the intended record and distinguish intentionally injected anomalies from unintended data-quality errors.

### 2.5 Developing Validation and Data-Quality Checks

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help define a data-quality checklist for primary keys, foreign-key integrity, duplicate business identifiers, lifecycle timestamps, order totals, fulfillment relationships, and payout arithmetic."

**Objective**

Assess whether the generated dataset satisfies structural and business-level expectations.

**AI assistance**

- Organizing integrity checks.
- Interpreting audit results.
- Distinguishing database-enforced constraints from application-level validation rules.
- Identifying inconsistencies that require investigation.

**Validation areas**

- Primary-key coverage and uniqueness.
- Foreign-key references and orphan records.
- Duplicate or missing business identifiers.
- Valid statuses and field values.
- Order-line and order-total reconciliation.
- Fulfillment dates and order-line ownership.
- Seller status and listing consistency.
- Commission calculation and duplicate deductions.
- Dispute deductions and payout eligibility.
- Payout header and payout-line reconciliation.

**Recorded evidence**

The supplied data dictionary audit reported `PASS`, with 12 tables and 73 documented fields. The supplied data-quality audit reported zero errors and zero orphan references for the relationships it checked. The validation summary contained an empty `validation_errors` list.

These results establish the outcome of the checks represented in the supplied artifacts; they do not prove that every possible business rule has been tested.

### 2.6 Building and Reviewing the Application

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help review the implementation of the SellerPulse application, identify issues affecting its operation, and provide practical debugging guidance without unnecessarily resetting the existing project or dataset."

**Objective**

Support application implementation and troubleshooting while preserving the working project state.

**AI assistance**

- Explaining technical errors and implementation concerns.
- Suggesting targeted troubleshooting commands.
- Reviewing how backend, frontend, and database components fit together.
- Helping prepare practical setup and execution instructions.

**Project technology references**

The project includes a FastAPI backend, a React and TypeScript frontend using Vite, and a SQLite database.

**Implementation decision**

During final documentation and provenance checks, the existing dataset was preserved. Destructive reseeding and unnecessary test reruns were avoided in accordance with the project author's instructions.

**Review responsibility**

The author must verify the final application behavior and distinguish previously observed successful execution from checks that have not been performed again.

### 2.7 Improving the Data Dictionary

**Actual prompt available in the project conversation**

"10 entities ke fields aur validation rules — `data/exports/data_dictionary.json` — existing file ko use/update karo."

**Objective**

Improve the existing machine-readable field reference while retaining its connection to the implemented schema.

**AI assistance**

- Adding explicit field-level validation guidance.
- Adding table-level validation notes.
- Explaining required fields, keys, uniqueness, allowed values, units, and business rules.

**Implementation decision**

The existing `data/exports/data_dictionary.json` was updated rather than replaced with an unrelated field inventory.

**Verification evidence**

A local check reported:

- 73 field records.
- 12 distinct tables.
- Zero records missing `validation_rules`.

**Trade-off**

A documented rule expresses an expected validation condition. It does not necessarily mean the database enforces that condition through a SQL constraint.

### 2.8 Documenting Primary Keys, Foreign Keys, and Relationships

**Actual prompt available in the project conversation**

"Primary keys, foreign keys aur relationships — `docs/SCHEMA.md`."

**Objective**

Create a readable technical schema reference for reviewers.

**AI assistance**

- Organizing the primary-key and foreign-key inventory.
- Explaining relationship cardinality.
- Documenting optional relationships and the bridge table.
- Distinguishing declared foreign keys from polymorphic event references.

**Implementation decision**

`docs/SCHEMA.md` was created to document the implemented tables, relationships, declared constraints, and additional business-level validation expectations.

**Verification evidence**

The author checked that the document listed the 12 tables and reviewed its initial content in the local PowerShell terminal.

**Review responsibility**

The final document should continue to match `backend/app/models.py`. Any relationship or constraint not declared in the implementation must be described as a business rule or recommendation, not as an enforced database constraint.

### 2.9 Verifying Dataset Provenance and the Source Manifest

**Actual prompt available in the project conversation**

"Dataset source, seed, counts aur checksums — `data/source_manifest.json`."

**Objective**

Check the dataset's provenance metadata and the integrity of the referenced artifacts.

**AI assistance**

- Providing a local checksum-verification procedure.
- Comparing manifest table counts with the validation summary.
- Interpreting mismatches and identifying a safe documentation update.

**Verification evidence**

The local verification reported:

- Seed: `4242`.
- Scale: `full`.
- Generator checksums: both matched.
- SQL export checksum: matched.
- CSV checksums: all 12 matched.
- Initial count discrepancies: `entity_events`, `payouts`, and `payout_lines`.

The manifest counts were subsequently aligned with `data/exports/validation_summary.json`, and a backup of the original manifest was created.

**Trade-off and limitation**

Aligning counts makes the two documents consistent, but it does not independently prove that the manifest, SQL export, and validation summary were generated from the same database snapshot. The original SQL and generator checksums were verified before the count update; they should not be interpreted as proof of a common snapshot.

### 2.10 Preparing the README and Supporting Documentation

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Prepare professional project documentation explaining SellerPulse, its architecture, setup instructions, dataset artifacts, validation evidence, limitations, screenshots, and AI-use disclosure."

**Objective**

Make the project understandable and reproducible for a reviewer who has not seen the development process.

**AI assistance**

- Structuring the README.
- Improving the clarity of technical explanations.
- Linking supporting documentation.
- Documenting setup, environment requirements, and limitations.

**Project decision**

Supporting documentation is separated by purpose: the README introduces the project, the schema explains relationships, the data dictionary documents fields, the manifest records provenance, and the validation artifacts summarize recorded checks.

**Review responsibility**

All commands, paths, screenshots, and claims must be confirmed against the actual repository before publication.

### 2.11 Preparing the AI Disclosure and Prompt History

**Actual prompt available in the project conversation**

"English me sb aur professional ay me yaad rakhna."

**Context**

The author requested professional English documentation and a complete prompt-history record covering the project from understanding the problem statement through final submission preparation.

**AI assistance**

- Organizing prompt records chronologically.
- Distinguishing actual prompts from reconstructed summaries.
- Documenting the purpose of AI assistance, implementation decisions, review evidence, and limitations.

**Project decision**

This document explicitly identifies reconstructed summaries rather than presenting them as verbatim historical prompts.

**Review responsibility**

The author should add any further original prompts that can be recovered and ensure that the disclosure reflects the AI tools actually used.

### 2.12 Preparing for Secure GitHub Publication

**Prompt record:** Reconstructed prompt summary.

**Prompt summary:**

"Help prepare a safe Git staging workflow for SellerPulse that includes the required source code and documentation while excluding credentials, local databases, large SQL dumps, virtual environments, and unnecessary backups."

**Objective**

Prepare the repository for public review without exposing local or sensitive artifacts.

**AI assistance**

- Suggesting explicit staging paths.
- Identifying files and directories that should be excluded.
- Recommending review of staged files before committing.

**Security items identified**

- `.env` files and credentials.
- Local database files.
- The approximately 268 MB SQL export.
- Virtual environments, caches, and generated build directories.
- Unnecessary backup files.

**Current limitation**

A proposed staging workflow is not evidence that a commit or push has succeeded. The staged files must be inspected, and publication must be confirmed separately.

---

## 3. Summary of AI Assistance

AI assistance was used in selected parts of the project to support:

- Problem decomposition and technical planning.
- Relational schema design discussions.
- Synthetic data and anomaly-scenario planning.
- Validation checklist development and audit interpretation.
- Application troubleshooting.
- Data dictionary and schema documentation.
- Dataset provenance and checksum verification.
- README preparation and GitHub publication planning.

AI output was treated as assistance requiring review, not as automatic proof of correctness. The project author remains responsible for the submitted implementation and its claims.

## 4. Author Review and Engineering Decisions

The following decisions are documented from the available project workflow:

1. The existing data dictionary was updated instead of replaced.
2. Schema documentation was prepared for all 12 implemented tables.
3. Anomaly labels were kept in a separate ground-truth artifact.
4. The existing dataset was preserved during final documentation checks.
5. Generator and export checksums were verified against the source manifest.
6. Discrepancies between manifest and validation-summary counts were identified and documented before aligning the counts.
7. Count alignment was not treated as independent proof of common data provenance.
8. Explicit Git staging was preferred over indiscriminately adding all project files.
9. Historical prompt wording was not invented where it was unavailable.
10. Validation claims were limited to the evidence provided by the available audit outputs.

These records reflect the workflow evidenced in the available conversation. The author should personally confirm the final source code, repository contents, and any additional checks performed outside that record.

## 5. Trade-offs and Limitations

### Documentation versus enforcement

A validation rule in the data dictionary does not necessarily correspond to a database constraint. Database-enforced checks and application-level business checks must be distinguished.

### Reproducibility versus data preservation

The existing dataset was retained during final verification to avoid destructive changes. Reproducibility should be established using consistent generation procedures and verified artifacts.

### Consistency versus provenance certainty

Matching table counts is useful, but it does not prove that all files originated from one database snapshot.

### Prompt completeness

This document contains available prompt wording and clearly labelled reconstructed summaries. It should not be represented as a complete verbatim export of every historical AI interaction.

### Validation scope

A passing audit only demonstrates the checks actually represented by that audit. It is not a universal guarantee of correctness.

### Publication status

Preparing a Git staging plan does not mean the project has been committed to or pushed to GitHub. Those steps require separate confirmation.

## 6. Security and Publication Checklist

Before making the repository public:

- [✅] Inspect the staged files for credentials, tokens, passwords, and sensitive data.
- [✅] Exclude `.env` files and local database files.
- [✅] Exclude the large SQL dump unless publication is explicitly required and approved.
- [✅] Exclude unnecessary backups, caches, and virtual environments.
- [✅] Confirm that `.gitignore` covers local and generated artifacts.
- [✅] Review the final staged diff before committing.
- [✅] Confirm that setup instructions and documentation links match the repository.
- [✅] Keep anomaly ground-truth labels separate from ordinary model input features.
- [✅] Confirm the final commit and remote push separately.

## 7. Final Disclosure

SellerPulse was developed with AI assistance for selected planning, technical-support, validation-interpretation, and documentation tasks. The project author remains responsible for reviewing the implementation, assessing the accuracy of the documentation, validating the submitted artifacts, and making the final engineering and publication decisions.

**Author:** Vijit Kumar
**Project:** SellerPulse
