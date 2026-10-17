"""Tests for mcp_negotiation_prober. Offline: fixture mode + stubs only."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_negotiation_prober import (  # noqa: E402
    ALL_ERAS,
    REAL_ERAS,
    classify_response,
    main,
    probe_endpoint,
    summarize,
)


def test_honest():
    r = classify_response("2025-06-18", "2025-06-18")
    assert r["verdict"] == "HONEST"


def test_silent_downgrade():
    r = classify_response("2026-07-28", "2025-03-26")
    assert r["verdict"] == "SILENT-DOWNGRADE"
    assert "2025-03-26" in r["detail"]


def test_echo_parrot_fictional():
    r = classify_response("1999-01-01", "1999-01-01")
    assert r["verdict"] == "ECHO-PARROT"


def test_echo_parrot_second_fictional():
    r = classify_response("2037-12-31", "2037-12-31")
    assert r["verdict"] == "ECHO-PARROT"


def test_unknown_when_no_echo():
    r = classify_response("2025-06-18", None)
    assert r["verdict"] == "UNKNOWN"


def test_stateless_header_mismatch():
    r = classify_response("2026-07-28", "2026-07-28",
                          header_version="2025-03-26")
    assert r["verdict"] == "SILENT-DOWNGRADE"


def test_stateless_header_match_is_honest():
    r = classify_response("2026-07-28", "2026-07-28",
                          header_version="2026-07-28")
    assert r["verdict"] == "HONEST"


def test_probe_endpoint_with_stub():
    def honest(_ep, era):
        # A server that truly validates: honest on real eras,
        # fictional eras can't be "honest" so it returns unknown.
        return (era, era) if era in REAL_ERAS else (None, None)
    results = probe_endpoint("x://y", send_fn=honest, eras=ALL_ERAS)
    assert len(results) == len(ALL_ERAS)
    assert all(r["verdict"] == "HONEST"
               for r in results if r["era"] in REAL_ERAS)
    assert all(r["verdict"] == "UNKNOWN"
               for r in results if r["era"] not in REAL_ERAS)


def test_probe_endpoint_reports_transport_error():
    def boom(_ep, _era):
        raise ConnectionError("refused")
    results = probe_endpoint("x://y", send_fn=boom, eras=["2025-06-18"])
    assert results[0]["error"] and results[0]["verdict"] == "UNKNOWN"


def test_summarize_worst_echo_parrot():
    s = summarize([{"verdict": "HONEST"}, {"verdict": "ECHO-PARROT"}])
    assert s["worst"] == "ECHO-PARROT"
    assert s["verdicts"] == {"HONEST": 1, "ECHO-PARROT": 1}


def test_fixture_main_flags_downgrade(capsys):
    code = main(["--fixture", "--json"])
    out = capsys.readouterr().out
    assert '"SILENT-DOWNGRADE"' in out and '"ECHO-PARROT"' in out
    assert code == 1


def test_all_eras_includes_fictional():
    assert "1999-01-01" in ALL_ERAS and "2026-07-28" in ALL_ERAS
