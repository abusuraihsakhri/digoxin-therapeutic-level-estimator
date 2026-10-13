# Digoxin Therapeutic Level Estimator

An educational adult population pharmacokinetic estimator for digoxin. The standalone browser interface estimates steady-state **average** concentration, creatinine clearance, digoxin clearance, and half-life; the Python CLI also exposes illustrative loading, maintenance, interaction and level-interpretation functions.

> **Research and education only.** This software is not clinically validated for diagnosis, toxicity exclusion or medication orders. Digoxin has a narrow therapeutic index. Interpret measured concentrations with symptoms, ECG, renal function, electrolytes, interacting drugs and the time since the last dose.

## Browser application

Open [`web/index.html`](web/index.html) in a modern desktop or mobile browser. No server, account, Python runtime or downloads are necessary. Enter adult demographics, creatinine, dosing details and optionally a measured digoxin concentration. Select **Calculate estimate** to view the population-PK calculations; **Export JSON** saves the current non-identifying results.

The static application processes inputs entirely in the browser; it does not send data to a service, save it in browser storage, or use analytics. Do not enter identifiable patient information. External reference links are optional and open only when clicked.

A GitHub Actions Pages deployment is configured for pushes to `master`. GitHub Pages must be enabled with **GitHub Actions** as the publishing source in repository settings. A live application link should be added here only after successful deployment and verification.

## PK model and limitations

- **Cockcroft–Gault CrCl (mL/min)**: `(140 − age) × supplied weight / (72 × SCr)`, multiplied by `0.85` with the female coefficient. This approximation assumes stable renal function and is sensitive to the weight selection.
- **Digoxin clearance (mL/min)**: `1.303 × CrCl + CL_nonrenal`, with an explicit **40 mL/min default** for nonrenal clearance. This is an assumed population parameter, *not* universal; published estimates vary with patient characteristics and heart-failure severity. The Python function permits an alternative nonrenal term.
- **Distribution volume**: 6 L/kg baseline, reduced under crude renal-impairment, older-age and heart-failure modifiers. This is not a fitted multicompartment model.
- **Average concentration (ng/mL)**: `F × dose_mcg / (CL_L_per_hour × interval_hours)`. This predicts a steady-state *average*, not a clinical trough or early post-dose peak.
- **Half-life (hours)**: `0.693 × Vd_L / CL_L_per_hour`.
- **Bioavailability assumptions**: tablet `0.70`, oral solution `0.80`, IV `1.00`. Actual absorption varies.
- **Sampling**: draw digoxin concentration just before the next scheduled dose, or at least six hours after the previous dose. A single serum result must not independently drive dose changes.

The browser uses JavaScript for local calculations; it does **not** run Python through Pyodide or require a backend. The Python API and CLI use the same main population equations, but separate implementations must be regression tested for parity. Do not interpret computed mathematical `peak`/`trough` values as post-distribution measured serum concentrations.

**References:** [Digoxin prescribing information (DailyMed)](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=b69e2d2b-725c-4f2c-912d-d068da5c0f31&type=display) · [Published comparison of digoxin dosing algorithms and Koup–Jusko model](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/769541).

## Python and API

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
node tests/browser_smoke.cjs        # optional JavaScript smoke test
```

Examples:

```bash
python cli.py crcl --weight 70 --age 70 --scr 1.4
python cli.py level --concentration 0.8 --indication heart_failure
python cli.py assess --weight 70 --age 70 --scr 1.4 --dose 125 --hf
python cli.py interactions --dose 125 --drugs amiodarone
python cli.py dose --target 0.8 --crcl 60
python cli.py serve --host 127.0.0.1 --port 8000
```

When serving, the browser calculator is at `http://127.0.0.1:8000/`, the interactive API documentation at `/docs` and a health endpoint at `/health`. The `/api/audit` and `/api/chat` endpoints are auxiliary **nonclinical demonstration interfaces**, unrelated to the standalone browser calculator. The chat currently supports **mock mode only**; no external model calls or clinical verification occur. The `enrichment.py` named modules are generic rule prototypes and **do not** implement validated two-compartment PK, electrolyte modeling, drug interactions or AF rate-control prediction.

To access `/api/audit/logs`, set `DIGOXIN_AUDIT_ADMIN_KEY` in the backend environment and pass the same secret in the `X-Audit-Key` request header. The API denies audit-log reads when no key is configured. The audit trail is **in-memory** and HMAC-linked; it is not a persistent compliance log. Identifier-pattern checks are heuristic and are **not** HIPAA de-identification. Avoid patient identifiers and do not expose the demonstration API to untrusted users without further authentication and data-security review.

## Containers

```bash
docker build -t digoxin-estimator .
docker run --rm -p 8000:8000 digoxin-estimator
```

The Docker image starts the FastAPI server on port 8000. Docker Compose is also provided, with optional `AUDIT_SECRET_KEY` for a consistent in-memory ledger signing key.

## Testing and compatibility

CI runs Python 3.10, 3.11 and 3.12 tests, syntax compilation, a Node-based browser-logic smoke test, dependency auditing and an optional GitHub Pages deployment. The browser app uses standard HTML and JavaScript without third-party libraries. The Node smoke test is **not** a substitute for a deployed real-browser end-to-end test.

## License

[MIT](LICENSE).
