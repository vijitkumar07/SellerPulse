import json
from pathlib import Path
from backend.app.models import Base
from backend.app.data_dictionary import FIELD_RULES
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "exports"
DICT_JSON = OUT / "data_dictionary.json"
REPORT = OUT / "data_dictionary_audit.json"
model_fields = {
    table_name: set(table.columns.keys())
    for table_name, table in Base.metadata.tables.items()
}
errors = []
report = {
    "model_table_count": len(model_fields),
    "model_field_count": sum(len(v) for v in model_fields.values()),
    "tables": {},
    "field_rules_checked": len(FIELD_RULES),
    "invalid_field_rules": [],
}
# Compare the exported dictionary with the SQLAlchemy models.
if not DICT_JSON.exists():
    errors.append("Exported data_dictionary.json is missing. Run the dictionary exporter first.")
else:
    dictionary = json.loads(DICT_JSON.read_text(encoding="utf-8"))
    dictionary_fields = {}
    for item in dictionary:
        table = item.get("table")
        field = item.get("field")
        if table and field:
            dictionary_fields.setdefault(table, set()).add(field)
    for table, actual_fields in model_fields.items():
        documented_fields = dictionary_fields.get(table, set())
        missing = sorted(actual_fields - documented_fields)
        extra = sorted(documented_fields - actual_fields)
        report["tables"][table] = {
            "model_fields": len(actual_fields),
            "documented_fields": len(documented_fields),
            "missing_fields": missing,
            "unknown_fields": extra,
        }
        if missing:
            errors.append(f"{table}: fields missing from dictionary: {missing}")
        if extra:
            errors.append(f"{table}: unknown dictionary fields: {extra}")
    extra_tables = sorted(set(dictionary_fields) - set(model_fields))
    report["unknown_dictionary_tables"] = extra_tables
    if extra_tables:
        errors.append(f"Unknown dictionary tables: {extra_tables}")
# FIELD_RULES is keyed by (table_name, field_name).
for key in FIELD_RULES:
    if not isinstance(key, tuple) or len(key) != 2:
        report["invalid_field_rules"].append(str(key))
        continue
    table, field = key
    if table not in model_fields or field not in model_fields.get(table, set()):
        report["invalid_field_rules"].append(str(key))
if report["invalid_field_rules"]:
    errors.append(
        "FIELD_RULES contains invalid table/field keys: "
        + str(report["invalid_field_rules"])
    )
report["error_count"] = len(errors)
report["errors"] = errors
report["status"] = "PASS" if not errors else "FAIL"
OUT.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SELLERPULSE DATA DICTIONARY AUDIT")
print("=" * 42)
print(f"Model tables: {report['model_table_count']}")
print(f"Model fields: {report['model_field_count']}")
print(f"Business field rules checked: {report['field_rules_checked']}")
print(f"Tables compared: {len(report['tables'])}")
print(f"Errors: {report['error_count']}")
for error in errors:
    print("ERROR:", error)
print(f"Report: {REPORT}")
print("RESULT:", report["status"])
