#!/usr/bin/env python3
"""Offline, allowlisted export of Agora's published catalogue projections (stdlib only)."""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-10-07"
INPUTS = {
    "catalogue-public.json": (361, 59),
    "catalogue-expanded-public.json": (760, 19),
    "catalogue-ustc-nanjing-public.json": (233, 10),
    "catalogue-xjtu-hit-public.json": (306, 12),
}
DOMAINS = {
    "admission.pku.edu.cn", "hwxy.nju.edu.cn", "ic.ustc.edu.cn", "iczu.zju.edu.cn",
    "international.join-tsinghua.edu.cn", "isc.sjtu.edu.cn", "iso.fudan.edu.cn",
    "sie.xjtu.edu.cn", "studyathit.hit.edu.cn", "www.fdsm.fudan.edu.cn",
    "www.isd.pku.edu.cn", "yzbm.tsinghua.edu.cn",
}
EXPECTED_UNIVERSITIES = {
    "Tsinghua University": (24, 94), "Peking University": (23, 220),
    "Shanghai Jiao Tong University": (43, 111), "Zhejiang University": (92, 284),
    "Fudan University": (67, 163), "University of Science and Technology of China": (18, 36),
    "Nanjing University": (52, 127), "Xi’an Jiaotong University": (50, 107),
    "Harbin Institute of Technology": (97, 52),
}
RECORD_TYPES = {
    "department_degree", "department_degree_language", "admission_division",
    "admission_college", "admission_programme", "admission_department",
    "admission_group", "admission_route",
}
CYCLES = {
    "prior_cycle_catalogue", "historical_2026", "latest_catalogue_cycle_unstated",
    "academic_year_2026_2027_guide_intake_2026", "current_catalogue", "verified_2027",
    "undated_live_catalogue", "selected_current_route", "current_notice_and_live_catalogue",
}
RECORD_REQUIRED = set("id university level recordType degreeType intake cycleStatus department nameOriginal nameEnglish language sourceIds sourceUrl".split())
RECORD_OPTIONAL = set("departmentCode departmentEnglish facultyGroup programmeCode studyModes languageEvidence duration notes groupKey groupTitle researchFieldsLabel researchFields listedMajors admissionGroups openChoiceStatements".split())
SOURCE_FIELDS = set("id title url intake checkedAt status".split())
FIELD_FIELDS = set("code nameOriginal nameEnglish nameSource language studyMode duration notes".split())
MAJOR_FIELDS = set("nameOriginal nameEnglish department duration".split())
GROUP_FIELDS = set("nameOriginal specializationOptionsOriginal openChoiceStatementsOriginal".split())
COVERAGE_FIELDS = set("slug university level cycle unit limits sourceIds recordCount url".split())
OWNER = "Agora Scholars"
INDEPENDENCE = "An independently curated directory by Agora Scholars; not a university publication, partnership or endorsement."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def keys(obj, allowed, required=()):
    require(isinstance(obj, dict), "Expected object")
    require(not (set(obj) - set(allowed)), "Unapproved fields: " + ", ".join(sorted(set(obj) - set(allowed))))
    require(set(required) <= set(obj), "Missing required fields: " + ", ".join(sorted(set(required) - set(obj))))


def string(value, nullable=False):
    require(isinstance(value, str) or (nullable and value is None), "Expected string" + (" or null" if nullable else ""))
    if isinstance(value, str):
        require(not any(ord(c) < 32 and c not in "\n\r\t" for c in value), "Control character")
        require(len(value) < 12000, "Unbounded text")
        require(not re.search(r"(?:/Users/|/private/|file://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", value), "Private path or email in public data")


def strings(value, nonempty=False):
    require(isinstance(value, list), "Expected string array")
    require(not nonempty or bool(value), "Empty required array")
    for item in value:
        string(item)


def official_url(value):
    string(value)
    parts = urlsplit(value)
    require(parts.scheme == "https" and parts.hostname in DOMAINS, "Non-allowlisted official URL: " + value)
    require(not parts.username and not parts.password and parts.port in (None, 443), "URL credentials or unexpected port")


def source_shape(source, projected=False):
    allowed = SOURCE_FIELDS | ({"projectionFile"} if projected else set())
    keys(source, allowed, allowed)
    for key, value in source.items():
        string(value, key == "intake")
    official_url(source["url"])
    require(source["checkedAt"] == SNAPSHOT, "Unexpected source check date")
    if projected:
        require(source["projectionFile"] in INPUTS, "Unknown source projection")


def record_shape(record, projected=False):
    allowed = RECORD_REQUIRED | RECORD_OPTIONAL | ({"projectionFile"} if projected else set())
    keys(record, allowed, RECORD_REQUIRED | ({"projectionFile"} if projected else set()))
    arrays = {"studyModes", "sourceIds", "notes", "openChoiceStatements"}
    nested = {"researchFields": FIELD_FIELDS, "listedMajors": MAJOR_FIELDS, "admissionGroups": GROUP_FIELDS}
    for key, value in record.items():
        if key in arrays:
            strings(value, key == "sourceIds")
        elif key in nested:
            require(isinstance(value, list), "Expected nested list")
            for item in value:
                keys(item, nested[key])
                for field, text in item.items():
                    if field in {"notes", "specializationOptionsOriginal", "openChoiceStatementsOriginal"}:
                        strings(text)
                    else:
                        string(text, field in {"language", "duration", "department"})
                if key == "researchFields":
                    require("code" in item and "language" in item and "studyMode" in item, "Missing field identity/language/study mode")
                    require(any(item.get(k) for k in ("nameEnglish", "nameOriginal", "nameSource", "duration")), "Empty research-field/qualifier row")
                elif key == "admissionGroups":
                    keys(item, GROUP_FIELDS, GROUP_FIELDS)
                else:
                    require(item.get("nameOriginal") or item.get("nameEnglish"), "Missing major name")
        else:
            string(value, key in {"degreeType", "intake", "nameOriginal", "nameEnglish", "language", "duration"})
    require(record["nameOriginal"] or record["nameEnglish"], "Missing record name")
    require(record["university"] in EXPECTED_UNIVERSITIES, "Unknown university")
    require(record["level"] in {"master", "undergraduate"}, "Unknown level")
    require(record["recordType"] in RECORD_TYPES, "Unknown counting unit")
    require(record["cycleStatus"] in CYCLES, "Unknown cycle status")
    require(record["intake"] in {None, "2026", "2027", "2026/2027 academic year"}, "Unexpected intake")
    require(len(set(record["sourceIds"])) == len(record["sourceIds"]), "Repeated source reference")
    official_url(record["sourceUrl"])
    if projected:
        require(record["projectionFile"] in INPUTS, "Unknown record projection")
        if record["projectionFile"] != "catalogue-public.json":
            require(bool(record.get("languageEvidence")), "Language qualifier lost")


def import_projections(directory):
    data = {"schemaVersion": 1, "snapshotDate": SNAPSHOT, "owner": OWNER, "independence": INDEPENDENCE,
            "provenance": [], "sources": [], "records": [], "coverage": []}
    for filename, (records_count, sources_count) in INPUTS.items():
        raw = (directory / filename).read_bytes()
        source = json.loads(raw)
        keys(source, {"updatedAt", "sources", "records"}, {"updatedAt", "sources", "records"})
        require(source["updatedAt"] == SNAPSHOT, "Snapshot date mismatch")
        require((len(source["records"]), len(source["sources"])) == (records_count, sources_count), "Input counts mismatch")
        for row in source["sources"]:
            source_shape(row)
            data["sources"].append({**row, "projectionFile": filename})
        for row in source["records"]:
            record_shape(row)
            data["records"].append({**row, "projectionFile": filename})
        data["provenance"].append({"filename": filename, "sha256": sha(raw), "records": records_count, "sources": sources_count})
    coverage = json.loads((ROOT / "data/coverage-notes.json").read_text(encoding="utf-8"))
    keys(coverage, {"coverageProvenance", "coverage"}, {"coverageProvenance", "coverage"})
    data.update(coverage)
    validate(data)
    return data


def validate(data):
    top = {"schemaVersion", "snapshotDate", "owner", "independence", "provenance", "coverageProvenance", "sources", "records", "coverage"}
    keys(data, top, top)
    require(data["schemaVersion"] == 1 and data["snapshotDate"] == SNAPSHOT, "Unsupported version/date")
    require(data["owner"] == OWNER and data["independence"] == INDEPENDENCE, "Ownership disclosure missing")
    require(len(data["records"]) == 1660 and len(data["sources"]) == 100 and len(data["coverage"]) == 18, "Snapshot counts mismatch")
    sources = {}
    for source in data["sources"]:
        source_shape(source, True)
        require(source["id"] not in sources, "Duplicate source ID")
        sources[source["id"]] = source
    ids = set()
    for record in data["records"]:
        record_shape(record, True)
        require(record["id"] not in ids, "Duplicate record ID")
        ids.add(record["id"])
        require(set(record["sourceIds"]) <= sources.keys(), "Unresolved source ID")
        require(record["sourceUrl"] in {sources[s]["url"] for s in record["sourceIds"]}, "Primary URL not among referenced sources")
    for university, expected in EXPECTED_UNIVERSITIES.items():
        actual = tuple(sum(r["university"] == university and r["level"] == level for r in data["records"]) for level in ("undergraduate", "master"))
        require(actual == expected, "University/level counts mismatch: " + university)
    require(len(data["provenance"]) == 4, "Missing input provenance")
    require({p.get("filename") for p in data["provenance"]} == set(INPUTS), "Unexpected projection provenance")
    for p in data["provenance"]:
        keys(p, {"filename", "sha256", "records", "sources"}, {"filename", "sha256", "records", "sources"})
        require(bool(re.fullmatch(r"[0-9a-f]{64}", p["sha256"])), "Invalid source hash")
        require((p["records"], p["sources"]) == INPUTS[p["filename"]], "Provenance counts mismatch")
        require(sum(r["projectionFile"] == p["filename"] for r in data["records"]) == p["records"], "Projection record count mismatch")
        require(sum(s["projectionFile"] == p["filename"] for s in data["sources"]) == p["sources"], "Projection source count mismatch")
    cp = data["coverageProvenance"]
    keys(cp, {"filename", "sha256", "fields"}, {"filename", "sha256", "fields"})
    require(cp["filename"] == "catalogue.ts" and bool(re.fullmatch(r"[0-9a-f]{64}", cp["sha256"])), "Invalid coverage provenance")
    require(cp["fields"] == sorted(COVERAGE_FIELDS - {"recordCount", "url"}), "Coverage allowlist mismatch")
    pairs, slugs = set(), set()
    for coverage in data["coverage"]:
        keys(coverage, COVERAGE_FIELDS, COVERAGE_FIELDS)
        for k, v in coverage.items():
            if k in {"limits", "sourceIds"}:
                strings(v, True)
            elif k != "recordCount":
                string(v)
        pair = (coverage["university"], coverage["level"])
        require(pair not in pairs and coverage["slug"] not in slugs, "Duplicate coverage")
        pairs.add(pair); slugs.add(coverage["slug"])
        require(re.fullmatch(r"[a-z0-9-]+", coverage["slug"]) is not None, "Invalid slug")
        require(coverage["url"] == "https://www.agorascholars.com/admissions/programmes/" + coverage["slug"], "Invalid live URL")
        require(coverage["recordCount"] == sum((r["university"], r["level"]) == pair for r in data["records"]) > 0, "Coverage count mismatch")
        require(set(coverage["sourceIds"]) <= sources.keys(), "Unresolved coverage source")
    for field, expected in (("researchFields", 1938), ("listedMajors", 154), ("admissionGroups", 27)):
        require(sum(len(r.get(field, [])) for r in data["records"]) == expected, "Nested count mismatch: " + field)
    require(sum(len(g["specializationOptionsOriginal"]) for r in data["records"] for g in r.get("admissionGroups", [])) == 104, "Specialization count mismatch")


def cell(value):
    # Null is explicit; an omitted optional field is an empty CSV cell.
    if value is None:
        return "null"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = str(value)
    # The JSON is lossless; protect spreadsheet users without executing formulas.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def csv_bytes(rows, fields):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(fields)
    for row in rows:
        writer.writerow([cell(row[k]) if k in row else "" for k in fields])
    return buffer.getvalue().encode("utf-8")


def counts(data):
    records = data["records"]
    return {
        "catalogueUnits": len(records), "universities": len(EXPECTED_UNIVERSITIES), "coveragePages": len(data["coverage"]), "sourceRecords": len(data["sources"]),
        "byLevel": dict(sorted(collections.Counter(r["level"] for r in records).items())),
        "byUniversity": dict(sorted(collections.Counter(r["university"] for r in records).items())),
        "byRecordType": dict(sorted(collections.Counter(r["recordType"] for r in records).items())),
        "byCycleStatus": dict(sorted(collections.Counter(r["cycleStatus"] for r in records).items())),
        "byIntake": dict(sorted(collections.Counter(r["intake"] or "unknown" for r in records).items())),
        "unknownTeachingLanguage": sum(r["language"] is None for r in records),
        "recordsWithLanguageEvidence": sum("languageEvidence" in r for r in records),
        "nestedResearchFieldRows": sum(len(r.get("researchFields", [])) for r in records),
        "nestedQualifierOnlyRows": sum(not any(f.get(k) for k in ("nameEnglish", "nameOriginal", "nameSource")) for r in records for f in r.get("researchFields", [])),
        "nestedMajorOptionCells": sum(len(r.get("listedMajors", [])) for r in records),
        "nestedAdmissionGroups": sum(len(r.get("admissionGroups", [])) for r in records),
        "nestedSpecializationOptions": sum(len(g["specializationOptionsOriginal"]) for r in records for g in r.get("admissionGroups", [])),
    }


def render(data):
    validate(data)
    sources = {s["id"]: s for s in data["sources"]}
    parent_rows, field_rows, major_rows, group_rows = [], [], [], []
    for record in data["records"]:
        context = {"parentRecordId": record["id"], "university": record["university"], "level": record["level"], "intake": record["intake"], "cycleStatus": record["cycleStatus"], "sourceIds": record["sourceIds"], "officialSourceUrls": [sources[s]["url"] for s in record["sourceIds"]], "sourceCheckedDates": [sources[s]["checkedAt"] for s in record["sourceIds"]]}
        parent_rows.append({**record, "officialSourceUrls": context["officialSourceUrls"], "sourceCheckedDates": context["sourceCheckedDates"]})
        for name, target in (("researchFields", field_rows), ("listedMajors", major_rows), ("admissionGroups", group_rows)):
            for index, item in enumerate(record.get(name, []), 1):
                row = {**context, "ordinal": index, **item}
                if name == "researchFields":
                    row["rowKind"] = "named_field" if any(item.get(k) for k in ("nameEnglish", "nameOriginal", "nameSource")) else "qualifier_only"
                target.append(row)
    context_fields = ["parentRecordId", "ordinal", "university", "level", "intake", "cycleStatus", "sourceIds", "officialSourceUrls", "sourceCheckedDates"]
    main_fields = ["id", "university", "level", "recordType", "nameOriginal", "nameEnglish", "programmeCode", "department", "departmentEnglish", "departmentCode", "degreeType", "intake", "cycleStatus", "language", "languageEvidence"]
    main_fields += sorted((RECORD_REQUIRED | RECORD_OPTIONAL) - set(main_fields)) + ["projectionFile", "officialSourceUrls", "sourceCheckedDates"]
    files = {
        "data/coverage-notes.json": json_bytes({"coverageProvenance": data["coverageProvenance"], "coverage": data["coverage"]}),
        "data/catalogue.json": (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
        "data/catalogue.csv": csv_bytes(parent_rows, main_fields),
        "data/sources.csv": csv_bytes(data["sources"], ["id", "title", "url", "intake", "checkedAt", "status", "projectionFile"]),
        "data/coverage.csv": csv_bytes(data["coverage"], ["slug", "university", "level", "recordCount", "unit", "cycle", "limits", "sourceIds", "url"]),
        "data/research-fields.csv": csv_bytes(field_rows, context_fields + ["rowKind"] + sorted(FIELD_FIELDS)),
        "data/major-options.csv": csv_bytes(major_rows, context_fields + sorted(MAJOR_FIELDS)),
        "data/admission-groups.csv": csv_bytes(group_rows, context_fields + sorted(GROUP_FIELDS)),
    }
    manifest = {"schemaVersion": 1, "snapshotDate": SNAPSHOT, "owner": OWNER, "counts": counts(data), "projectionInputs": data["provenance"], "coverageInput": data["coverageProvenance"], "files": [{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(files.items())], "interpretation": "Catalogue units are not unique degrees or open applications. Nested rows are subordinate source entries, not additional degree counts. Currentness labels apply only to this dated snapshot. Source check dates are inherited from the public projections; exporting does not recheck the URLs."}
    files["manifest.json"] = json_bytes(manifest)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-projections", type=Path, help="Maintainer import: directory containing the four named public JSON projections; coverage notes are maintained in this repository")
    parser.add_argument("--check", action="store_true", help="Validate and compare reproducible outputs without writing")
    args = parser.parse_args(argv)
    data = import_projections(args.from_projections) if args.from_projections else json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))
    files = render(data)
    for name, body in files.items():
        target = ROOT / name
        if args.check:
            require(target.is_file() and target.read_bytes() == body, "Missing or stale output: " + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    print(json.dumps({"status": "checked" if args.check else "exported", "snapshotDate": SNAPSHOT, "counts": counts(data)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        print("Export rejected: " + str(error), file=sys.stderr)
        sys.exit(1)
