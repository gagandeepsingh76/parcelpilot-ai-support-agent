# Candidate Data Pack (local only - not committed)

Place the supplied assessment files here:

```
data_pack/
├── 01_Support_Policy_v3_CURRENT.pdf
├── 02_Support_Policy_v2_DEPRECATED.pdf
├── 03_Cancellation_and_Service_Credit_SOP_v4.pdf
├── 04_Product_Operations_Guide_and_Known_Issues.pdf
├── 05_Northstar_Logistics_Enterprise_Agreement.pdf
├── 06_LumenWorks_Service_Agreement.pdf
└── ParcelPilot_Assessment_Data.xlsx
```

The backend ingests everything in this folder at startup (`make ingest` /
`python -m app.ingestion.run`). Filenames are matched by pattern, so cosmetic
renames still resolve; metadata (version/status/type/customer-scope) comes from
the embedded document structure first and falls back to filename parsing.
