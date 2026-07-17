# M0-05 simulator and PWA safety/security review

- Date: 2026-07-17
- Scope: synthetic M0 campaign, explainable local PWA and laboratory ingress only
- Status: approved for M0-05 evidence; field support remains `unverified`
- Review authority: `docs/security/OpenBREC-RF-threat-model.md`

## Decision

M0-05 may expose the `lab-sim` PWA to a browser only through host loopback. MQTT, PostgreSQL, API and worker remain on the internal Docker network and receive no host ports. This boundary permits local explanation without turning the laboratory profile into a field network profile.

The PWA is an explanation surface over a versioned synthetic projection. It is not a detector, a distress terminal or an operational dispatch system. Every consolidated zone remains `abstained`; loss, partition or missing capability can only reduce confidence or coverage. The interface keeps observation, evidence and inference separate and displays timestamp, zone, precision, confidence, coverage, sources, missing capabilities and explanation.

## Implemented controls and evidence

1. The six-node scenario uses fixture logical time and canonical ordering; ten input-order variations produce one result hash.
2. Loss, duplicate, partition, logical brownout, restart and malicious-peer outcomes are explicit; accepted/quarantined units reconcile with zero unresolved dispositions.
3. The expected PWA projection is bound to the scenario by canonical SHA-256.
4. UI copy prohibits a presence or absence conclusion and keeps abstention and missing capabilities visible.
5. `ui-smoke` builds the exact locked frontend, starts a loopback-only preview, drives Chromium, exercises zone selection and semantic filtering, then cuts browser connectivity and reloads from the service worker.
6. Browser console/page errors fail the gate. The accepted receipt records six visible nodes, three semantic layers, three inference events, offline reload passed and zero console errors.
7. `offline-startup` separately confirms valid/invalid contract paths and denies external network access to the contained runtime after the web ingress change.

Evidence is stored in `evidence/m0/{simulator,core-replay,determinism,ui-smoke,offline-startup}/m0-05-receipt.json`; every receipt evaluates `1a805cca90521d48dd45026ee37f8ef0cfc5ff80` with `dirty: false`.

## Governed residuals

| Residual | State after M0-05 | Required resolution |
|---|---|---|
| Local browser access while core remains contained | resolved for `lab-sim` under M0-R013 | Reopen if ingress leaves loopback, a core port is published or offline browser reload fails. |
| Browser binary provenance, frontend SBOM, licenses and vulnerability evidence | planned for M0-06 under M0-R007/M0-R012 | Bind the browser revision and full dependency/image graph to final supply-chain receipts. |
| Live worker/PostgreSQL projection path | planned for M0-06 under M0-R017 | Integrate durable runtime storage before claiming end-to-end live projections. The current PWA intentionally consumes a versioned synthetic fixture. |
| Field terminal authentication, authorization, TLS, device hardening and remote ingress | not implemented; field `unverified` | Define and test a separate field profile. Do not reuse the loopback laboratory decision as field approval. |
| Responder comprehension, language and accessibility under incident stress | not claimed | Run the human-factor gates defined by the beacon/human UX specification before an operational UI claim. |

## Stop conditions

- any host bind other than loopback in `lab-sim`;
- any MQTT, PostgreSQL, API or worker host port or external egress;
- any projection hash not bound to the versioned scenario;
- any hidden uncertainty, source loss, missing capability or abstention;
- any wording that confirms presence, absence or rescue from this synthetic evidence;
- any browser smoke that succeeds without a real offline reload;
- any claim that this PWA, scenario or ingress is a supported field profile.
