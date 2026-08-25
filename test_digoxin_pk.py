"""
Tests for Digoxin Therapeutic Level Estimator.
"""
import pytest
from digoxin_pk import (
    calculate_crcl_cockcroft_gault,
    calculate_digoxin_clearance,
    calculate_volume_of_distribution,
    calculate_half_life,
    calculate_steady_state_concentration,
    calculate_peak_concentration,
    calculate_loading_dose,
    calculate_maintenance_dose,
    adjust_dose_for_drug_interactions,
    interpret_digoxin_level,
    renal_dose_adjustment,
    full_digoxin_assessment,
    main,
    THERAPEUTIC_LOW,
    THERAPEUTIC_HIGH,
    HF_THERAPEUTIC_LOW,
    HF_THERAPEUTIC_HIGH,
    ORAL_BIOAVAILABILITY,
)


# ============================================================================
# CrCl Tests
# ============================================================================

class TestCrCl:
    def test_normal_male(self):
        crcl = calculate_crcl_cockcroft_gault(70, 50, 1.0, False)
        expected = ((140 - 50) * 70) / (72 * 1.0)
        assert abs(crcl - expected) < 0.1

    def test_female_reduction(self):
        crcl_m = calculate_crcl_cockcroft_gault(70, 50, 1.0, False)
        crcl_f = calculate_crcl_cockcroft_gault(70, 50, 1.0, True)
        assert abs(crcl_f - crcl_m * 0.85) < 0.1

    def test_invalid_scr(self):
        with pytest.raises(ValueError):
            calculate_crcl_cockcroft_gault(70, 50, 0, False)


# ============================================================================
# Digoxin Clearance Tests
# ============================================================================

class TestDigoxinClearance:
    def test_koup_jusko(self):
        # CL = 1.303 * 100 + 0.88 = 131.18
        cl = calculate_digoxin_clearance(100)
        assert abs(cl - 131.18) < 0.01

    def test_zero_crcl(self):
        cl = calculate_digoxin_clearance(0)
        assert abs(cl - 0.88) < 0.01

    def test_negative_crcl(self):
        with pytest.raises(ValueError):
            calculate_digoxin_clearance(-10)


# ============================================================================
# Volume of Distribution Tests
# ============================================================================

class TestVolumeOfDistribution:
    def test_normal(self):
        vd = calculate_volume_of_distribution(70)
        assert abs(vd - 420.0) < 0.1  # 70 * 6.0

    def test_heart_failure(self):
        vd_normal = calculate_volume_of_distribution(70)
        vd_hf = calculate_volume_of_distribution(70, heart_failure=True)
        assert vd_hf < vd_normal

    def test_elderly(self):
        vd_normal = calculate_volume_of_distribution(70)
        vd_elderly = calculate_volume_of_distribution(70, elderly=True)
        assert vd_elderly < vd_normal

    def test_renal_impairment(self):
        vd_normal = calculate_volume_of_distribution(70)
        vd_renal = calculate_volume_of_distribution(70, renal_impairment=True)
        assert vd_renal < vd_normal

    def test_combined_factors(self):
        vd = calculate_volume_of_distribution(70, heart_failure=True, elderly=True, renal_impairment=True)
        assert vd < calculate_volume_of_distribution(70)

    def test_invalid_weight(self):
        with pytest.raises(ValueError):
            calculate_volume_of_distribution(0)


# ============================================================================
# Half-life Tests
# ============================================================================

class TestHalfLife:
    def test_calculation(self):
        # t1/2 = 0.693 * 420 / (1.303*80+0.88) / (60/1000)
        vd = 420.0
        cl = calculate_digoxin_clearance(80)
        t_half = calculate_half_life(vd, cl)
        assert t_half > 0
        # Normal digoxin half-life is ~36 hours
        assert 20 < t_half < 60

    def test_invalid_vd(self):
        with pytest.raises(ValueError):
            calculate_half_life(0, 100)


# ============================================================================
# Steady-State Concentration Tests
# ============================================================================

class TestSteadyState:
    def test_basic_calculation(self):
        css = calculate_steady_state_concentration(250, 100, 24)
        assert css > 0
        assert css < 5  # Reasonable range

    def test_higher_dose_higher_css(self):
        css_low = calculate_steady_state_concentration(125, 100, 24)
        css_high = calculate_steady_state_concentration(250, 100, 24)
        assert css_high > css_low

    def test_lower_clearance_higher_css(self):
        css_normal = calculate_steady_state_concentration(250, 100, 24)
        css_low_cl = calculate_steady_state_concentration(250, 50, 24)
        assert css_low_cl > css_normal

    def test_invalid_dose(self):
        with pytest.raises(ValueError):
            calculate_steady_state_concentration(0, 100, 24)


# ============================================================================
# Peak/Trough Tests
# ============================================================================

class TestPeakTrough:
    def test_peak_higher_than_trough(self):
        result = calculate_peak_concentration(250, 420, 100, 24)
        assert result["peak_ng_ml"] > result["trough_ng_ml"]

    def test_average_between_peak_trough(self):
        result = calculate_peak_concentration(250, 420, 100, 24)
        assert result["trough_ng_ml"] <= result["average_ng_ml"] <= result["peak_ng_ml"]


# ============================================================================
# Loading Dose Tests
# ============================================================================

class TestLoadingDose:
    def test_basic(self):
        result = calculate_loading_dose(1.5, 420)
        assert result["total_loading_dose_mcg"] > 0
        assert result["total_loading_dose_mg"] > 0

    def test_divided_doses(self):
        result = calculate_loading_dose(1.5, 420)
        regimen = result["oral_regimen"]
        assert regimen["dose_1_mcg"] > regimen["dose_2_mcg"]

    def test_higher_target_higher_dose(self):
        low = calculate_loading_dose(1.0, 420)
        high = calculate_loading_dose(2.0, 420)
        assert high["total_loading_dose_mcg"] > low["total_loading_dose_mcg"]


# ============================================================================
# Maintenance Dose Tests
# ============================================================================

class TestMaintenanceDose:
    def test_basic(self):
        result = calculate_maintenance_dose(1.0, 100)
        assert result["calculated_daily_dose_mcg"] > 0
        assert result["rounded_daily_dose_mcg"] > 0

    def test_renal_impairment(self):
        normal = calculate_maintenance_dose(1.0, 100)
        impaired = calculate_maintenance_dose(1.0, 50)
        assert impaired["calculated_daily_dose_mcg"] < normal["calculated_daily_dose_mcg"]

    def test_rounding(self):
        result = calculate_maintenance_dose(1.0, 100)
        # Should be rounded to nearest 12.5mcg
        assert result["rounded_daily_dose_mcg"] % 12.5 == 0


# ============================================================================
# Drug Interaction Tests
# ============================================================================

class TestDrugInteractions:
    def test_amiodarone(self):
        result = adjust_dose_for_drug_interactions(250, ["amiodarone"])
        assert result["adjusted_dose_mcg"] < 250
        assert result["dose_reduction_percent"] > 0

    def test_verapamil(self):
        result = adjust_dose_for_drug_interactions(250, ["verapamil"])
        assert result["adjusted_dose_mcg"] < 250

    def test_multiple_drugs(self):
        result = adjust_dose_for_drug_interactions(250, ["amiodarone", "verapamil"])
        assert len(result["interacting_drugs"]) == 2
        # Uses the most significant interaction
        assert result["adjusted_dose_mcg"] < 250

    def test_no_interactions(self):
        result = adjust_dose_for_drug_interactions(250, ["aspirin"])
        assert result["adjusted_dose_mcg"] == 250
        assert len(result["interacting_drugs"]) == 0

    def test_invalid_dose(self):
        with pytest.raises(ValueError):
            adjust_dose_for_drug_interactions(0, ["amiodarone"])


# ============================================================================
# Level Interpretation Tests
# ============================================================================

class TestLevelInterpretation:
    def test_therapeutic(self):
        result = interpret_digoxin_level(1.2)
        assert result["status"] == "THERAPEUTIC"

    def test_subtherapeutic(self):
        result = interpret_digoxin_level(0.3)
        assert result["status"] == "SUBTHERAPEUTIC"

    def test_supratherapeutic(self):
        result = interpret_digoxin_level(2.5)
        assert result["status"] == "SUPRATHERAPEUTIC"

    def test_toxic(self):
        result = interpret_digoxin_level(3.5)
        assert result["status"] == "TOXIC"
        assert result["toxicity_symptoms"] is not None

    def test_heart_failure_range(self):
        result = interpret_digoxin_level(1.2, "heart_failure")
        assert result["status"] == "SUPRATHERAPEUTIC"  # >0.9 for HF

    def test_heart_failure_therapeutic(self):
        result = interpret_digoxin_level(0.7, "heart_failure")
        assert result["status"] == "THERAPEUTIC"

    def test_boundary_low(self):
        result = interpret_digoxin_level(0.5)
        assert result["status"] == "THERAPEUTIC"

    def test_boundary_high(self):
        result = interpret_digoxin_level(2.0)
        assert result["status"] == "THERAPEUTIC"

    def test_invalid_concentration(self):
        with pytest.raises(ValueError):
            interpret_digoxin_level(-1)


# ============================================================================
# Renal Dose Adjustment Tests
# ============================================================================

class TestRenalDoseAdjustment:
    def test_normal_function(self):
        result = renal_dose_adjustment(250, 120)
        assert result["renal_classification"] == "NORMAL"
        assert result["dose_reduction_percent"] < 5  # Minimal reduction

    def test_mild_impairment(self):
        result = renal_dose_adjustment(250, 70)
        assert result["renal_classification"] == "MILD_IMPAIRMENT"
        assert result["adjusted_dose_mcg"] < 250

    def test_moderate_impairment(self):
        result = renal_dose_adjustment(250, 40)
        assert result["renal_classification"] == "MODERATE_IMPAIRMENT"
        assert result["adjusted_dose_mcg"] < 250

    def test_severe_impairment(self):
        result = renal_dose_adjustment(250, 15)
        assert result["renal_classification"] == "SEVERE_IMPAIRMENT"
        assert result["adjusted_dose_mcg"] < 250

    def test_invalid_dose(self):
        with pytest.raises(ValueError):
            renal_dose_adjustment(0, 80)


# ============================================================================
# Full Assessment Tests
# ============================================================================

class TestFullAssessment:
    def test_basic_assessment(self):
        result = full_digoxin_assessment(
            weight_kg=70, age_years=70, serum_creatinine_mg_dl=1.4,
            is_female=False, current_dose_mcg=250
        )
        assert "patient_parameters" in result
        assert "pk_parameters" in result
        assert "predicted_levels" in result
        assert result["pk_parameters"]["vd_liters"] > 0

    def test_assessment_with_level(self):
        result = full_digoxin_assessment(
            weight_kg=70, age_years=70, serum_creatinine_mg_dl=1.4,
            is_female=False, current_dose_mcg=250, measured_level_ng_ml=1.5
        )
        assert result["measured_level_interpretation"] is not None

    def test_assessment_with_heart_failure(self):
        result = full_digoxin_assessment(
            weight_kg=70, age_years=70, serum_creatinine_mg_dl=1.4,
            is_female=False, current_dose_mcg=250, heart_failure=True
        )
        assert result["patient_parameters"]["heart_failure"] is True

    def test_assessment_with_interactions(self):
        result = full_digoxin_assessment(
            weight_kg=70, age_years=70, serum_creatinine_mg_dl=1.4,
            is_female=False, current_dose_mcg=250,
            interacting_drugs=["amiodarone"]
        )
        assert result["drug_interactions"] is not None

    def test_disclaimer_present(self):
        result = full_digoxin_assessment(
            weight_kg=70, age_years=70, serum_creatinine_mg_dl=1.4,
            is_female=False, current_dose_mcg=250
        )
        assert "disclaimer" in result


# ============================================================================
# CLI Tests
# ============================================================================

class TestCLI:
    def test_level_command(self):
        ret = main(["level", "--concentration", "1.2"])
        assert ret == 0

    def test_dose_command(self):
        ret = main(["dose", "--target", "1.0", "--crcl", "80"])
        assert ret == 0

    def test_crcl_command(self):
        ret = main(["crcl", "--weight", "70", "--age", "70", "--scr", "1.4"])
        assert ret == 0

    def test_interactions_command(self):
        ret = main(["interactions", "--dose", "250", "--drugs", "amiodarone"])
        assert ret == 0

    def test_assess_command(self):
        ret = main(["assess", "--weight", "70", "--age", "70", "--scr", "1.4", "--dose", "250"])
        assert ret == 0
