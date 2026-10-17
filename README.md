# mcp-negotiation-prober

**Your MCP server agreed to the newest protocol. Did it mean it?**

Oct 10–12, 2026: a public probe ran 4-era handshake tests against 78
public MCP endpoints — **0 of 78 genuinely validated the newest era**,
66/78 (85%) silently downgraded the request, and 6 echoed fictional
eras verbatim. Then the probe was RETRACTED, because the stateless
2026-07-28 spec removed the handshake entirely — exposing that nobody
can currently SEE the modern cohort.

This tool is the instrument the retraction proved missing: it probes
any MCP endpoint across protocol eras — **including fictional ones** —
and classifies each response honestly.

## What it checks (per era)

| Verdict | Meaning |
|---------|---------|
| `HONEST` | server negotiated the era you asked for |
| `SILENT-DOWNGRADE` | you asked `2026-07-28`; it answered `2025-03-26` without declaring it — or the stateless `mcp-protocol-version` header disagrees with the body |
| `ECHO-PARROT` | it parroted a fictional era (`1999-01-01`) verbatim — it never reads the field |
| `UNKNOWN` | no usable `protocolVersion` in the response |

Probes `2024-11-05`, `2025-03-26`, `2025-06-18`, `2026-07-28` plus the
fictional `1999-01-01` and `2037-12-31`. Built for the stateless era:
for `2026-07-28` it cross-checks the per-request
`mcp-protocol-version` HTTP header the spec requires.

## Install

Zero third-party dependencies — Python 3.9+ only.

```bash
git clone https://github.com/Iceman2050/mcp-negotiation-prober.git
cd mcp-negotiation-prober
pip install -e .
```

## Usage

```bash
# Probe your own endpoint (network only touches the URL you give it)
python3 mcp_negotiation_prober.py --endpoint https://mcp.example.com/mcp

# Offline demo against a canned dishonest server (CI-safe)
python3 mcp_negotiation_prober.py --fixture --json
```

Exit code `1` on ECHO-PARROT or SILENT-DOWNGRADE — drop it into CI to
catch servers that lie about protocol support.

## Honest scope — what this does NOT claim

- Results describe **negotiation behavior**, not security. A silent
  downgrade may be a compatibility choice — but it is one you should
  see, not discover in production.
- It cannot audit servers that don't expose an HTTP endpoint.

## Tests

```bash
python3 -m pytest -q
```

Fully offline: covers every verdict class (honest, silent-downgrade,
echo-parrot ×2 fictional eras, unknown), stateless-header
cross-checking, transport-error reporting, and fixture mode.

## License

MIT — see [LICENSE](LICENSE).
## Built by Ingenious AI

This tool is built and maintained by **Ingenious AI**. Get early access to our AI security platforms:

- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20DisclosureGuard
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20ModelMinder
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20TermsWatch
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20Vibe-Code%20Audit
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20Rogue-Agent%20Defense
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20BreachHunter
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20ChatBreaker
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20Agent%20Flight%20Recorder
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20Agent%20Auth%20Gateway
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20DomainGuard
- https://wa.me/5016691053?text=Hi%20Ingenious%20AI!%20I%20want%20early%20access%20to%20ContentCraft%20AI


> Built by Ingenious AI with Muse — get free tokens with invite code `2HCQH1`
