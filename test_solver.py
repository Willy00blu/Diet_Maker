"""
Comprehensive Solver Test Script.

Run from the project root:
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 test_solver.py

Exposes all parameters available in the GUI so any configuration can be tested.
Each scenario defines overrides on top of defaults; unspecified values fall back
to the system defaults (same as launching the app with no changes).

SCENARIO STRUCTURE
------------------
{
    "name": str,                  # short identifier
    "description": str,           # what is being tested
    "expected": "pass"|"fail",    # expected solver outcome
    "classification": str,        # "ok" | "sensible_fail" | "design_bug"
    "note": str,                  # optional explanation

    # --- Nutrition (all optional) ---
    "n_days":     int,   # 1-7, default 5
    "kcal":       int,   # daily kcal target, default 2000
    "prot_pct":   int,   # protein %, default 20
    "carb_pct":   int,   # carbohydrate %, default 55
    "fat_pct":    int,   # fat %, default 25
    "delta_kcal": int,   # calorie tolerance %, default 10
    "delta_macro": int,  # macro tolerance %, default 50

    # --- Objective ---
    "objective": "none"|"cost"|"preference",   # default "none"

    # --- Axiom overrides (all optional) ---
    # Only specified entries are overridden. Format:
    #   "axioms": {
    #       "meal_validity": {
    #           "breakfast": {"enabled": False},
    #           "lunch":     {"params": {"proteine": {"exact": 2}}},
    #       },
    #       "daily_frequency": {
    #           "daily_vegetables": {"enabled": True, "params": {"min": 2, "max": 3}},
    #       },
    #       "diet_frequency": {
    #           "diet_meat":    {"params": {"min": 1, "max": 3}},
    #           "diet_fish":    {"params": {"min": 1, "max": 3}},
    #           "diet_legumes": {"params": {"min": 1, "max": 3}},
    #           "diet_variety": {"params": {"max_normal": 4, "max_jolly": 14}},
    #           "meal_prep":    {"params": {"min_if_used": 2, "max_total": 14}},
    #       },
    #       "sport_nutrition": {
    #           "chrono_carb":    {"enabled": False},
    #           "chrono_protein": {"enabled": False},
    #           "chrono_fat":     {"enabled": False},
    #       },
    #   }

    # --- Per-food overrides (all optional) ---
    # Keyed by food name (string). Use food names exactly as in food_db.csv.
    # "foods": {
    #     "Chicken breast": {"enabled": False},
    #     "Oats":           {"portion_min": 30, "portion_max": 80},
    #     "Salmon":         {"enabled": True, "portion_min": 100, "portion_max": 200},
    # }
}
"""

import sys
import os
import copy
import time
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Python path setup — must be run from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import DietService, DietRequest, DietResponse, NutritionTargets, AxiomConfig
from pipeline.contracts import FoodSelection
from backend.config.axioms import (
    MEAL_VALIDITY_AXIOMS,
    DAILY_FREQUENCY_AXIOMS,
    DIET_FREQUENCY_AXIOMS,
    SPORT_NUTRITION_AXIOMS,
)
from backend.config.nutrition import N_DAYS, TARGET_KCAL, PCT_PROT, PCT_CARB, PCT_FAT, DELTA_KCAL, DELTA_MACRO
from backend.config.food import FOODS_CONFIG


# =============================================================================
# DEFAULT VALUES (mirror what the GUI shows on first load)
# =============================================================================

DEFAULTS = {
    "n_days":     N_DAYS,
    "kcal":       TARGET_KCAL,
    "prot_pct":   int(PCT_PROT * 100),
    "carb_pct":   int(PCT_CARB * 100),
    "fat_pct":    int(PCT_FAT * 100),
    "delta_kcal": int(DELTA_KCAL * 100),
    "delta_macro": int(DELTA_MACRO * 100),
    "objective":  "none",
}


# =============================================================================
# TEST SCENARIOS
# =============================================================================

SCENARIOS: List[Dict[str, Any]] = [

    # -------------------------------------------------------------------------
    # BASELINE
    # -------------------------------------------------------------------------
    {
        "name": "baseline",
        "description": "Default configuration — no overrides",
        "expected": "pass",
        "classification": "ok",
    },

    # -------------------------------------------------------------------------
    # OBJECTIVE VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "objective_cost",
        "description": "Minimize cost objective",
        "expected": "pass",
        "classification": "ok",
        "objective": "cost",
    },
    {
        "name": "objective_preference",
        "description": "Maximize preference (star ratings) objective",
        "expected": "pass",
        "classification": "ok",
        "objective": "preference",
    },

    # -------------------------------------------------------------------------
    # DURATION VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "1_day",
        "description": "Single day diet (default diet_frequency still requires meat/fish/legumes ≥2)",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "With 1 day and protein slots = 2 (lunch+dinner), meat≥2 + fish≥2 + legumes≥2 is impossible.",
        "n_days": 1,
    },
    {
        "name": "1_day_relaxed_diet_freq",
        "description": "Single day with diet_frequency mins set to 1 each",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": (
            "Even with min=1 per category, you still need meat in 1 slot + fish in 1 slot + legumes in 1 slot. "
            "Breakfast proteins are tagged _col (latte/uova) and cannot satisfy meat/fish/legumes requirements. "
            "With 1 day, only lunch+dinner = 2 slots accept carne/pesce/legumi → 3 required but 2 available."
        ),
        "n_days": 1,
        "axioms": {
            "diet_frequency": {
                "diet_meat":    {"params": {"min": 1, "max": 4}},
                "diet_fish":    {"params": {"min": 1, "max": 4}},
                "diet_legumes": {"params": {"min": 1, "max": 5}},
            }
        },
    },
    {
        "name": "1_day_no_diet_freq",
        "description": "Single day with all diet_frequency axioms disabled",
        "expected": "pass",
        "classification": "ok",
        "n_days": 1,
        "axioms": {
            "diet_frequency": {
                "diet_meat":    {"enabled": False},
                "diet_fish":    {"enabled": False},
                "diet_legumes": {"enabled": False},
                "diet_variety": {"enabled": False},
                "meal_prep":    {"enabled": False},
            }
        },
    },
    {
        "name": "7_days",
        "description": "Full 7-day diet with default axioms",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": (
            "Default diet_variety max_normal=3 was calibrated for 5 days. "
            "7 days × 4 meals = 28 slots; with ~17 selectable proteins and max 3 appearances each, "
            "the variety constraint becomes too tight. Use 7_days_relaxed_variety instead."
        ),
        "n_days": 7,
    },
    {
        "name": "7_days_strict_variety",
        "description": "7 days with diet_variety max_normal=3 (28 slots, ~17 foods → too little diversity)",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "7 days × 4 meals × variety=3 pushes solver to near-infeasibility with limited protein pool.",
        "n_days": 7,
        "axioms": {
            "diet_frequency": {
                "diet_variety": {"params": {"max_normal": 3, "max_jolly": 14}},
            }
        },
    },
    {
        "name": "7_days_relaxed_variety",
        "description": "7 days with diet_variety max_normal=4",
        "expected": "pass",
        "classification": "ok",
        "n_days": 7,
        "axioms": {
            "diet_frequency": {
                "diet_variety": {"params": {"max_normal": 4, "max_jolly": 14}},
            }
        },
    },

    # -------------------------------------------------------------------------
    # NUTRITION VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "high_kcal",
        "description": "High calorie target (2800 kcal) with default 10% macro tolerance",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "At 2800 kcal, 10% macro tolerance is too tight for available foods.",
        "kcal": 2800,
        "delta_macro": 10,
    },
    {
        "name": "high_kcal_relaxed_macro",
        "description": "High calorie target (2800 kcal) with 30% macro tolerance",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": (
            "With the current food database, the effective kcal ceiling is ~2500 kcal when diet_frequency "
            "constraints are active. At 2800 kcal, portions must be larger, but variety constraints "
            "(max_normal=3 per food) prevent reusing enough foods to reach the caloric target. "
            "Disabling diet_frequency makes it pass. Max viable kcal with defaults ≈ 2500."
        ),
        "kcal": 2800,
        "delta_macro": 30,
    },
    {
        "name": "zero_delta_macro",
        "description": "Zero macro tolerance (mathematically impossible)",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "No combination of real foods can hit exact macro percentages.",
        "delta_macro": 0,
    },
    {
        "name": "zero_delta_kcal",
        "description": "Zero calorie tolerance (exact kcal target)",
        "expected": "pass",
        "classification": "ok",
        "note": (
            "Portion quantities are continuous variables (not discrete), so the solver CAN find "
            "an exact kcal match. A 0% calorie tolerance is strict but not infeasible."
        ),
        "delta_kcal": 0,
    },
    {
        "name": "wide_tolerances",
        "description": "Very wide tolerances (delta_kcal=30%, delta_macro=80%)",
        "expected": "pass",
        "classification": "ok",
        "delta_kcal": 30,
        "delta_macro": 80,
    },
    {
        "name": "low_kcal",
        "description": "Low calorie target (1500 kcal)",
        "expected": "pass",
        "classification": "ok",
        "kcal": 1500,
        "delta_macro": 30,
    },

    # -------------------------------------------------------------------------
    # MEAL VALIDITY VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "breakfast_disabled",
        "description": "Breakfast meal_validity disabled → slot forced empty, targets scaled accordingly",
        "expected": "pass",
        "classification": "ok",
        "note": (
            "Disabling breakfast forces the slot empty. Nutrition targets are scaled by the active "
            "fraction (~80%), meal_distribution skips breakfast, chrono_protein/fat skip breakfast. "
            "Fix: _get_active_kcal_fraction + _is_slot_disabled propagated to all constraint modules."
        ),
        "axioms": {
            "meal_validity": {"breakfast": {"enabled": False}},
        },
    },
    {
        "name": "snack_disabled",
        "description": "Snack meal_validity disabled → slot forced empty, targets scaled accordingly",
        "expected": "pass",
        "classification": "ok",
        "note": "Snack contributes ~7.5% of kcal. Active fraction ≈ 0.925. Remaining slots can cover.",
        "axioms": {
            "meal_validity": {"snack": {"enabled": False}},
        },
    },
    {
        "name": "breakfast_and_snack_disabled",
        "description": "Both breakfast and snack disabled → only lunch and dinner active",
        "expected": "pass",
        "classification": "ok",
        "note": "Active fraction ≈ 0.725. Lunch+dinner carry all nutrition. No composition rules conflict.",
        "axioms": {
            "meal_validity": {
                "breakfast": {"enabled": False},
                "snack":     {"enabled": False},
            },
        },
    },

    # -------------------------------------------------------------------------
    # DAILY FREQUENCY VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "vegetables_min3",
        "description": "Require ≥3 vegetables per day (max 2 slots allow vegs)",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "Only lunch and dinner include verdure slots; max achievable = 2/day.",
        "axioms": {
            "daily_frequency": {
                "daily_vegetables": {"params": {"min": 3, "max": 4}},
            }
        },
    },
    {
        "name": "no_daily_frequency",
        "description": "All daily_frequency axioms disabled",
        "expected": "pass",
        "classification": "ok",
        "axioms": {
            "daily_frequency": {
                "daily_vegetables": {"enabled": False},
                "daily_fruit":      {"enabled": False},
                "daily_variety":    {"enabled": False},
            }
        },
    },

    # -------------------------------------------------------------------------
    # DIET FREQUENCY CONTRADICTIONS
    # -------------------------------------------------------------------------
    {
        "name": "meal_prep_contradiction",
        "description": "meal_prep min_if_used=4 but diet_variety max_normal=3 → direct contradiction",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "meal_prep requires each used food appear ≥4 times, but variety caps it at 3.",
        "axioms": {
            "diet_frequency": {
                "diet_variety": {"params": {"max_normal": 3, "max_jolly": 14}},
                "meal_prep":    {"params": {"min_if_used": 4, "max_total": 14}},
            }
        },
    },
    {
        "name": "high_protein_requirements",
        "description": "Meat ≥4, Fish ≥4, Legumes ≥4 over 5 days",
        "expected": "pass",
        "classification": "ok",
        "note": (
            "12 required protein-source meals over 5 days. Breakfast also has 1 protein slot "
            "(uova/latte), plus snack can also include protein. Total protein slots per day ≈ 3-4. "
            "5 days × 3 = 15 protein slots > 12 needed. Feasible."
        ),
        "axioms": {
            "diet_frequency": {
                "diet_meat":    {"params": {"min": 4, "max": 7}},
                "diet_fish":    {"params": {"min": 4, "max": 7}},
                "diet_legumes": {"params": {"min": 4, "max": 7}},
            }
        },
    },

    # -------------------------------------------------------------------------
    # SPORT NUTRITION VARIATIONS
    # -------------------------------------------------------------------------
    {
        "name": "no_sport_nutrition",
        "description": "All chrono-nutrition axioms disabled",
        "expected": "pass",
        "classification": "ok",
        "axioms": {
            "sport_nutrition": {
                "chrono_carb":    {"enabled": False},
                "chrono_protein": {"enabled": False},
                "chrono_fat":     {"enabled": False},
            }
        },
    },
    {
        "name": "strict_chrono_carb",
        "description": "Very strict carb timing: lunch ≥50%, dinner ≤15%",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "Combined with meal distribution constraints, this extreme timing is hard to satisfy.",
        "axioms": {
            "sport_nutrition": {
                "chrono_carb": {"params": {"lunch_min_pct": 0.50, "dinner_max_pct": 0.15, "delta": 0.02}},
            }
        },
    },

    # -------------------------------------------------------------------------
    # COMBINED RELAXATION
    # -------------------------------------------------------------------------
    {
        "name": "fully_relaxed",
        "description": "All optional axioms disabled — only basic nutrition constraints active",
        "expected": "pass",
        "classification": "ok",
        "axioms": {
            "daily_frequency": {
                "daily_vegetables": {"enabled": False},
                "daily_fruit":      {"enabled": False},
                "daily_variety":    {"enabled": False},
            },
            "diet_frequency": {
                "diet_meat":    {"enabled": False},
                "diet_fish":    {"enabled": False},
                "diet_legumes": {"enabled": False},
                "diet_variety": {"enabled": False},
                "meal_prep":    {"enabled": False},
            },
            "sport_nutrition": {
                "chrono_carb":    {"enabled": False},
                "chrono_protein": {"enabled": False},
                "chrono_fat":     {"enabled": False},
            },
        },
    },

    # -------------------------------------------------------------------------
    # BUG-REGRESSION TESTS
    # -------------------------------------------------------------------------
    {
        "name": "cost_objective_1day",
        "description": "cost objective with n_days=1 (was KeyError crash)",
        "expected": "pass",
        "classification": "ok",
        "note": "Bug: _set_optimization_objective did not pass number_of_days → KeyError on day 2+ variables.",
        "n_days": 1,
        "objective": "cost",
        "axioms": {
            "diet_frequency": {
                "diet_meat":    {"enabled": False},
                "diet_fish":    {"enabled": False},
                "diet_legumes": {"enabled": False},
                "diet_variety": {"enabled": False},
                "meal_prep":    {"enabled": False},
            }
        },
    },
    {
        "name": "preference_objective_3days",
        "description": "preference objective with n_days=3 (was KeyError crash)",
        "expected": "pass",
        "classification": "ok",
        "note": "Same KeyError bug as cost objective. Fixed by threading number_of_days through.",
        "n_days": 3,
        "objective": "preference",
        "axioms": {
            "diet_frequency": {
                "diet_variety": {"params": {"max_normal": 4, "max_jolly": 14}},
            }
        },
    },
    {
        "name": "lunch_disabled",
        "description": "Lunch disabled → targets scaled, chrono_carb lunch min skipped",
        "expected": "pass",
        "classification": "ok",
        "note": "Bug: chrono_carb required carbs at lunch even when lunch was forced empty.",
        "axioms": {
            "meal_validity": {"lunch": {"enabled": False}},
        },
    },
    {
        "name": "dinner_disabled",
        "description": "Dinner disabled → targets scaled, daily vegetables min still satisfiable from lunch",
        "expected": "pass",
        "classification": "ok",
        "axioms": {
            "meal_validity": {"dinner": {"enabled": False}},
        },
    },
    {
        "name": "lunch_and_dinner_disabled",
        "description": "Both lunch and dinner disabled → legumes structurally impossible",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": (
            "No selectable legumi_col foods exist in the DB (legumes are only for lunch/dinner). "
            "The only legumi_sna foods (Edamame, Chickpea Hummus) are marked selectable=False. "
            "With lunch+dinner disabled, diet_legumes min=2 can never be satisfied. "
            "The vegetable min bug IS fixed (that constraint is correctly skipped); "
            "but diet_frequency legumes requirement remains infeasible."
        ),
        "axioms": {
            "meal_validity": {
                "lunch":  {"enabled": False},
                "dinner": {"enabled": False},
            },
        },
    },
    {
        "name": "lunch_and_dinner_disabled_no_legumes",
        "description": "Both lunch and dinner disabled + diet_legumes disabled",
        "expected": "pass",
        "classification": "ok",
        "note": "Vegetable min is correctly skipped. Nutrition scaled to breakfast+snack (~27.5% of target).",
        "axioms": {
            "meal_validity": {
                "lunch":  {"enabled": False},
                "dinner": {"enabled": False},
            },
            "diet_frequency": {
                "diet_legumes": {"enabled": False},
            },
        },
    },
    {
        "name": "fruit_min_enforced",
        "description": "daily_fruit min=1 should require at least 1 fruit per day",
        "expected": "pass",
        "classification": "ok",
        "note": "Bug: min parameter was silently ignored. Now enforced. min=1 is achievable (breakfast/snack).",
        "axioms": {
            "daily_frequency": {
                "daily_fruit": {"params": {"min": 1, "max": 3}},
            }
        },
    },
    {
        "name": "fruit_min_impossible",
        "description": "daily_fruit min=4 — fruit only at breakfast+snack = max 2/day",
        "expected": "fail",
        "classification": "sensible_fail",
        "note": "With min now enforced: requiring 4 fruit/day is impossible (only 2 fruit-capable slots).",
        "axioms": {
            "daily_frequency": {
                "daily_fruit": {"params": {"min": 4, "max": 5}},
            }
        },
    },

    # -------------------------------------------------------------------------
    # ADD YOUR OWN SCENARIOS BELOW
    # e.g.:
    # {
    #     "name": "custom_test",
    #     "description": "...",
    #     "expected": "pass",
    #     "classification": "ok",
    #     "n_days": 3,
    #     "kcal": 2000,
    #     "delta_macro": 20,
    #     "axioms": {...},
    #     "foods": {"Chicken breast": {"enabled": False}},
    # },
    # -------------------------------------------------------------------------
]


# =============================================================================
# BUILDER: scenario dict -> DietRequest
# =============================================================================

def build_request(scenario: Dict[str, Any], all_foods) -> DietRequest:
    """Build a DietRequest from a scenario definition + loaded food data."""

    # --- Nutrition targets ---
    nutrition = NutritionTargets(
        n_days=     scenario.get("n_days",     DEFAULTS["n_days"]),
        kcal=       scenario.get("kcal",       DEFAULTS["kcal"]),
        prot_pct=   scenario.get("prot_pct",   DEFAULTS["prot_pct"]),
        carb_pct=   scenario.get("carb_pct",   DEFAULTS["carb_pct"]),
        fat_pct=    scenario.get("fat_pct",    DEFAULTS["fat_pct"]),
        delta_kcal= scenario.get("delta_kcal", DEFAULTS["delta_kcal"]),
        delta_macro=scenario.get("delta_macro",DEFAULTS["delta_macro"]),
    )

    # --- Food selections ---
    food_overrides: Dict[str, Any] = scenario.get("foods", {})
    food_selections: List[FoodSelection] = []
    preferences: Dict[str, int] = {}

    for food in all_foods:
        override = food_overrides.get(food.name, {})
        enabled = override.get("enabled", True)
        portion_min = override.get("portion_min", food.portion_min)
        portion_max = override.get("portion_max", food.portion_max)
        rating = override.get("rating", FOODS_CONFIG.get(str(food.id), {}).get("preference", 3))

        food_selections.append(FoodSelection(
            food_id=food.id,
            name=food.name,
            enabled=enabled,
            rating=rating,
            portion_min=portion_min,
            portion_max=portion_max,
        ))
        preferences[food.name] = rating

    # --- Axiom config ---
    axioms_config = _build_axioms_config(scenario.get("axioms", {}))

    return DietRequest(
        food_selections=food_selections,
        preferences=preferences,
        nutrition_targets=nutrition,
        objective=scenario.get("objective", DEFAULTS["objective"]),
        axioms_config=axioms_config,
    )


def _build_axioms_config(
    overrides: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, AxiomConfig]]:
    """
    Merge scenario axiom overrides onto the default config.

    The default config is taken from the AXIOMS_CONFIG constants.
    Only the specified groups/axioms are overridden.
    """
    # Build full defaults from the config constants
    defaults_by_group = {
        "meal_validity":   MEAL_VALIDITY_AXIOMS,
        "daily_frequency": DAILY_FREQUENCY_AXIOMS,
        "diet_frequency":  DIET_FREQUENCY_AXIOMS,
        "sport_nutrition": SPORT_NUTRITION_AXIOMS,
    }

    result: Dict[str, Dict[str, AxiomConfig]] = {}

    for group_key, group_defaults in defaults_by_group.items():
        result[group_key] = {}
        group_overrides = overrides.get(group_key, {})

        for axiom_key, axiom_default in group_defaults.items():
            axiom_override = group_overrides.get(axiom_key, {})

            # enabled: override takes priority, else use default
            enabled = axiom_override.get("enabled", axiom_default.get("enabled", True))

            # params: deep-merge (override values win, rest from default)
            default_params = copy.deepcopy(axiom_default.get("params", {}))
            override_params = axiom_override.get("params", {})
            merged_params = {**default_params, **override_params}

            result[group_key][axiom_key] = AxiomConfig(
                enabled=enabled,
                params=merged_params,
            )

    return result


# =============================================================================
# RUNNER
# =============================================================================

def run_scenario(
    scenario: Dict[str, Any],
    service: DietService,
    all_foods,
    verbose: bool = False,
) -> Tuple[bool, float, DietResponse]:
    """Run a single scenario and return (actual_passed, elapsed_seconds, response)."""
    request = build_request(scenario, all_foods)
    t0 = time.time()
    response = service.generate(request)
    elapsed = time.time() - t0
    return response.success, elapsed, response


def print_plan_summary(plan: Dict) -> None:
    """Print a compact summary of the generated diet plan."""
    for day, slots in plan.items():
        items_all = []
        for slot, items in slots.items():
            for name, grams in items:
                items_all.append(f"{name}({grams}g)")
        print(f"    {day}: {', '.join(items_all) if items_all else '(empty)'}")


# =============================================================================
# MAIN
# =============================================================================

def main(verbose: bool = False, run_only: Optional[List[str]] = None) -> None:
    """
    Run all scenarios and print a classified summary report.

    Args:
        verbose: If True, print the full diet plan for passing scenarios
        run_only: If provided, only run scenarios whose name is in this list
    """
    print("=" * 70)
    print("  DIET SOLVER — COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # Load food database once
    service = DietService()
    all_foods = service.load_foods(include_non_selectable=False)
    print(f"  Foods loaded: {len(all_foods)}")
    print()

    scenarios_to_run = [
        s for s in SCENARIOS
        if run_only is None or s["name"] in run_only
    ]

    results = []

    for scenario in scenarios_to_run:
        name = scenario["name"]
        description = scenario["description"]
        expected = scenario["expected"]
        classification = scenario["classification"]
        note = scenario.get("note", "")

        print(f"[{name}]")
        print(f"  {description}")

        actual_passed, elapsed, response = run_scenario(
            scenario, service, all_foods, verbose
        )

        actual = "pass" if actual_passed else "fail"
        matched = (actual == expected)

        status_icon = "OK  " if matched else "WARN"
        result_tag  = f"[{status_icon}]"

        print(f"  {result_tag}  result={actual.upper():4s}  expected={expected.upper():4s}  "
              f"class={classification:<15s}  ({elapsed:.1f}s)")

        if not actual_passed and response.error_message:
            # Show first line of error only (keep output compact)
            first_line = response.error_message.split("\n")[0]
            print(f"  error : {first_line}")

        if note:
            print(f"  note  : {note[:100]}{'...' if len(note) > 100 else ''}")

        if verbose and actual_passed and response.plan:
            print_plan_summary(response.plan)

        # Flag unexpected outcomes clearly
        if not matched:
            if actual == "pass" and expected == "fail":
                print("  *** UNEXPECTED PASS — constraint may be missing or inactive ***")
            elif actual == "fail" and expected == "pass":
                print("  *** UNEXPECTED FAIL — check configuration or food database ***")

        print()
        results.append({
            "name": name,
            "expected": expected,
            "actual": actual,
            "matched": matched,
            "classification": classification,
            "elapsed": elapsed,
        })

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    total       = len(results)
    matched     = sum(1 for r in results if r["matched"])
    unexpected  = total - matched

    passes      = sum(1 for r in results if r["actual"] == "pass")
    fails       = sum(1 for r in results if r["actual"] == "fail")

    print(f"  Total scenarios : {total}")
    print(f"  Passed (solver) : {passes}")
    print(f"  Failed (solver) : {fails}")
    print(f"  As expected     : {matched}/{total}")
    if unexpected:
        print(f"  UNEXPECTED      : {unexpected}")

    print()
    print("  Classification breakdown:")
    for cls in ["ok", "sensible_fail", "design_bug"]:
        count = sum(1 for r in results if r["classification"] == cls)
        if count:
            items = [r["name"] for r in results if r["classification"] == cls]
            print(f"    {cls:<18s}: {count}  ({', '.join(items)})")

    if unexpected:
        print()
        print("  Unexpected results:")
        for r in results:
            if not r["matched"]:
                print(f"    {r['name']:<35s} expected={r['expected']} actual={r['actual']}")

    total_time = sum(r["elapsed"] for r in results)
    print()
    print(f"  Total time: {total_time:.1f}s")
    print("=" * 70)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run solver test scenarios. All parameters are configurable in SCENARIOS."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full diet plan for each passing scenario"
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="SCENARIO_NAME",
        help="Run only the specified scenario(s) by name"
    )
    args = parser.parse_args()

    main(verbose=args.verbose, run_only=args.only)
