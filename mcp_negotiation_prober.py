"""mcp-negotiation-prober: does your MCP server negotiate honestly?

Oct 10–12, 2026: a public probe ran 4-era handshake tests against 78
public MCP endpoints — 0 of 78 genuinely validated the newest era,
66/78 (85%) silently downgraded the request, and 6 echoed fictional
eras verbatim. Then the probe was RETRACTED because the stateless
2026-07-28 spec removed the handshake entirely — exposing that nobody
can currently SEE the modern cohort. The instrument gap is real.

This tool probes any MCP endpoint across protocol eras — including
fictional ones — and classifies each response as:
  HONEST            server echoes the era it actually negotiated
  SILENT-DOWNGRADE  you asked for 2026-07-28; it answered 2025-03-26
                    without declaring the downgrade
  ECHO-PARROT       it parroted back a fictional era verbatim (it never
                    reads the field at all)
  UNKNOWN           no usable protocolVersion in the response

The prober is built for the stateless era too: for 2026-07-28 it also
checks the per-request `mcp-protocol-version` HTTP header the spec
requires. Network calls go only to the endpoint you specify
(`--endpoint`); a `--fixture` mode runs offline against canned
responses for CI/testing.

Honest scope: results describe the endpoint's negotiation behavior,
not its security. A silent downgrade may be a compatibility choice —
but it is one you should see, not discover in production.
"""

import argparse
import json
import sys
import urllib.request

# Protocol eras: real ones the tool probes, plus fictional ones the
# server must never echo back.
REAL_ERAS = ("2024-11-05", "2025-03-26", "2025-06-18", "2026-07-28")
FICTIONAL_ERAS = ("1999-01-01", "2037-12-31")
ALL_ERAS = REAL_ERAS + FICTIONAL_ERAS


def classify_response(requested, echoed, header_version=None):
    """Classify one handshake response. Pure function.

    requested: the protocolVersion we sent.
    echoed: the protocolVersion the server returned (or None).
    header_version: the mcp-protocol-version HTTP header value (or None).
    """
    if requested in FICTIONAL_ERAS and echoed == requested:
        return {"verdict": "ECHO-PARROT",
                "detail": "server echoed fictional era %r verbatim — it "
                          "does not read the field" % requested}
    if echoed is None:
        return {"verdict": "UNKNOWN",
                "detail": "no protocolVersion in response"}
    if echoed == requested:
        if requested == "2026-07-28" and header_version is not None \
                and header_version != requested:
            return {"verdict": "SILENT-DOWNGRADE",
                    "detail": "body says %r but stateless header says %r"
                              % (echoed, header_version)}
        return {"verdict": "HONEST",
                "detail": "server negotiated %r as requested" % echoed}
    if echoed in REAL_ERAS and REAL_ERAS.index(echoed) < \
            REAL_ERAS.index(requested):
        return {"verdict": "SILENT-DOWNGRADE",
                "detail": "asked %r, server answered %r without declaring "
                          "the downgrade" % (requested, echoed)}
    return {"verdict": "UNKNOWN",
            "detail": "unexpected version %r" % echoed}


def probe_era(endpoint, era, timeout=10):
    """Send one initialize handshake; return (echoed, header_version)."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": era,
                   "capabilities": {},
                   "clientInfo": {"name": "mcp-negotiation-prober",
                                  "version": "1.0.0"}},
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream",
                 "mcp-protocol-version": era})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        header = resp.headers.get("mcp-protocol-version")
        raw = resp.read(64_000).decode("utf-8", "replace")
    echoed = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        res = obj.get("result", {})
        if isinstance(res, dict) and "protocolVersion" in res:
            echoed = res["protocolVersion"]
            break
    return echoed, header


def probe_endpoint(endpoint, send_fn=None, eras=ALL_ERAS):
    """Probe all eras; return list of per-era result dicts."""
    send = send_fn or probe_era
    results = []
    for era in eras:
        try:
            echoed, header = send(endpoint, era)
            error = None
        except Exception as exc:  # noqa: BLE001 — report, don't crash
            echoed, header, error = None, None, "%r" % exc
        c = classify_response(era, echoed, header_version=header)
        results.append({"era": era, "echoed": echoed,
                        "header_version": header, "error": error, **c})
    return results


def summarize(results):
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return {"verdicts": counts,
            "worst": ("ECHO-PARROT" if counts.get("ECHO-PARROT")
                      else "SILENT-DOWNGRADE" if counts.get("SILENT-DOWNGRADE")
                      else "UNKNOWN" if counts.get("UNKNOWN") else "HONEST"),
            "results": results}


def render_markdown(endpoint, summary):
    lines = ["# MCP Negotiation Probe — %s" % endpoint, "",
             "- Eras probed: %d" % len(summary["results"]),
             "- Overall: **%s**" % summary["worst"], ""]
    for v, n in summary["verdicts"].items():
        lines.append("- %s: %d" % (v, n))
    lines.append("")
    for r in summary["results"]:
        lines.append("## era %s → %s" % (r["era"], r["verdict"]))
        if r["error"]:
            lines.append("- transport error: %s" % r["error"])
        else:
            lines.append("- echoed: %r, stateless header: %r"
                         % (r["echoed"], r["header_version"]))
        lines.append("- %s" % r["detail"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Probe an MCP endpoint's protocol negotiation honesty.")
    ap.add_argument("--endpoint", default="",
                    help="MCP endpoint URL to probe (required unless "
                         "--fixture)")
    ap.add_argument("--fixture", action="store_true",
                    help="offline mode: canned silent-downgrade server")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--out", default="-")
    args = ap.parse_args(argv)

    def fixture_send(_endpoint, era):
        # Canned dishonest server: downgrades everything to 2025-03-26,
        # echoes fictional eras verbatim.
        if era in FICTIONAL_ERAS:
            return era, None
        return "2025-03-26", None

    if args.fixture:
        send, endpoint = fixture_send, "fixture://canned"
    elif args.endpoint:
        send, endpoint = None, args.endpoint
    else:
        ap.error("--endpoint or --fixture is required")
    summary = summarize(probe_endpoint(endpoint, send_fn=send))
    out = json.dumps(summary, indent=2) if args.as_json \
        else render_markdown(endpoint, summary)
    if args.out == "-":
        sys.stdout.write(out)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
    return 1 if summary["worst"] in ("ECHO-PARROT", "SILENT-DOWNGRADE") \
        else 0


if __name__ == "__main__":
    sys.exit(main())
