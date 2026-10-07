# Schema and counting rules — version 1

This is a dated snapshot schema, not a live admissions API. UTF-8 JSON is authoritative. CSVs are derived views. Original Chinese and English labels are preserved as supplied in Agora's public projections, including source spelling and punctuation; missing translations are not filled in.

## Top-level JSON

| Field | Meaning |
|---|---|
| `schemaVersion` | `1` |
| `snapshotDate` | `2026-10-07`; date of the curation snapshot, not every programme's intake |
| `owner`, `independence` | Visible Agora ownership and non-affiliation statement |
| `provenance` | Four public projection basenames, SHA-256 hashes and counts; no internal paths |
| `coverageProvenance` | Hash and allowed fields of the published website's coverage definitions, recorded when copied into this repository's coverage notes |
| `sources` | 100 official-source records, including explicit unavailable-source evidence |
| `records` | 1,660 catalogue units, retaining nested source units |
| `coverage` | 18 university/level scopes, counting labels, cycle statements, gaps and live directory URLs |

## Catalogue record allowlist

Required fields are `id`, `university`, `level`, `recordType`, `degreeType`, `intake`, `cycleStatus`, `department`, `nameOriginal`, `nameEnglish`, `language`, `sourceIds`, `sourceUrl` and added provenance field `projectionFile`.

| Field(s) | Type and interpretation |
|---|---|
| `id` | Stable identifier within this snapshot. Not a university-issued application ID. |
| `university` | One of the nine university names in the README. |
| `level` | `undergraduate` or `master`. |
| `recordType` | Source counting unit; see below. |
| `degreeType` | String or null. Preserve source naming; null means unestablished. |
| `intake` | String or null. Values are `2026`, `2027`, `2026/2027 academic year`, or null. |
| `cycleStatus` | Snapshot-specific interpretation of cycle evidence; see below. |
| `department`, `departmentEnglish`, `departmentCode` | Source department labels/codes. The last two are optional. Empty strings do not imply a verified institution-wide programme. |
| `programmeCode` | Optional string; preserve leading zeros and source coding. |
| `nameOriginal`, `nameEnglish` | Source labels or null; at least one must be present. Neither implies teaching language. |
| `language` | String or null. May describe a mixed/staged route rather than one language. |
| `languageEvidence` | Optional source-linked explanation. Present for 1,299 rows; absent in the 361-row base projection. Absence is not a waiver of language requirements. |
| `duration` | Optional string or null; literal published duration, not normalized. |
| `studyModes` | Optional array of literal source labels. |
| `notes` | Optional array of source qualifications/limitations; preserve alongside the row. |
| `facultyGroup`, `groupKey`, `groupTitle` | Optional published grouping metadata; not additional academic awards. |
| `researchFieldsLabel` | Optional source-specific label for subordinate rows. |
| `researchFields` | Optional array: fields, directions or subordinate qualifications. Exact allowed keys: `code`, `nameOriginal`, `nameEnglish`, `nameSource`, `language`, `studyMode`, `duration`, `notes`. `nameSource` is a literal source label, not a source ID. Two rows have no name/code and only language/duration; CSV `rowKind` exposes this. |
| `listedMajors` | Optional array of major-option cells. Allowed keys: `nameOriginal`, `nameEnglish`, `department`, `duration`. A cell may combine more than one major/track. |
| `admissionGroups` | Optional array with `nameOriginal`, `specializationOptionsOriginal` (string array), `openChoiceStatementsOriginal` (string array). Nested specialization options are not independent degree counts. |
| `openChoiceStatements` | Optional string array of source statements about choices; not a list of individually verified selectable degrees. |
| `sourceIds` | Nonempty array referencing `sources[].id`; preserve all references. |
| `sourceUrl` | Primary official URL, which must equal one of the referenced source URLs. |
| `projectionFile` | Added export provenance: one of the four allowed public projection basenames. |

### Counting units

| `recordType` | How to read one row |
|---|---|
| `department_degree` | A degree entry within a department; fields remain subordinate. |
| `department_degree_language` | A department/degree/teaching-language catalogue entry; repeated degree titles may occur. |
| `admission_division` | An admissions division containing options. |
| `admission_college` | A college admissions entry containing options. |
| `admission_department` | An undergraduate department admissions entry, potentially with nested groups. |
| `admission_programme` | A named programme entry in the cited source; listing alone does not establish an open application. |
| `admission_group` | An admissions grouping of major options. |
| `admission_route` | A route or cluster; do not count its nested options again as degrees. |

### Cycle statuses

`prior_cycle_catalogue` and `historical_2026` preserve earlier-cycle material. `undated_live_catalogue` means the table itself has no verified intake year. `latest_catalogue_cycle_unstated` means the latest retrieved catalogue's intake is not explicit. `academic_year_2026_2027_guide_intake_2026` preserves HIT's academic-year label with a 2026-entry guide. `current_catalogue`, `verified_2027`, `selected_current_route` and `current_notice_and_live_catalogue` identify supported current/selected notices **at the snapshot date**; read the record intake and coverage limitations to determine scope. None asserts that applications are currently open.

## Source and coverage allowlists

Each source contains `id`, `title`, `url`, `intake` (string or null), `checkedAt`, `status` and added `projectionFile`. `status` is literal retrieval/cycle evidence rather than a globally normalized availability flag. All source links use HTTPS and one of the 12 official hostnames explicitly allowed by the exporter. A link can be retained with a failed status; its presence does not promise current availability.

Coverage contains only `slug`, `university`, `level`, `cycle`, `unit`, `limits` (string array), `sourceIds`, `recordCount` and `url`. The notes were taken from already published catalogue definitions; `recordCount` and the live URL are derived. `data/coverage-notes.json` is the repository-maintained input for these statements. Review it when a source scope changes; it is not inferred automatically from programme names.

## Nulls, missing fields and CSVs

- JSON null means unknown or not established in this snapshot. An omitted optional key means that the public projection did not supply that field. An empty array means no nested entries were supplied, not proof that none exist at the university.
- CSV preserves explicit null as the text `null`; an omitted field becomes an empty cell. A genuinely empty source string also becomes an empty cell; use JSON where that distinction matters.
- Arrays and nested objects in CSV cells are compact JSON strings, not comma-separated guesses. `officialSourceUrls` and `sourceCheckedDates` align positionally with `sourceIds`.
- The three subordinate CSVs use `parentRecordId` plus one-based `ordinal`. `rowKind` is `named_field` or `qualifier_only` in research-fields.csv. The parent intake/cycle and source context travel with every subordinate row. These are derived identifiers, not official programme codes.
- Files use UTF-8 without a BOM and LF record endings. A leading apostrophe protects CSV strings whose first non-space character is `=`, `+`, `-` or `@`, or that begin with a tab/newline/carriage return. JSON preserves the exact underlying value. Import identifier/code columns as text in spreadsheet tools to retain leading zeros.

## Reproducibility and validation

The importer reads only these filenames from the chosen source directory:

| Public projection | Units | Sources |
|---|---:|---:|
| `catalogue-public.json` | 361 | 59 |
| `catalogue-expanded-public.json` | 760 | 19 |
| `catalogue-ustc-nanjing-public.json` | 233 | 10 |
| `catalogue-xjtu-hit-public.json` | 306 | 12 |

Unknown keys fail closed at every nested layer. Validation checks identifiers, source references and hosts, per-file and university/level counts, coverage uniqueness, nested counts, date/cycle labels, teaching-language qualifiers, and private path/email/control-character guards. It cannot independently determine whether a source is factually correct or currently reachable. No network requests occur.

`--check` re-renders all derived files in memory and requires exact bytes. The manifest hashes generated data files, not itself. Source hashes identify the precise input bytes; they are provenance, not a fresh factual review. Tests exercise corruption and boundary cases in addition to validating the complete dataset.

To update to another snapshot, review official evidence, the allowed fields/hosts, explicit count invariants, coverage statements and source dates together. Do not silently change constants or erase unresolved source gaps just to make a new import pass.
