# Digoxin Therapeutic Level Estimator

> **Domain:** Clinical Pharmacology & Precision Pharmacotherapy  
> **Reference Guidelines & Standards:** `CPIC Guidelines & FDA Table of Pharmacogenomic Biomarkers`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Digoxin Therapeutic Level Estimator

Real pharmacokinetic calculations for digoxin therapeutic drug monitoring.
Implements population PK with renal-based clearance adjustment.

Key formulas:
- Therapeutic range: 0.5-2.0 ng/mL (HF: 0.5-0.9 ng/mL)
- Vd: 5-7 L/kg (reduced in renal impairment, CHF, elderly)
- CL = 1.303 * CrCl + 0.88 (mL/min) [Koup & Jusko]
- t1/2 = 0.693 * Vd / CL
- Loading dose: LD = Vd * Ctarget / F
- Maintenance dose: MD = Css * CL * tau / F (F = 0.7 oral)
- Steady state: Css = (F * Dose) / (CL * tau) [simplified]

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`calculate_crcl_cockcroft_gault()`**: Calculate creatinine clearance using Cockcroft-Gault equation.

CrCl = ((140 - age) * weight) / (72 * SCr) * (0.85 if female)

Args:
    weight_kg: Patient weight in kg
    age_years: Patient age in years
    serum_creatinine_mg_dl: Serum creatinine in mg/dL
    is_female: Whether patient is female
    
Returns:
    CrCl in mL/min
- **`calculate_digoxin_clearance()`**: Calculate digoxin clearance using Koup & Jusko equation.

CL_digoxin (mL/min) = 1.303 * CrCl + 0.88

This accounts for both renal and non-renal elimination.

Args:
    crcl_ml_min: Creatinine clearance in mL/min
    
Returns:
    Digoxin clearance in mL/min
- **`calculate_volume_of_distribution()`**: Calculate digoxin volume of distribution.

Normal: 5-7 L/kg
Reduced in: renal impairment, CHF, elderly, hypothyroidism

Args:
    weight_kg: Patient weight in kg
    vd_per_kg: Base Vd in L/kg
    renal_impairment: Whether patient has renal impairment
    heart_failure: Whether patient has heart failure
    elderly: Whether patient is elderly (>65)
    
Returns:
    Volume of distribution in liters
- **`calculate_half_life()`**: Calculate digoxin half-life.

t1/2 = 0.693 * Vd / CL
(converting CL from mL/min to L/h)

Args:
    vd_liters: Volume of distribution in liters
    cl_ml_min: Digoxin clearance in mL/min
    
Returns:
    Half-life in hours
- **`calculate_steady_state_concentration()`**: Calculate steady-state average concentration.

Css = (F * Dose) / (CL * tau)
where CL is in L/h and Dose in mcg, giving Css in mcg/L = ng/mL

Args:
    dose_mcg: Digoxin dose in mcg
    cl_ml_min: Digoxin clearance in mL/min
    tau_hours: Dosing interval in hours
    bioavailability: Bioavailability fraction
    
Returns:
    Steady-state concentration in ng/mL

---

## 📐 Mathematical Formulation & Logic

```text
  Key formulas:
  Calculate creatinine clearance using Cockcroft-Gault equation.
  Calculate digoxin clearance using Koup & Jusko equation.
  Calculate digoxin volume of distribution.
  Calculate digoxin half-life.
```

---

## 💻 CLI Quickstart & Usage

### Installation

```bash
pip install -e .
# Or install with development dependencies:
pip install -e ".[dev]"
```

### 1. Interpret Digoxin Level
```bash
python cli.py level --concentration 1.2
python cli.py level --concentration 0.7 --indication heart_failure
```

### 2. Calculate Maintenance Dose
```bash
python cli.py dose --target 1.0 --crcl 80
python cli.py dose --target 0.8 --crcl 60 --interval 24 --route oral
```

### 3. Calculate CrCl
```bash
python cli.py crcl --weight 70 --age 70 --scr 1.4
python cli.py crcl --weight 60 --age 65 --scr 1.2 --female
```

### 4. Drug Interaction Adjustment
```bash
python cli.py interactions --dose 250 --drugs amiodarone
python cli.py interactions --dose 250 --drugs amiodarone verapamil
```

### 5. Full Assessment
```bash
python cli.py assess --weight 70 --age 70 --scr 1.4 --dose 250
python cli.py assess --weight 70 --age 70 --scr 1.4 --dose 250 --hf --drugs amiodarone
```

### 6. Enterprise Supervisor Audit
```bash
python cli.py audit --task-id TASK-001 --primary 12.0 --secondary 4.0
python cli.py chat "Explain digoxin dosing"
python cli.py verify-audit
```

### 7. Run API Server
```bash
python cli.py serve --host 0.0.0.0 --port 8000
```

### Parameter Reference
- `level`: Interpret a digoxin concentration level
- `dose`: Calculate maintenance dose based on target Css and CrCl
- `crcl`: Calculate creatinine clearance (Cockcroft-Gault)
- `interactions`: Adjust dose for drug interactions
- `assess`: Full pharmacokinetic assessment
- `audit`: Run enterprise supervisor audit
- `chat`: Query the supervisory chat
- `verify-audit`: Verify audit trail integrity
- `serve`: Run the FastAPI REST server

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Notes
- The audit trail uses HMAC-SHA256 with a secret key from the `AUDIT_SECRET_KEY` environment variable
- If not set, a cryptographically secure random key is generated at startup
- For production deployments, always set `AUDIT_SECRET_KEY` to ensure audit trail persistence

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t digoxin-therapeutic-level-estimator .
docker run -p 8000:8000 digoxin-therapeutic-level-estimator
```

Or using Docker Compose:

```bash
# Set a secure audit key for production
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up -d
```

---

## 📁 Project Structure

```
digoxin-therapeutic-level-estimator/
├── agents/                  # Enterprise agent framework
│   ├── api.py              # FastAPI REST API
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider factory
│   ├── metrics.py          # Prometheus metrics
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry
│   ├── supervisor.py       # Supervisor orchestrator
│   └── workers.py          # Specialized worker agents
├── tests/                  # Test suite
│   ├── test_digoxin_therapeutic_level_estimator.py
│   └── test_enrichment.py
├── web/                    # Web operations console
│   └── index.html
├── cli.py                  # CLI entry point
├── digoxin_pk.py           # Core PK calculations
├── enrichment.py           # Enrichment feature modules
├── simulator.py            # High-throughput simulator
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
└── LICENSE                 # MIT License
```
