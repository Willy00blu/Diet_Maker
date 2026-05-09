"""
Axiom configuration.
Each axiom can be enabled/disabled and has editable parameters.
"""

# ==========================================
# NUTRITION AXIOMS (nutrition.py)
# ==========================================
NUTRITION_AXIOMS = {
    "daily_nutrition": {
        "enabled": True,
        "icon": "⚡",
        "label": "Kcal / Macro Targets",
        "description": "Daily constraints on calories and macronutrients",
        "params": {}
    },
    "meal_distribution": {
        "enabled": True,
        "icon": "📊",
        "label": "Meal Distribution",
        "description": "Caloric distribution across meals",
        "params": {
            "breakfast": {"min_pct": 0.15, "max_pct": 0.25},
            "lunch":     {"min_pct": 0.35, "max_pct": 0.40},
            "snack":     {"min_pct": 0.05, "max_pct": 0.10},
            "dinner":    {"min_pct": 0.30, "max_pct": 0.35},
        }
    },
}

# ==========================================
# DAILY FREQUENCY AXIOMS (daily_frequency.py)
# ==========================================
DAILY_FREQUENCY_AXIOMS = {
    "daily_vegetables": {
        "enabled": True,
        "icon": "🥬",
        "label": "Daily Vegetables",
        "description": "Daily vegetable servings",
        "params": {
            "min": 1,
            "max": 2,
        }
    },
    "daily_fruit": {
        "enabled": True,
        "icon": "🍎",
        "label": "Daily Fruit",
        "description": "Daily fruit serving limit",
        "params": {
            "min": 0,
            "max": 1,
        }
    },
    "daily_variety": {
        "enabled": True,
        "icon": "🔄",
        "label": "Daily Variety",
        "description": "Anti-repetition: same food at most 1x per day",
        "params": {
            "max_per_food": 1,
        }
    },
}

# ==========================================
# DIET FREQUENCY AXIOMS (diet_frequency.py)
# Constraints over the full diet period (default 7 days)
# Adjust manually if N_DAYS changes
# ==========================================
DIET_FREQUENCY_AXIOMS = {
    "diet_meat": {
        "enabled": True,
        "icon": "🥩",
        "label": "Meat Limit",
        "description": "Meat frequency over the diet period",
        "params": {
            "min": 2,
            "max": 4,
        }
    },
    "diet_fish": {
        "enabled": True,
        "icon": "🐟",
        "label": "Fish Requirement",
        "description": "Minimum fish servings over the diet period",
        "params": {
            "min": 2,
            "max": 4,
        }
    },
    "diet_legumes": {
        "enabled": True,
        "icon": "🫘",
        "label": "Legume Centrality",
        "description": "Legume frequency over the diet period",
        "params": {
            "min": 2,
            "max": 5,
        }
    },
    "diet_variety": {
        "enabled": True,
        "icon": "🎲",
        "label": "Weekly Variety",
        "description": "Max times the same food appears across the diet",
        "params": {
            "max_normal": 3,
            "max_jolly": 14,
        }
    },
    "meal_prep": {
        "enabled": True,
        "icon": "📦",
        "label": "Meal Prep",
        "description": "Logistic feasibility: if used, at least N times",
        "params": {
            "min_if_used": 2,
            "max_total": 14,
        }
    },
}

# ==========================================
# MEAL VALIDITY AXIOMS (meal_validity.py)
# ==========================================
MEAL_VALIDITY_AXIOMS = {
    "breakfast": {
        "enabled": True,
        "icon": "🌅",
        "label": "Breakfast",
        "description": "Breakfast composition",
        "params": {
            "proteine": {"exact": 1},
            "carboidrati": {"exact": 1},
            "grassi": {"min": 0, "max": 1},
            "frutta": {"min": 0, "max": 1},
            "xor_dolce_salato": True,
        }
    },
    "lunch": {
        "enabled": True,
        "icon": "☀️",
        "label": "Lunch",
        "description": "Lunch composition",
        "params": {
            "proteine": {"exact": 1},
            "carboidrati": {"exact": 1},
            "verdure": {"exact": 1},
            "grassi": {"exact": 1},
            "frutta": {"min": 0, "max": 1},
        }
    },
    "snack": {
        "enabled": True,
        "icon": "🍪",
        "label": "Snack",
        "description": "Snack composition",
        "params": {
            "proteine": {"min": 0, "max": 1},
            "carboidrati": {"min": 0, "max": 1},
            "grassi": {"min": 0, "max": 1},
            "frutta": {"min": 0, "max": 1},
            "min_totale": 1,
            "xor_dolce_salato": True,
        }
    },
    "dinner": {
        "enabled": True,
        "icon": "🌙",
        "label": "Dinner",
        "description": "Dinner composition",
        "params": {
            "proteine": {"exact": 1},
            "carboidrati": {"exact": 1},
            "verdure": {"exact": 1},
            "grassi": {"exact": 1},
            "frutta": {"min": 0, "max": 1},
        }
    },
}

# ==========================================
# SPORT NUTRITION AXIOMS (nutrizione_sportiva.py)
# ==========================================
SPORT_NUTRITION_AXIOMS = {
    "chrono_carb": {
        "enabled": True,
        "icon": "🍝",
        "label": "Carb Timing",
        "description": "Chrono-nutrition: carbohydrate timing",
        "params": {
            "lunch_min_pct": 0.35,
            "dinner_max_pct": 0.25,
            "delta": 0.05,
        }
    },
    "chrono_protein": {
        "enabled": True,
        "icon": "🥚",
        "label": "Protein Timing",
        "description": "Chrono-nutrition: protein distribution",
        "params": {
            "min_pct_per_meal": 0.20,  # breakfast, lunch, dinner
            "delta": 0.05,
        }
    },
    "chrono_fat": {
        "enabled": True,
        "icon": "🥑",
        "label": "Fat Timing",
        "description": "Chrono-nutrition: fat distribution",
        "params": {
            "breakfast_min_pct": 0.15,
            "max_pct_per_meal": 0.35,
            "delta": 0.05,
        }
    },
}

# ==========================================
# AGGREGATED CONFIGURATION
# ==========================================
AXIOMS_CONFIG = {
    "daily_frequency": {
        "icon": "📅",
        "label": "Daily Frequency",
        "description": "Constraints on vegetables, fruit and variety",
        "axioms": DAILY_FREQUENCY_AXIOMS,
    },
    "diet_frequency": {
        "icon": "📆",
        "label": "Diet Frequency",
        "description": "Weekly constraints on meat, fish, legumes",
        "axioms": DIET_FREQUENCY_AXIOMS,
    },
    "meal_validity": {
        "icon": "🍽️",
        "label": "Meal Composition",
        "description": "Structure of each meal",
        "axioms": MEAL_VALIDITY_AXIOMS,
    },
    "sport_nutrition": {
        "icon": "💪",
        "label": "Sport Nutrition",
        "description": "Chrono-nutrition and nutrient timing",
        "axioms": SPORT_NUTRITION_AXIOMS,
    },
}
