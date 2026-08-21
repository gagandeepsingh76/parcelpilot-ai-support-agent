"""Unit tests for the document-metadata contract (filename -> doc_type/version/status/scope)."""

from app.ingestion.metadata import derive_docmeta

ACCOUNTS = [
    {"account_id": "ACC-001", "account_name": "Northstar Logistics"},
    {"account_id": "ACC-002", "account_name": "LumenWorks Ltd"},
]


def meta_for(filename: str, first_page: str = "") -> dict:
    return derive_docmeta(filename, [first_page] if first_page else [], ACCOUNTS)


def test_policy_current_with_version_from_filename():
    meta = meta_for("01_Support_Policy_v3_CURRENT.pdf")
    assert meta["doc_type"] == "policy"
    assert meta["version"] == "3"
    assert meta["status"] == "CURRENT"
    assert meta["customer_scope"] == "global"
    assert meta["assumed_current"] is False


def test_deprecated_status_detected_from_filename():
    meta = meta_for("02_Support_Policy_v2_DEPRECATED.pdf")
    assert meta["status"] == "DEPRECATED"


def test_sop_and_guide_types():
    assert meta_for("03_Cancellation_and_Service_Credit_SOP_v4.pdf")["doc_type"] == "sop"
    assert meta_for("04_Product_Operations_Guide_and_Known_Issues.pdf")["doc_type"] == "product-guide"


def test_version_and_status_fall_back_to_content():
    first_page = "Some Agreement\nVersion: 2\nStatus: CURRENT\n"
    meta = meta_for("07_Mystery_Agreement.pdf", first_page)
    assert meta["version"] == "2"
    assert meta["status"] == "CURRENT"


def test_missing_status_assumes_current_with_flag():
    meta = meta_for("08_Plain_Agreement.pdf", "Bare agreement text without status line.")
    assert meta["status"] == "CURRENT"
    assert meta["assumed_current"] is True


def test_scope_tokens_map_to_account_ids():
    northstar = meta_for("05_Northstar_Logistics_Enterprise_Agreement.pdf")
    lumen = meta_for("06_LumenWorks_Service_Agreement.pdf")
    assert northstar["customer_scope"] == "ACC-001"
    assert lumen["customer_scope"] == "ACC-002"


def test_doc_id_from_leading_number_and_title_from_content():
    meta = meta_for(
        "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "Northstar Logistics Enterprise Agreement\nDocument ID: X\n",
    )
    assert meta["doc_id"] == "05"
    assert meta["title"].lower().startswith("northstar logistics enterprise")


def test_unknown_type_raises_value_error():
    try:
        meta_for("09_Completely_Unknown_Thing.pdf")
    except ValueError as exc:
        assert "doc_type" in str(exc)
    else:
        raise AssertionError("expected ValueError for unclassifiable filename")
