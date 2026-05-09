"""
Global constants for the diet optimization system.

This file centralizes all "magic numbers" to make the code
more readable and maintainable. Each constant has a descriptive name
and a comment explaining its purpose.
"""

# =============================================================================
# NUTRITIONAL CONSTANTS
# =============================================================================

# Calories per gram of macronutrient (standard scientific values)
KCAL_PER_GRAM_PROTEIN = 4  # Protein provides 4 kcal per gram
KCAL_PER_GRAM_CARBOHYDRATE = 4  # Carbohydrates provide 4 kcal per gram
KCAL_PER_GRAM_FAT = 9  # Fat provides 9 kcal per gram


# =============================================================================
# VALIDATION LIMITS
# =============================================================================

# Valid range for diet duration (days)
MIN_DIET_DAYS = 1
MAX_DIET_DAYS = 7

# Valid range for daily calories (kcal)
MIN_DAILY_KCAL = 1000  # Below this threshold is dangerous for health
MAX_DAILY_KCAL = 5000  # Above this is unrealistic for most people

# Valid range for macronutrient percentages
MIN_PROTEIN_PERCENTAGE = 10  # Minimum recommended for health
MAX_PROTEIN_PERCENTAGE = 40  # Maximum for high-protein diets

MIN_CARBOHYDRATE_PERCENTAGE = 30  # Minimum for sufficient energy
MAX_CARBOHYDRATE_PERCENTAGE = 70  # Maximum for high-carbohydrate diets

MIN_FAT_PERCENTAGE = 15  # Minimum for fat-soluble vitamin absorption
MAX_FAT_PERCENTAGE = 40  # Maximum for high-fat diets

# Minimum number of enabled foods required to generate a valid diet
MIN_ENABLED_FOODS = 10


# =============================================================================
# UI CONSTANTS - PORTIONS
# =============================================================================

# Threshold for determining portion slider step
# Foods with portion_min < 50g use a smaller step
PORTION_STEP_THRESHOLD = 50  # grams

# Slider step for small portions (e.g. oil, butter)
PORTION_STEP_SMALL = 5  # grams

# Slider step for large portions (e.g. pasta, rice)
PORTION_STEP_LARGE = 10  # grams

# Maximum slider range for small portions
PORTION_SLIDER_MAX_SMALL = 100  # grams

# Maximum slider range for large portions
PORTION_SLIDER_MAX_LARGE = 500  # grams


# =============================================================================
# UI CONSTANTS - LAYOUT
# =============================================================================

# Column weights in the food matrix [Selection, Name, Portions, Rating]
FOOD_MATRIX_COLUMN_WEIGHTS = [0.5, 2, 3, 2.5]

# Maximum range for axiom parameter sliders
AXIOM_PARAMETER_MAX_RANGE = 15

# Maximum meal components (for UI sliders)
MAX_MEAL_COMPONENTS = 3


# =============================================================================
# RATING CONSTANTS
# =============================================================================

# Default rating for a food item (1-5 star scale)
DEFAULT_FOOD_RATING = 3

# Rating range
MIN_FOOD_RATING = 1
MAX_FOOD_RATING = 5
