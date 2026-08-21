"""Data-pack ingestion pipeline.

Modules:
    pdfparse   - PDF text extraction + section splitting (pypdf)
    xlsxload   - workbook sheets -> dicts (openpyxl)
    metadata   - filename/content -> document metadata contract
    run        - orchestrator; rebuilds SQLite from scratch
                 (python -m app.ingestion.run)

Import submodules directly, e.g. `from app.ingestion.run import ingest`.
(The package deliberately avoids eager imports so `python -m` execution stays clean.)
"""

__all__: list[str] = []
