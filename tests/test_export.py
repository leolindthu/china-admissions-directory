import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("catalogue_export", ROOT / "scripts/export.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))

    def corrupted(self, edit, message):
        data = copy.deepcopy(self.data)
        edit(data)
        with self.assertRaisesRegex(ValueError, message):
            export.validate(data)

    def test_full_snapshot_and_counts(self):
        export.validate(self.data)
        c = export.counts(self.data)
        self.assertEqual(c["catalogueUnits"], 1660)
        self.assertEqual(c["unknownTeachingLanguage"], 102)
        self.assertEqual(c["nestedQualifierOnlyRows"], 2)
        self.assertEqual(c["nestedResearchFieldRows"], 1938)
        self.assertEqual(c["byLevel"], {"master": 1194, "undergraduate": 466})

    def test_duplicates_rejected(self):
        self.corrupted(lambda d: d["records"][1].update(id=d["records"][0]["id"]), "Duplicate record")
        self.corrupted(lambda d: d["sources"][1].update(id=d["sources"][0]["id"]), "Duplicate source")

    def test_unknown_nested_private_fields_rejected(self):
        self.corrupted(lambda d: d["records"][0].update(applicantEmail="private@example.com"), "Unapproved fields")
        self.corrupted(lambda d: next(r for r in d["records"] if r.get("researchFields"))["researchFields"][0].update(bankAccount="123"), "Unapproved fields")
        self.corrupted(lambda d: d["sources"][0].update(internalPath="/Users/person/source.pdf"), "Unapproved fields")

    def test_private_text_rejected_in_allowed_fields(self):
        self.corrupted(lambda d: d["records"][0].update(notes=["Email private@example.com"]), "Private path or email")
        self.corrupted(lambda d: d["records"][0].update(notes=["/Users/person/private-file"]), "Private path or email")

    def test_source_identity_and_official_url(self):
        self.corrupted(lambda d: d["records"][0].update(sourceIds=["missing"]), "Unresolved source")
        self.corrupted(lambda d: d["records"][0].update(sourceUrl="https://example.com/admissions"), "Non-allowlisted")
        self.corrupted(lambda d: d["sources"][0].update(url="https://user:password@yzbm.tsinghua.edu.cn/"), "URL credentials|Private path or email")
        self.corrupted(lambda d: d["records"][0].update(sourceUrl="https://yzbm.tsinghua.edu.cn/unrelated"), "Primary URL")

    def test_count_and_coverage_drift_rejected(self):
        self.corrupted(lambda d: d["records"].pop(), "Snapshot counts")
        self.corrupted(lambda d: d["coverage"][0].update(recordCount=25), "Coverage count")
        self.corrupted(lambda d: next(r for r in d["records"] if r.get("listedMajors"))["listedMajors"].pop(), "Nested count")

    def test_uncertainty_and_language_qualifiers_preserved(self):
        self.corrupted(lambda d: d["records"][0].update(cycleStatus="applications_open"), "Unknown cycle")
        self.corrupted(lambda d: d["records"][0].update(intake="2028"), "Unexpected intake")
        self.corrupted(lambda d: next(r for r in d["records"] if r["projectionFile"] != "catalogue-public.json").pop("languageEvidence"), "Language qualifier")
        self.assertTrue(any(s["status"] == "broken_link_404" for s in self.data["sources"]))

    def test_csv_unicode_arrays_nulls_and_formula_safety(self):
        output = export.csv_bytes([{"name": "北京大学", "null": None, "array": ["清华", "北京"], "formula": " =1+1", "code": "001"}], ["name", "null", "missing", "array", "formula", "code"])
        rows = list(csv.DictReader(io.StringIO(output.decode("utf-8"))))
        self.assertEqual(rows[0]["name"], "北京大学")
        self.assertEqual(rows[0]["null"], "null")
        self.assertEqual(rows[0]["missing"], "")
        self.assertEqual(json.loads(rows[0]["array"]), ["清华", "北京"])
        self.assertEqual(rows[0]["formula"], "' =1+1")
        self.assertEqual(rows[0]["code"], "001")

    def test_subordinate_parent_links_and_qualifier_rows(self):
        files = export.render(self.data)
        rows = list(csv.DictReader(io.StringIO(files["data/research-fields.csv"].decode("utf-8"))))
        ids = {r["id"] for r in self.data["records"]}
        self.assertEqual(len(rows), 1938)
        self.assertTrue(all(r["parentRecordId"] in ids for r in rows))
        qualifiers = [r for r in rows if r["rowKind"] == "qualifier_only"]
        self.assertEqual({r["parentRecordId"] for r in qualifiers}, {"sjtu-m-en-020", "sjtu-m-en-021"})
        self.assertTrue(all(r["language"] == "English" and r["duration"] == "2 years" for r in qualifiers))

    def test_deterministic_outputs_and_manifest_hashes(self):
        files = export.render(self.data)
        self.assertEqual(files, export.render(copy.deepcopy(self.data)))
        for name, body in files.items():
            self.assertEqual((ROOT / name).read_bytes(), body, name)
        manifest = json.loads(files["manifest.json"])
        for entry in manifest["files"]:
            self.assertEqual(export.sha(files[entry["path"]]), entry["sha256"])
            self.assertEqual(len(files[entry["path"]]), entry["bytes"])

    def test_import_reads_only_four_public_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for filename in export.INPUTS:
                data = {"updatedAt": export.SNAPSHOT}
                for field in ("sources", "records"):
                    data[field] = [{k: v for k, v in r.items() if k != "projectionFile"} for r in self.data[field] if r["projectionFile"] == filename]
                (path / filename).write_bytes(export.json_bytes(data))
            (path / "private-not-for-export.json").write_text('{"secret":"must never be read"}')
            imported = export.import_projections(path)
            self.assertEqual(imported["records"], self.data["records"])
            self.assertEqual(imported["sources"], self.data["sources"])
            self.assertNotIn("must never be read", json.dumps(imported))
            filename = next(iter(export.INPUTS))
            changed = json.loads((path / filename).read_text())
            changed["privateRecords"] = []
            (path / filename).write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "Unapproved fields"):
                export.import_projections(path)


if __name__ == "__main__":
    unittest.main()
