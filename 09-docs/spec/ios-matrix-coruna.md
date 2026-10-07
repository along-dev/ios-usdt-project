# Supported iOS Version Matrix

This table maps `group.html` exploit-chain module selection to bundled Stage1/Stage2 files in the project root.

| iOS Range | Stage1 Module | Stage2 Module | Notes |
|-----------|---------------|---------------|-------|
| 15.2 – 15.5 | `Stage1_15.2_15.5_jacurutu.js` | via offset flags | PAC path depends on runtime offsets |
| 15.6 – 16.1.2 | `Stage1_15.6_16.1.2_bluebird.js` | via offset flags | |
| 16.2 – 16.5.1 | `Stage1_16.2_16.5.1_terrorbird.js` | `Stage2_16.3_16.5.1_seedbell` | `offsets.CpDW_T` |
| 16.6 – 17.2.1 | `Stage1_16.6_17.2.1_cassowary.js` | `Stage2_17.0_17.2.1_seedbell` + optional pre | `offsets.wF8NpI` |
| 16.6 – 16.7.x alt | same | `Stage2_16.6_16.7.12_seedbell` | `offsets.LJ1EuL` alternate branch |
| 15.0 – 16.2 fallback | varies | `Stage2_15.0_16.2_breezy15` | `offsets.IqxL92` |
| 13.0 – 14.x fallback | varies | `Stage2_13.0_14.x_breezy` | default fallback |

## Validation status

- **Bundled modules**: all files listed in `verify_setup.py` are present locally.
- **Stage2 16.6–16.7.12 branch**: module file exists and hash mapping is wired in `group.html`; physical device matrix testing is still required before production use.
- **Stage3**: local payload delivery uses `payloads/bootstrap.dylib` via patched `Stage3_VariantA/B.js`.

## Lab-only reminder

Run only on authorized devices in an isolated network. Patch levels, A18 devices, and iOS 17.3+ may require additional Stage modules not bundled here.
