"""
Core Definitions for the Diet Optimization System.

This module contains the fundamental definitions used throughout the system:
- FoodItem: the data structure representing a food item
- TAGS: the food categorization system
- SLOTS: the meals of the day
- DAYS_NAMES: the days of the week

These definitions are the "common language" of the system and are imported
by virtually all other modules.
"""

from dataclasses import dataclass, field
from typing import List, Dict


# =============================================================================
# FOOD ITEM DATA STRUCTURE
# =============================================================================

@dataclass(frozen=True)
class FoodItem:
    """
    Represents a single food item in the database.

    Immutable (frozen=True) to ensure nutritional data cannot be accidentally
    modified during optimization.

    Attributes:
        id: Unique food item identifier (integer)
        name: Human-readable food name (e.g. "Chicken Breast")
        kcal_100g: Calories per 100 grams
        prot_100g: Protein in grams per 100 grams
        carb_100g: Carbohydrates in grams per 100 grams
        fat_100g: Fat in grams per 100 grams
        portion_min: Minimum portion in grams (when selected)
        portion_max: Maximum portion in grams
        tags: List of tags categorizing the food item
        price: Price per 100 grams in euros

    Example:
        >>> chicken = FoodItem(
        ...     id=1,
        ...     name="Chicken Breast",
        ...     kcal_100g=165,
        ...     prot_100g=31,
        ...     carb_100g=0,
        ...     fat_100g=3.6,
        ...     portion_min=100,
        ...     portion_max=200,
        ...     tags=["carne", "carne_pra", "carne_cen"],
        ...     price=1.50
        ... )
        >>> chicken.has_tag("carne")
        True
    """
    id: int
    name: str
    kcal_100g: float
    prot_100g: float
    carb_100g: float
    fat_100g: float
    portion_min: float
    portion_max: float
    tags: List[str] = field(default_factory=list)
    price: float = 0.0

    def has_tag(self, tag: str) -> bool:
        """
        Checks whether the food item has a given tag.

        Args:
            tag: The tag to look for

        Returns:
            True if the food has the tag, False otherwise
        """
        return tag in self.tags


# =============================================================================
# FOOD CATEGORIZATION SYSTEM (TAGS)
# =============================================================================

# The TAGS system organizes foods into categories and subcategories.
# Each food item can have multiple tags that define:
# 1. Its nutritional category (proteins, carbohydrates, fats, others)
# 2. Which meals it can be consumed at (breakfast, lunch, snack, dinner)
#
# STRUCTURE:
# TAGS[CATEGORY][SUBCATEGORY][KEY]
#
# Where KEY can be:
# - "ROOT": general tag for the subcategory (e.g. "carne")
# - "COL": slot-specific tag for breakfast (e.g. "carne_col")
# - "PRA": slot-specific tag for lunch (e.g. "carne_pra")
# - "SNA": slot-specific tag for snack (e.g. "carne_sna")
# - "CEN": slot-specific tag for dinner (e.g. "carne_cen")
#
# USAGE EXAMPLE:
# - A food with tag "carne" is a protein source of the meat type
# - A food with tag "carne_pra" is allowed at lunch
# - A food with both tags can be selected by the solver for lunch
#
# SPECIAL NOTE - JOLLY:
# The tag "alimento_jolly" identifies foods that can be used
# freely without frequency restrictions (e.g. oil, salt, spices).

TAGS: Dict = {
    # -------------------------------------------------------------------------
    # PROTEINS: main protein sources
    # -------------------------------------------------------------------------
    "PROTEINE": {
        # Meat (chicken, beef, pork, turkey, etc.)
        "CARNE": {
            "ROOT": "carne",           # General tag "is a meat"
            "COL": "carne_col",        # Allowed at breakfast (rare)
            "PRA": "carne_pra",        # Allowed at lunch
            "SNA": "carne_sna",        # Allowed as snack (rare)
            "CEN": "carne_cen"         # Allowed at dinner
        },
        # Fish and seafood
        "PESCE": {
            "ROOT": "pesce",
            "COL": "pesce_col",
            "PRA": "pesce_pra",
            "SNA": "pesce_sna",
            "CEN": "pesce_cen"
        },
        # Legumes (beans, lentils, chickpeas, etc.)
        "LEGUMI": {
            "ROOT": "legumi",
            "COL": "legumi_col",
            "PRA": "legumi_pra",
            "SNA": "legumi_sna",
            "CEN": "legumi_cen"
        },
        # Eggs in all forms
        "UOVA": {
            "ROOT": "uova",
            "COL": "uova_col",
            "PRA": "uova_pra",
            "SNA": "uova_sna",
            "CEN": "uova_cen"
        },
        # Sweet dairy (yogurt, milk, sweet ricotta)
        "LATTICINI_DOLCI": {
            "ROOT": "latte_dolce",
            "COL": "latte_dolce_col",
            "PRA": "latte_dolce_pra",
            "SNA": "latte_dolce_sna",
            "CEN": "latte_dolce_cen"
        },
        # Savory dairy (cheeses, mozzarella, salted ricotta)
        "LATTICINI_SALATI": {
            "ROOT": "latte_salato",
            "COL": "latte_salato_col",
            "PRA": "latte_salato_pra",
            "SNA": "latte_salato_sna",
            "CEN": "latte_salato_cen"
        }
    },

    # -------------------------------------------------------------------------
    # CARBOHYDRATES: complex carbohydrate sources
    # -------------------------------------------------------------------------
    "CARBO": {
        # Savory carbs (pasta, rice, bread, potatoes)
        "COMPLESSI_SALATI": {
            "ROOT": "carbo_salati",
            "COL": "carbo_salati_col",
            "PRA": "carbo_salati_pra",
            "SNA": "carbo_salati_sna",
            "CEN": "carbo_salati_cen"
        },
        # Sweet breakfast carbs (cereals, rusk crackers, muesli)
        "DOLCI_COLAZIONE": {
            "ROOT": "carbo_dolci",
            "COL": "carbo_dolci_col",
            "PRA": "carbo_dolci_pra",
            "SNA": "carbo_dolci_sna",
            "CEN": "carbo_dolci_cen"
        }
    },

    # -------------------------------------------------------------------------
    # FATS: healthy fat sources
    # -------------------------------------------------------------------------
    "GRASSI": {
        # Pure fats (olive oil, nuts, avocado)
        "PURI": {
            "ROOT": "grassi",
            "COL": "grassi_col",
            "PRA": "grassi_pra",
            "SNA": "grassi_sna",
            "CEN": "grassi_cen"
        }
    },

    # -------------------------------------------------------------------------
    # OTHERS: complementary foods
    # -------------------------------------------------------------------------
    "ALTRI": {
        # Vegetables of all kinds
        "VERDURE": {
            "ROOT": "verdure",
            "COL": "verdure_col",
            "PRA": "verdure_pra",
            "SNA": "verdure_sna",
            "CEN": "verdure_cen"
        },
        # Fresh and dried fruit
        "FRUTTA": {
            "ROOT": "frutta",
            "COL": "frutta_col",
            "PRA": "frutta_pra",
            "SNA": "frutta_sna",
            "CEN": "frutta_cen"
        }
    },

    # -------------------------------------------------------------------------
    # TECHNICAL: special tags controlling system behavior
    # -------------------------------------------------------------------------
    "TECNICI": {
        # "Jolly" foods that can appear without frequency limits
        # Examples: olive oil, salt, spices, herbs
        # These foods are excluded from anti-repetition constraints
        "JOLLY": "alimento_jolly"
    }
}


# =============================================================================
# DIET TEMPORAL STRUCTURE
# =============================================================================

# Meals of the day in chronological order
SLOTS: List[str] = [
    "Breakfast",
    "Lunch",
    "Snack",
    "Dinner",
]

DAYS_NAMES: List[str] = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# =============================================================================
# DATA STRUCTURE TEMPLATES
# =============================================================================

# Template for a single day structure
# Format: {slot: [list of foods]}
DAY_STRUCTURE_TEMPLATE: Dict[str, List] = {
    slot: [] for slot in SLOTS
}

# Template for a full week structure
# Format: {day: {slot: [list of foods]}}
WEEK_STRUCTURE_TEMPLATE: Dict[str, Dict[str, List]] = {
    day: {slot: [] for slot in SLOTS}
    for day in DAYS_NAMES
}
