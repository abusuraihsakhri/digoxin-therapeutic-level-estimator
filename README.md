# Digoxin Therapeutic Level Estimator

Real pharmacokinetic calculator for digoxin therapeutic drug monitoring with renal dose adjustment and drug interaction considerations.

## Clinical Background

Digoxin has a narrow therapeutic index and is primarily renally eliminated (~70%). Dosing must account for:
- **Renal function** (CrCl-based clearance)
- **Volume of distribution** (reduced in CHF, renal impairment, elderly)
- **Drug interactions** (amiodarone, verapamil, quinidine significantly increase levels)

## Key Formulas

| Parameter | Formula |
|-----------|---------|
| CrCl (Cockcroft-Gault) | `((140 - age) × weight) / (72 × SCr) × 0.85 if female` |
| Digoxin CL (Koup & Jusko) | `CL = 1.303 × CrCl + 0.88` (mL/min) |
| Volume of distribution | `Vd = 5-7 L/kg` (reduced in CHF/renal/elderly) |
| Half-life | `t1/2 = 0.693 × Vd / CL` |
| Steady-state | `Css = (F × Dose) / (CL × τ)` |
| Loading dose | `LD = Vd × Ctarget / F` |
| Maintenance dose | `MD = Css × CL × τ / F` |

## Therapeutic Ranges

| Indication | Target Range |
|------------|-------------|
| General (AF rate control) | 0.5-2.0 ng/mL |
| Heart failure | 0.5-0.9 ng/mL |
| Toxicity threshold | >2.0 ng/mL |

## Installation

```bash
# No dependencies required - Python 3.8+ stdlib only
cd digoxin-therapeutic-level-estimator
```

## Usage

### Interpret Digoxin Level
```bash
python cli.py level --concentration 1.2
python cli.py level --concentration 0.7 --indication heart_failure
python cli.py level --concentration 2.5
```

### Calculate Maintenance Dose
```bash
python cli.py dose --target 1.0 --crcl 80
python cli.py dose --target 0.8 --crcl 40 --route oral
```

### Calculate CrCl
```bash
python cli.py crcl --weight 70 --age 70 --scr 1.4
python cli.py crcl --weight 60 --age 75 --scr 1.8 --female
```

### Drug Interaction Adjustment
```bash
python cli.py interactions --dose 250 --drugs amiodarone verapamil
```

### Full Assessment
```bash
python cli.py assess --weight 70 --age 70 --scr 1.4 --dose 250
python cli.py assess --weight 70 --age 70 --scr 1.4 --dose 250 --level 1.8 --hf --drugs amiodarone
```

## Output Format

All commands output JSON. Example:
```json
{
  "concentration_ng_ml": 1.2,
  "status": "THERAPEUTIC",
  "target_range": "0.5-2.0 ng/mL (general)",
  "recommendation": "Within therapeutic range. Continue current regimen.",
  "toxicity_risk": "LOW"
}
```

## Drug Interactions

The following drugs significantly increase digoxin levels:

| Drug | Level Increase | Mechanism |
|------|---------------|-----------|
| Amiodarone | ~70% | Reduces renal and non-renal clearance |
| Verapamil | ~60% | Reduces renal clearance, P-gp inhibition |
| Quinidine | ~75% | Reduces clearance, displaces from tissue |
| Clarithromycin | ~70% | P-gp inhibition |
| Cyclosporine | ~50% | Reduces renal and biliary clearance |

## Tests

```bash
python -m pytest test_digoxin_pk.py -v
```

## Disclaimer

**FOR EDUCATIONAL AND RESEARCH USE ONLY.** This calculator is not a substitute for clinical pharmacist review. Digoxin dosing requires careful consideration of renal function, drug interactions, electrolyte status (especially K+), and thyroid function.

## References

- Koup JR, Jusko WJ, et al. Digoxin pharmacokinetics: role of renal failure in dosage regimen design. *Clin Pharmacol Ther*. 1975;18(1):9-21.
- Bauman JL, et al. The effect of renal impairment on digoxin pharmacokinetics. *J Clin Pharmacol*. 1984;24(1):57-62.
- Digoxin Investigation Group. The effect of digoxin on mortality and morbidity in patients with heart failure. *N Engl J Med*. 1997;336(8):525-533.

## License

MIT License. See [LICENSE](LICENSE) for details.
