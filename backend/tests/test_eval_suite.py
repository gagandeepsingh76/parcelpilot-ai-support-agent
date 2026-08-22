"""Pytest wrapper so the offline eval suite runs in CI (Step 10).

The standalone CLI (python evals/run_evals.py) shares this code path.
"""

from pathlib import Path

import pytest

from evals.run_evals import FIXTURES_DIR, _fresh_connection, build_cases, run_offline


@pytest.fixture(scope="module")
def eval_conn(tmp_path_factory):
    conn = _fresh_connection(tmp_path_factory.mktemp("evaldb"))
    yield conn
    conn.close()


def test_eval_suite_has_expected_coverage():
    cases = build_cases()
    categories = {case.category for case in cases}
    assert len(cases) >= 12, "keep at least 12 NL scenarios"
    assert {"clean", "conflicting", "unsupported", "leak"} <= categories
    # every case must be runnable offline through its reference plan
    assert all(case.offline_plan for case in cases)


def test_offline_eval_suite_green(eval_conn):
    if not FIXTURES_DIR.exists():
        pytest.skip("synthetic fixtures missing")
    passed, failed = run_offline(eval_conn, verbose=True)
    assert failed == 0, f"{failed} evaluation case(s) failed"
    assert passed >= 12
