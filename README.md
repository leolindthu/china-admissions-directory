# China admissions catalogue data

An openly inspectable catalogue snapshot curated by **Agora Scholars**, an independent China admissions advisory service. It brings selected official international undergraduate and master's catalogues into one source-linked dataset.

**Snapshot: 7 October 2026.** Repository: [leolindthu/china-admissions-directory](https://github.com/leolindthu/china-admissions-directory).

Browse the [live catalogue directory](https://www.agorascholars.com/admissions/programmes) or read [Agora's service and source methodology](https://www.agorascholars.com/admissions/about). Agora owns this curation and export code. The universities own their admissions decisions and official materials. This repository does not imply university affiliation, partnership, endorsement or an application channel.

## What is included

**1,660 catalogue units from 9 universities**, covering 466 undergraduate units and 1,194 master's units, with 100 official source records. These are **not 1,660 distinct degrees**, not all programmes in China, and not a list of applications currently open.

| University | Undergraduate units | Master's units |
|---|---:|---:|
| Tsinghua University | 24 | 94 |
| Peking University | 23 | 220 |
| Shanghai Jiao Tong University | 43 | 111 |
| Zhejiang University | 92 | 284 |
| Fudan University | 67 | 163 |
| University of Science and Technology of China | 18 | 36 |
| Nanjing University | 52 | 127 |
| Xi’an Jiaotong University | 50 | 107 |
| Harbin Institute of Technology | 97 | 52 |

A unit may be a department–degree entry, a department–degree–language entry, a division, a college, a programme, an admission group or a route. Read `recordType` and the matching coverage note before comparing counts. Repeated titles across departments, teaching languages or tracks are retained when the official catalogue lists them separately.

The export also retains 1,938 subordinate research-field/qualification rows, 154 major-option cells and 27 admission groups containing 104 specialization options. These subordinate rows are **not added** to the 1,660-unit total. Two SJTU subordinate rows contain only teaching-language/duration qualifications; the research-field CSV marks them `qualifier_only`.

## Download and use

- [catalogue.json](data/catalogue.json): compact, lossless canonical export, including records, sources, coverage limits and input hashes.
- [catalogue.csv](data/catalogue.csv): one row per catalogue unit, with original names, cycles, source links and nested arrays encoded as JSON cells.
- [sources.csv](data/sources.csv): official document/page URLs, titles, intake labels, checked dates and retrieval limitations. This is the complete source-link index for this snapshot.
- [coverage.csv](data/coverage.csv): the 18 university/level coverage statements and live directory links.
- [research-fields.csv](data/research-fields.csv), [major-options.csv](data/major-options.csv), [admission-groups.csv](data/admission-groups.csv): subordinate tables joined by `parentRecordId` and one-based `ordinal`.
- [manifest.json](manifest.json): counts, snapshot date, input provenance and export hashes.
- [SCHEMA.md](SCHEMA.md): field meanings, nulls, counting rules and reproducibility instructions.

For example, this standard-library Python snippet selects Nanjing master's rows with an unstated intake, without assuming that catalogue publication year is intake year:

```python
import json
from pathlib import Path

data = json.loads(Path("data/catalogue.json").read_text(encoding="utf-8"))
for row in data["records"]:
    if row["university"] == "Nanjing University" and row["level"] == "master":
        if row["intake"] is None:
            print(row["id"], row["nameOriginal"], row["sourceUrl"])
```

## Applicant and counsellor resources

- [How to choose a China admissions consultant](https://www.agorascholars.com/admissions/guides/china-admissions-consultant): questions to ask when comparing admissions support and reviewing an adviser's proposed scope.
- [Adviser comparison worksheet (CSV)](https://www.agorascholars.com/downloads/china-admissions-adviser-comparison.csv): an editable ten-question worksheet for recording and comparing advisers' answers.

- [High-school preparation guide and planning worksheet](guides/high-school-preparation/README.md): a dated, source-linked framework for comparing selected mainland China and Hong Kong undergraduate routes, with a blank worksheet and explicit intake limits. Prepared 9 October 2026; this separate resource does not refresh the catalogue snapshot.

These resources are published by Agora Scholars, the curator of this dataset. For dataset attribution, use the snapshot metadata in [CITATION.cff](CITATION.cff) and retain the official source references for any rows you use.

## Check the cycle before using a row

Most rows are 2026 references. There are 1,211 rows explicitly labelled 2026, 152 labelled 2027, 97 labelled **2026/2027 academic year**, and 200 with unknown/unstated intake. The academic-year label is preserved literally: HIT's accompanying guide specifies September 2026 entry; it is not evidence of a 2027 intake.

The verified 2027 Tsinghua master's catalogue, Nanjing undergraduate list and selected programme notices do not make every other catalogue current. `current_*` and `verified_2027` statuses describe evidence available **on the snapshot date**. They do not mean an application window is open today. See every university/level's `cycle` and `limits` in [coverage.csv](data/coverage.csv).

Teaching language is unknown for 102 units. Some sources distinguish language at research-field level, and an English title or document does not establish English teaching. The export retains all 11 Zhejiang language-qualification notes and the SJTU Engineering Cluster's stage-dependent language qualification. The planned SJTU Robotics option is excluded from the listed-major count. Check the source and route-specific requirements rather than treating these rows as eligibility decisions.

Source `checkedAt` dates are inherited from the public catalogue's research record. Creating this repository did not fetch or revalidate those URLs. One retained PKU source explicitly has status `broken_link_404`; its URL is evidence of a coverage gap, not an accessible verified programme list. No missing document rows have been invented.

## Reproduce and validate offline

Requires Python 3.9+; no packages, credentials or network access are needed.

```sh
python3 scripts/export.py --check
python3 -m unittest discover -s tests -v
```

`python3 scripts/export.py` regenerates CSVs and the manifest from the checked-in canonical JSON. For maintainers importing a new copy of this exact snapshot, `--from-projections /path/to/public-projections` reads only four explicitly named public JSON files. It uses this repository's reviewed `data/coverage-notes.json` for coverage notes. It does not read university PDFs, raw spreadsheets, client records or any other files in the supplied directory. Unknown fields, unsupported cycles and count changes fail validation and require an explicit reviewed schema/snapshot update.

## Corrections and contributions

Open an issue in this repository with the affected record ID or coverage slug, the exact official source URL, the relevant text/page/table, the intake year and the date you checked it. Say whether the issue concerns a transcription, teaching language, cycle, unavailable source or scope limitation. Do not include applicant identities, passports, application documents, private correspondence or personal contact information.

Corrections require source review. A changed page hash is not by itself evidence of a changed admission rule. University admissions offices determine personal eligibility and current requirements; this public catalogue is a research aid.

## Attribution and rights

When referring to this dataset, use “Agora Scholars, China admissions catalogue data, snapshot 2026-10-07,” and retain the record's official source references. [LICENSE](LICENSE) covers Agora's original export code, documentation and original curation only. University names, catalogue labels, source facts, quotations and linked documents remain subject to their respective rights; Agora claims no ownership of university materials. No university PDFs or raw source workbooks are redistributed here.
