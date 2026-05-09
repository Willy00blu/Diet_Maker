"""
Package config - Centralized system configuration.

Structure:
- nutrition.py: nutritional targets (kcal, macros, delta)
- axioms.py: axiom configuration
- objectives.py: objective functions and solver

Backwards compatibility: all symbols are re-exported here.
"""

# Nutrition config
from backend.config.nutrition import (
    N_DAYS,
    TARGET_KCAL,
    PCT_PROT, PCT_CARB, PCT_FAT,
    DELTA_KCAL, DELTA_MACRO,
    TARGET_PROT, TARGET_CARB, TARGET_FAT,
)

# Axioms config
from backend.config.axioms import (
    NUTRITION_AXIOMS,
    DAILY_FREQUENCY_AXIOMS,
    DIET_FREQUENCY_AXIOMS,
    MEAL_VALIDITY_AXIOMS,
    SPORT_NUTRITION_AXIOMS,
    AXIOMS_CONFIG,
)

# Objectives config
from backend.config.objectives import (
    OBJECTIVES_CONFIG,
    SOLVER_CONFIG,
)

# Food config
from backend.config.food import FOODS_CONFIG
