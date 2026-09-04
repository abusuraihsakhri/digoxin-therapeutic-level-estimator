#!/usr/bin/env python3
"""
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
"""

import argparse
import csv
import json
import math
import sys
from typing import Dict, Any, List, Optional, Tuple


# ============================================================================
# Constants
# ============================================================================

# Therapeutic ranges (ng/mL)
THERAPEUTIC_LOW = 0.5
THERAPEUTIC_HIGH = 2.0
HF_THERAPEUTIC_LOW = 0.5
HF_THERAPEUTIC_HIGH = 0.9
TOXICITY_THRESHOLD = 2.0
HIGH_TOXICITY_THRESHOLD = 3.0

# Population PK parameters
DEFAULT_VD_PER_KG = 6.0        # L/kg (range 5-7)
VD_REDUCED_PER_KG = 4.5        # L/kg for renal impairment/CHF/elderly
ORAL_BIOAVAILABILITY = 0.7     # 70% for digoxin tablets
ELIXIR_BIOAVAILABILITY = 0.8   # 80% for digoxin elixir
IV_BIOAVAILABILITY = 1.0       # 100% for IV

# Digoxin half-life
HALF_LIFE_NORMAL = 36.0        # hours (1.5 days)
HALF_LIFE_RENAL = 4.5 * 24     # hours (4.5 days in anuria)

# Drug interaction multipliers (increase digoxin level)
DRUG_INTERACTION_MULTIPLIERS = {
    "amiodarone": 1.70,    # ~70% increase
    "verapamil": 1.60,     # ~60% increase
    "quinidine": 1.75,     # ~75% increase
    "propafenone": 1.40,   # ~40% increase
    "spironolactone": 1.25, # ~25% increase
    "cyclosporine": 1.50,  # ~50% increase
    "itraconazole": 1.50,  # ~50% increase
    "clarithromycin": 1.70, # ~70% increase
    "erythromycin": 1.40,  # ~40% increase
    "tetracycline": 1.40,  # ~40% increase
    "indomethacin": 1.30,  # ~30% increase
    "diltiazem": 1.20,     # ~20% increase
    "nifedipine": 1.15,    # ~15% increase
    "captopril": 1.15,     # ~15% increase
}


# ============================================================================
# Core PK Functions
# ============================================================================

def calculate_crcl_cockcroft_gault(
    weight_kg: float,
    age_years: int,
    serum_creatinine_mg_dl: float,
    is_female: bool = False
) -> float:
    """
    Calculate creatinine clearance using Cockcroft-Gault equation.
    
    CrCl = ((140 - age) * weight) / (72 * SCr) * (0.85 if female)
    
    Args:
        weight_kg: Patient weight in kg
        age_years: Patient age in years
        serum_creatinine_mg_dl: Serum creatinine in mg/dL
        is_female: Whether patient is female
        
    Returns:
        CrCl in mL/min
    """
    if serum_creatinine_mg_dl <= 0:
        raise ValueError("Serum creatinine must be positive")
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    if age_years < 0:
        raise ValueError("Age must be non-negative")
    
    crcl = ((140 - age_years) * weight_kg) / (72 * serum_creatinine_mg_dl)
    if is_female:
        crcl *= 0.85
    return round(crcl, 2)


def calculate_digoxin_clearance(crcl_ml_min: float) -> float:
    """
    Calculate digoxin clearance using Koup & Jusko equation.
    
    CL_digoxin (mL/min) = 1.303 * CrCl + 0.88
    
    This accounts for both renal and non-renal elimination.
    
    Args:
        crcl_ml_min: Creatinine clearance in mL/min
        
    Returns:
        Digoxin clearance in mL/min
    """
    if crcl_ml_min < 0:
        raise ValueError("CrCl must be non-negative")
    return round(1.303 * crcl_ml_min + 0.88, 2)


def calculate_volume_of_distribution(
    weight_kg: float,
    vd_per_kg: float = DEFAULT_VD_PER_KG,
    renal_impairment: bool = False,
    heart_failure: bool = False,
    elderly: bool = False
) -> float:
    """
    Calculate digoxin volume of distribution.
    
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
    """
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    
    effective_vd_per_kg = vd_per_kg
    
    # Reduce Vd for special populations
    if renal_impairment:
        effective_vd_per_kg = min(effective_vd_per_kg, VD_REDUCED_PER_KG)
    if heart_failure:
        effective_vd_per_kg *= 0.75  # 25% reduction in CHF
    if elderly:
        effective_vd_per_kg *= 0.85  # 15% reduction in elderly
    
    vd = effective_vd_per_kg * weight_kg
    return round(vd, 1)


def calculate_half_life(vd_liters: float, cl_ml_min: float) -> float:
    """
    Calculate digoxin half-life.
    
    t1/2 = 0.693 * Vd / CL
    (converting CL from mL/min to L/h)
    
    Args:
        vd_liters: Volume of distribution in liters
        cl_ml_min: Digoxin clearance in mL/min
        
    Returns:
        Half-life in hours
    """
    if vd_liters <= 0:
        raise ValueError("Vd must be positive")
    if cl_ml_min <= 0:
        raise ValueError("CL must be positive")
    
    cl_l_per_hour = cl_ml_min * 60 / 1000
    t_half = 0.693 * vd_liters / cl_l_per_hour
    return round(t_half, 1)


def calculate_steady_state_concentration(
    dose_mcg: float,
    cl_ml_min: float,
    tau_hours: float,
    bioavailability: float = ORAL_BIOAVAILABILITY
) -> float:
    """
    Calculate steady-state average concentration.
    
    Css = (F * Dose) / (CL * tau)
    where CL is in L/h and Dose in mcg, giving Css in mcg/L = ng/mL
    
    Args:
        dose_mcg: Digoxin dose in mcg
        cl_ml_min: Digoxin clearance in mL/min
        tau_hours: Dosing interval in hours
        bioavailability: Bioavailability fraction
        
    Returns:
        Steady-state concentration in ng/mL
    """
    if dose_mcg <= 0:
        raise ValueError("Dose must be positive")
    if cl_ml_min <= 0:
        raise ValueError("Clearance must be positive")
    if tau_hours <= 0:
        raise ValueError("Dosing interval must be positive")
    
    # Convert CL from mL/min to L/h
    cl_l_per_hour = cl_ml_min * 60 / 1000
    
    # Css (ng/mL) = (F * Dose_mcg) / (CL_L_per_h * tau_h)
    css = (bioavailability * dose_mcg) / (cl_l_per_hour * tau_hours)
    return round(css, 2)


def calculate_peak_concentration(
    dose_mcg: float,
    vd_liters: float,
    cl_ml_min: float,
    tau_hours: float,
    bioavailability: float = ORAL_BIOAVAILABILITY,
    absorption_ka: float = 0.02  # h^-1 (approximate)
) -> Dict[str, float]:
    """
    Estimate peak and trough digoxin concentrations at steady state.
    
    For oral digoxin (absorption rate ~0.02 h^-1):
    Peak occurs ~1-2 hours post-dose (distribution phase)
    Trough occurs just before next dose
    
    Args:
        dose_mcg: Digoxin dose in mcg
        vd_liters: Volume of distribution in liters
        cl_ml_min: Digoxin clearance in mL/min
        tau_hours: Dosing interval in hours
        bioavailability: Bioavailability
        absorption_ka: Absorption rate constant
        
    Returns:
        Dictionary with peak and trough estimates
    """
    ke = cl_ml_min * 60 / (1000 * vd_liters)  # Elimination rate constant
    
    # Steady-state average
    css_avg = calculate_steady_state_concentration(dose_mcg, cl_ml_min, tau_hours, bioavailability)
    
    # Simplified: trough = Css_avg * e^(-ke * tau/2) approximation
    # More accurate: use one-compartment model
    # Ctrough = (F*Dose/Vd) * e^(-ke*tau) / (1 - e^(-ke*tau))
    cmax = (bioavailability * dose_mcg / vd_liters) / (1 - math.exp(-ke * tau_hours))
    cmin = cmax * math.exp(-ke * tau_hours)
    
    return {
        "peak_ng_ml": round(cmax, 2),
        "trough_ng_ml": round(cmin, 2),
        "average_ng_ml": round(css_avg, 2)
    }


def calculate_loading_dose(
    target_concentration_ng_ml: float,
    vd_liters: float,
    bioavailability: float = ORAL_BIOAVAILABILITY
) -> Dict[str, Any]:
    """
    Calculate digoxin loading dose.
    
    LD = Vd * Ctarget / F
    
    Args:
        target_concentration_ng_ml: Target concentration in ng/mL
        vd_liters: Volume of distribution in liters
        bioavailability: Bioavailability
        
    Returns:
        Dictionary with loading dose
    """
    if vd_liters <= 0:
        raise ValueError("Vd must be positive")
    if target_concentration_ng_ml <= 0:
        raise ValueError("Target concentration must be positive")
    
    ld_mcg = vd_liters * target_concentration_ng_ml / bioavailability
    ld_mg = ld_mcg / 1000
    
    # Typical loading: 50% initial, 25% at 6h, 25% at 12h
    initial_dose = ld_mcg * 0.5
    second_dose = ld_mcg * 0.25
    third_dose = ld_mcg * 0.25
    
    return {
        "target_concentration_ng_ml": target_concentration_ng_ml,
        "vd_liters": vd_liters,
        "total_loading_dose_mcg": round(ld_mcg, 0),
        "total_loading_dose_mg": round(ld_mg, 2),
        "oral_regimen": {
            "dose_1_mcg": round(initial_dose, 0),
            "dose_1_hours": 0,
            "dose_2_mcg": round(second_dose, 0),
            "dose_2_hours": 6,
            "dose_3_mcg": round(third_dose, 0),
            "dose_3_hours": 12,
            "note": "Divided loading: 50% initial, 25% at 6h, 25% at 12h"
        },
        "notes": "Loading dose for acute situations. Monitor levels and renal function."
    }


def calculate_maintenance_dose(
    target_css_ng_ml: float,
    cl_ml_min: float,
    tau_hours: float = 24.0,
    bioavailability: float = ORAL_BIOAVAILABILITY
) -> Dict[str, Any]:
    """
    Calculate maintenance digoxin dose.
    
    MD = Css * CL * tau / F
    (converting units appropriately)
    
    Args:
        target_css_ng_ml: Target steady-state concentration in ng/mL
        cl_ml_min: Digoxin clearance in mL/min
        tau_hours: Dosing interval in hours
        bioavailability: Bioavailability
        
    Returns:
        Dictionary with maintenance dose
    """
    if target_css_ng_ml <= 0:
        raise ValueError("Target concentration must be positive")
    if cl_ml_min <= 0:
        raise ValueError("Clearance must be positive")
    
    # Convert CL from mL/min to L/h
    cl_l_per_hour = cl_ml_min * 60 / 1000
    
    # Dose (mcg) = Css (ng/mL) * CL (L/h) * tau (h) / F
    # ng/mL = mcg/L, so: mcg = mcg/L * L/h * h = mcg ✓
    dose_mcg = target_css_ng_ml * cl_l_per_hour * tau_hours / bioavailability
    dose_mg = dose_mcg / 1000
    
    # Round to available tablet sizes (125mcg = 0.125mg, 250mcg = 0.25mg)
    dose_mcg_rounded = round(dose_mcg / 12.5) * 12.5  # Round to nearest 12.5mcg
    
    return {
        "target_css_ng_ml": target_css_ng_ml,
        "clearance_ml_min": cl_ml_min,
        "interval_hours": tau_hours,
        "bioavailability": bioavailability,
        "calculated_daily_dose_mcg": round(dose_mcg, 1),
        "calculated_daily_dose_mg": round(dose_mg, 3),
        "rounded_daily_dose_mcg": dose_mcg_rounded,
        "rounded_daily_dose_mg": round(dose_mcg_rounded / 1000, 3),
        "predicted_css_ng_ml": round(calculate_steady_state_concentration(dose_mcg_rounded, cl_ml_min, tau_hours, bioavailability), 2),
        "notes": "Standard tablets: 125mcg (0.125mg), 250mcg (0.25mg). Monitor levels after 5-7 days."
    }


def adjust_dose_for_drug_interactions(
    base_dose_mcg: float,
    interacting_drugs: List[str]
) -> Dict[str, Any]:
    """
    Adjust digoxin dose for drug interactions.
    
    Many drugs increase digoxin levels by reducing clearance or
    displacing from tissue binding sites.
    
    Args:
        base_dose_mcg: Calculated base dose in mcg
        interacting_drugs: List of interacting drug names
        
    Returns:
        Dictionary with adjusted dose and interaction details
    """
    if base_dose_mcg <= 0:
        raise ValueError("Base dose must be positive")
    
    interactions = []
    max_multiplier = 1.0
    
    for drug in interacting_drugs:
        drug_lower = drug.lower().strip()
        if drug_lower in DRUG_INTERACTION_MULTIPLIERS:
            mult = DRUG_INTERACTION_MULTIPLIERS[drug_lower]
            interactions.append({
                "drug": drug,
                "level_increase_factor": mult,
                "dose_reduction_factor": round(1 / mult, 2),
                "mechanism": _get_interaction_mechanism(drug_lower)
            })
            max_multiplier = max(max_multiplier, mult)
    
    # Use the most significant interaction for dose adjustment
    adjusted_dose = base_dose_mcg / max_multiplier
    
    return {
        "base_dose_mcg": base_dose_mcg,
        "interacting_drugs": interactions,
        "max_interaction_factor": max_multiplier,
        "adjusted_dose_mcg": round(adjusted_dose, 0),
        "adjusted_dose_mg": round(adjusted_dose / 1000, 3),
        "dose_reduction_percent": round((1 - 1/max_multiplier) * 100, 1),
        "notes": "Reduce digoxin dose when co-administered with interacting drugs. Monitor levels closely."
    }


def _get_interaction_mechanism(drug: str) -> str:
    """Get mechanism of drug interaction with digoxin."""
    mechanisms = {
        "amiodarone": "Reduces renal and non-renal digoxin clearance",
        "verapamil": "Reduces renal digoxin clearance and P-glycoprotein inhibition",
        "quinidine": "Reduces renal and non-renal clearance, displaces from tissue binding",
        "propafenone": "P-glycoprotein inhibition reduces digoxin clearance",
        "spironolactone": "Reduces renal clearance, interferes with assay",
        "cyclosporine": "Reduces renal and biliary clearance",
        "itraconazole": "P-glycoprotein inhibition",
        "clarithromycin": "P-glycoprotein inhibition, reduces renal clearance",
        "erythromycin": "Increases bioavailability via gut flora alteration",
        "tetracycline": "Increases bioavailability via gut flora alteration",
        "indomethacin": "Reduces renal clearance",
        "diltiazem": "Moderate P-glycoprotein inhibition",
        "nifedipine": "Mild increase in clearance",
        "captopril": "Mild reduction in renal clearance"
    }
    return mechanisms.get(drug, "Mechanism varies")


def interpret_digoxin_level(
    concentration_ng_ml: float,
    indication: str = "general"
) -> Dict[str, Any]:
    """
    Interpret digoxin concentration.
    
    Args:
        concentration_ng_ml: Digoxin level in ng/mL
        indication: "general", "heart_failure", or "afib"
        
    Returns:
        Dictionary with interpretation
    """
    if concentration_ng_ml < 0:
        raise ValueError("Concentration must be non-negative")
    
    if indication == "heart_failure":
        low, high = HF_THERAPEUTIC_LOW, HF_THERAPEUTIC_HIGH
        target_desc = "0.5-0.9 ng/mL (heart failure)"
    else:
        low, high = THERAPEUTIC_LOW, THERAPEUTIC_HIGH
        target_desc = "0.5-2.0 ng/mL (general)"
    
    if concentration_ng_ml < low:
        status = "SUBTHERAPEUTIC"
        recommendation = "Increase dose. Level below therapeutic range."
        toxicity_risk = "LOW"
    elif concentration_ng_ml <= high:
        status = "THERAPEUTIC"
        recommendation = "Within therapeutic range. Continue current regimen."
        toxicity_risk = "LOW"
    elif concentration_ng_ml <= HIGH_TOXICITY_THRESHOLD:
        status = "SUPRATHERAPEUTIC"
        recommendation = "Reduce dose or hold. Monitor for toxicity symptoms."
        toxicity_risk = "MODERATE"
    else:
        status = "TOXIC"
        recommendation = "Hold digoxin. Monitor cardiac rhythm. Consider digoxin-specific antibody fragments."
        toxicity_risk = "HIGH"
    
    # Toxicity symptoms
    symptoms = []
    if concentration_ng_ml > TOXICITY_THRESHOLD:
        symptoms = [
            "Nausea, vomiting, anorexia",
            "Visual disturbances (yellow-green halos)",
            "Cardiac arrhythmias (bradycardia, heart block, PVCs)",
            "Confusion, fatigue"
        ]
    
    return {
        "concentration_ng_ml": concentration_ng_ml,
        "status": status,
        "target_range": target_desc,
        "recommendation": recommendation,
        "toxicity_risk": toxicity_risk,
        "toxicity_symptoms": symptoms if symptoms else None
    }


def renal_dose_adjustment(
    base_dose_mcg: float,
    crcl_ml_min: float,
    normal_crcl: float = 120.0
) -> Dict[str, Any]:
    """
    Adjust digoxin dose for renal impairment.
    
    Since ~70% of digoxin is renally eliminated:
    Adjusted dose = Base dose * (patient CL / normal CL)
    
    Args:
        base_dose_mcg: Base dose in mcg for normal renal function
        crcl_ml_min: Patient's CrCl in mL/min
        normal_crcl: Normal CrCl reference (default 120 mL/min)
        
    Returns:
        Dictionary with renal-adjusted dose
    """
    if base_dose_mcg <= 0:
        raise ValueError("Base dose must be positive")
    if crcl_ml_min < 0:
        raise ValueError("CrCl must be non-negative")
    
    # Digoxin CL = 1.303 * CrCl + 0.88
    patient_cl = calculate_digoxin_clearance(crcl_ml_min)
    normal_cl = calculate_digoxin_clearance(normal_crcl)
    
    # Dose adjustment ratio
    ratio = patient_cl / normal_cl
    adjusted_dose = base_dose_mcg * ratio
    
    # Round to nearest 12.5mcg
    adjusted_dose_rounded = round(adjusted_dose / 12.5) * 12.5
    
    # Renal impairment classification
    if crcl_ml_min >= 90:
        renal_class = "NORMAL"
    elif crcl_ml_min >= 60:
        renal_class = "MILD_IMPAIRMENT"
    elif crcl_ml_min >= 30:
        renal_class = "MODERATE_IMPAIRMENT"
    elif crcl_ml_min >= 15:
        renal_class = "SEVERE_IMPAIRMENT"
    else:
        renal_class = "END_STAGE"
    
    return {
        "base_dose_mcg": base_dose_mcg,
        "crcl_ml_min": crcl_ml_min,
        "renal_classification": renal_class,
        "patient_clearance_ml_min": patient_cl,
        "normal_clearance_ml_min": normal_cl,
        "dose_adjustment_ratio": round(ratio, 3),
        "adjusted_dose_mcg": adjusted_dose_rounded,
        "adjusted_dose_mg": round(adjusted_dose_rounded / 1000, 3),
        "dose_reduction_percent": round((1 - ratio) * 100, 1),
        "monitoring_note": "Monitor digoxin levels closely in renal impairment. Check levels every 3-5 days initially."
    }


# ============================================================================
# Full Assessment
# ============================================================================

def full_digoxin_assessment(
    weight_kg: float,
    age_years: int,
    serum_creatinine_mg_dl: float,
    is_female: bool,
    current_dose_mcg: float,
    measured_level_ng_ml: Optional[float] = None,
    indication: str = "general",
    heart_failure: bool = False,
    interacting_drugs: Optional[List[str]] = None,
    route: str = "oral",
    tau_hours: float = 24.0
) -> Dict[str, Any]:
    """
    Complete digoxin dosing assessment.
    
    Args:
        weight_kg: Patient weight in kg
        age_years: Patient age in years
        serum_creatinine_mg_dl: Serum creatinine in mg/dL
        is_female: Whether patient is female
        current_dose_mcg: Current digoxin dose in mcg
        measured_level_ng_ml: Measured digoxin level in ng/mL
        indication: "general" or "heart_failure"
        heart_failure: Whether patient has heart failure
        interacting_drugs: List of interacting medications
        route: "oral", "iv", or "elixir"
        tau_hours: Dosing interval in hours
        
    Returns:
        Complete assessment dictionary
    """
    # Bioavailability based on route
    if route == "iv":
        bioavailability = IV_BIOAVAILABILITY
    elif route == "elixir":
        bioavailability = ELIXIR_BIOAVAILABILITY
    else:
        bioavailability = ORAL_BIOAVAILABILITY
    
    # Step 1: CrCl
    crcl = calculate_crcl_cockcroft_gault(weight_kg, age_years, serum_creatinine_mg_dl, is_female)
    
    # Step 2: Digoxin clearance
    cl_digoxin = calculate_digoxin_clearance(crcl)
    
    # Step 3: Vd
    elderly = age_years > 65
    vd = calculate_volume_of_distribution(weight_kg, renal_impairment=(crcl < 60),
                                          heart_failure=heart_failure, elderly=elderly)
    
    # Step 4: Half-life
    t_half = calculate_half_life(vd, cl_digoxin)
    
    # Step 5: Predicted steady-state
    predicted_conc = calculate_steady_state_concentration(current_dose_mcg, cl_digoxin, tau_hours, bioavailability)
    peak_trough = calculate_peak_concentration(current_dose_mcg, vd, cl_digoxin, tau_hours, bioavailability)
    
    # Step 6: Interpret measured level if available
    level_interp = None
    if measured_level_ng_ml is not None:
        level_interp = interpret_digoxin_level(measured_level_ng_ml, indication)
    
    # Step 7: Drug interactions
    interaction_adj = None
    if interacting_drugs:
        interaction_adj = adjust_dose_for_drug_interactions(current_dose_mcg, interacting_drugs)
    
    # Step 8: Renal dose adjustment
    renal_adj = renal_dose_adjustment(current_dose_mcg, crcl)
    
    # Step 9: Recommended maintenance dose
    target_css = 0.8 if indication == "heart_failure" else 1.2
    recommended = calculate_maintenance_dose(target_css, cl_digoxin, tau_hours, bioavailability)
    
    # Step 10: Loading dose if needed
    loading = None
    if measured_level_ng_ml is not None and measured_level_ng_ml < 0.3:
        loading = calculate_loading_dose(target_css, vd, bioavailability)
    
    return {
        "patient_parameters": {
            "weight_kg": weight_kg,
            "age_years": age_years,
            "serum_creatinine_mg_dl": serum_creatinine_mg_dl,
            "is_female": is_female,
            "crcl_ml_min": crcl,
            "heart_failure": heart_failure,
            "elderly": elderly
        },
        "pk_parameters": {
            "vd_liters": vd,
            "cl_digoxin_ml_min": cl_digoxin,
            "half_life_hours": t_half,
            "half_life_days": round(t_half / 24, 1),
            "bioavailability": bioavailability
        },
        "current_regimen": {
            "dose_mcg": current_dose_mcg,
            "interval_hours": tau_hours,
            "route": route
        },
        "predicted_levels": {
            "average_ng_ml": predicted_conc,
            "peak_ng_ml": peak_trough["peak_ng_ml"],
            "trough_ng_ml": peak_trough["trough_ng_ml"]
        },
        "measured_level_interpretation": level_interp,
        "drug_interactions": interaction_adj,
        "renal_adjustment": renal_adj,
        "recommended_maintenance": recommended,
        "loading_dose": loading,
        "disclaimer": "FOR EDUCATIONAL/RESEARCH USE ONLY. Not a substitute for clinical pharmacist review."
    }


def main(argv=None):
    """CLI entry point for digoxin level estimator."""
    parser = argparse.ArgumentParser(
        prog="digoxin-estimate",
        description="Digoxin Therapeutic Level Estimator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Level command ---
    level_parser = subparsers.add_parser("level", help="Interpret digoxin level")
    level_parser.add_argument("--concentration", type=float, required=True, help="Digoxin level ng/mL")
    level_parser.add_argument("--indication", default="general", choices=["general", "heart_failure", "afib"],
                             help="Clinical indication")

    # --- Dose command ---
    dose_parser = subparsers.add_parser("dose", help="Calculate maintenance dose")
    dose_parser.add_argument("--target", type=float, required=True, help="Target Css ng/mL")
    dose_parser.add_argument("--crcl", type=float, required=True, help="CrCl mL/min")
    dose_parser.add_argument("--interval", type=float, default=24.0, help="Dosing interval hours")
    dose_parser.add_argument("--route", default="oral", choices=["oral", "iv", "elixir"])

    # --- CrCl command ---
    crcl_parser = subparsers.add_parser("crcl", help="Calculate CrCl")
    crcl_parser.add_argument("--weight", type=float, required=True, help="Weight kg")
    crcl_parser.add_argument("--age", type=int, required=True, help="Age years")
    crcl_parser.add_argument("--scr", type=float, required=True, help="Serum creatinine mg/dL")
    crcl_parser.add_argument("--female", action="store_true")

    # --- Interactions command ---
    int_parser = subparsers.add_parser("interactions", help="Drug interaction adjustment")
    int_parser.add_argument("--dose", type=float, required=True, help="Current dose mcg")
    int_parser.add_argument("--drugs", nargs="+", required=True, help="Interacting drug names")

    # --- Assess command ---
    assess_parser = subparsers.add_parser("assess", help="Full assessment")
    assess_parser.add_argument("--weight", type=float, required=True, help="Weight kg")
    assess_parser.add_argument("--age", type=int, required=True, help="Age years")
    assess_parser.add_argument("--scr", type=float, required=True, help="Serum creatinine mg/dL")
    assess_parser.add_argument("--female", action="store_true")
    assess_parser.add_argument("--dose", type=float, required=True, help="Current dose mcg")
    assess_parser.add_argument("--level", type=float, help="Measured level ng/mL")
    assess_parser.add_argument("--hf", action="store_true", help="Heart failure")
    assess_parser.add_argument("--drugs", nargs="+", help="Interacting drugs")

    # --- Audit command (enterprise supervisor) ---
    audit_parser = subparsers.add_parser("audit", help="Run enterprise supervisor audit")
    audit_parser.add_argument("--task-id", required=True, help="Task identifier")
    audit_parser.add_argument("--target", default="SPECIMEN-001", help="Target identifier")
    audit_parser.add_argument("--primary", type=float, default=10.0, help="Primary metric")
    audit_parser.add_argument("--secondary", type=float, default=3.0, help="Secondary metric")
    audit_parser.add_argument("--descriptor", default="NOMINAL", help="Status descriptor")
    audit_parser.add_argument("--critical", action="store_true", help="Critical flag")

    # --- Chat command (enterprise supervisor) ---
    chat_parser = subparsers.add_parser("chat", help="Supervisory chat query")
    chat_parser.add_argument("query", nargs="+", help="Chat query text")

    # --- Verify-audit command ---
    verify_parser = subparsers.add_parser("verify-audit", help="Verify audit trail integrity")

    # --- Serve command (API server) ---
    serve_parser = subparsers.add_parser("serve", help="Run FastAPI server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind")

    args = parser.parse_args(argv)

    if args.command == "level":
        result = interpret_digoxin_level(args.concentration, args.indication)
        print(json.dumps(result, indent=2))

    elif args.command == "dose":
        cl = calculate_digoxin_clearance(args.crcl)
        f = {"oral": ORAL_BIOAVAILABILITY, "iv": IV_BIOAVAILABILITY, "elixir": ELIXIR_BIOAVAILABILITY}[args.route]
        result = calculate_maintenance_dose(args.target, cl, args.interval, f)
        print(json.dumps(result, indent=2))

    elif args.command == "crcl":
        crcl = calculate_crcl_cockcroft_gault(args.weight, args.age, args.scr, args.female)
        cl = calculate_digoxin_clearance(crcl)
        print(json.dumps({"crcl_ml_min": crcl, "digoxin_cl_ml_min": cl}, indent=2))

    elif args.command == "interactions":
        result = adjust_dose_for_drug_interactions(args.dose, args.drugs)
        print(json.dumps(result, indent=2))

    elif args.command == "assess":
        result = full_digoxin_assessment(
            weight_kg=args.weight,
            age_years=args.age,
            serum_creatinine_mg_dl=args.scr,
            is_female=args.female,
            current_dose_mcg=args.dose,
            measured_level_ng_ml=args.level,
            heart_failure=args.hf,
            interacting_drugs=args.drugs
        )
        print(json.dumps(result, indent=2))

    elif args.command == "audit":
        from agents.supervisor import SystemSupervisor
        from agents.models import SystemTaskPayload
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.descriptor,
            is_critical_flag=args.critical
        )
        dossier = supervisor.process_task(payload)
        print(json.dumps(dossier.to_dict(), indent=2, default=str))

    elif args.command == "chat":
        from agents.supervisor import SystemSupervisor
        supervisor = SystemSupervisor(model_provider="mock")
        query = " ".join(args.query)
        response = supervisor.query_supervisory_chat(query)
        print(json.dumps({"response": response}, indent=2))

    elif args.command == "verify-audit":
        from agents.base import AuditLogger
        verified = AuditLogger.verify_integrity()
        trail_len = len(AuditLogger.get_trail())
        print(json.dumps({"integrity_verified": verified, "trail_length": trail_len}, indent=2))

    elif args.command == "serve":
        import uvicorn
        from agents.api import app
        uvicorn.run(app, host=args.host, port=args.port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
