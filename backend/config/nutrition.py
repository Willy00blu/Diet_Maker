"""
Nutritional objectives configuration.
Caloric targets, macros, tolerance deltas, and meal distribution.
"""

# ==========================================
# DIET DURATION (DAYS)
# ==========================================
N_DAYS = 5  # Number of diet days (1-7)

# ==========================================
# ENERGY BUDGET (TARGET)
# ==========================================
TARGET_KCAL = 2200

# ==========================================
# MACRO SPLIT (PERCENTAGES)
# ==========================================
PCT_PROT = 0.20  # 20% from protein
PCT_CARB = 0.55  # 55% from carbohydrates
PCT_FAT = 0.25   # 25% from fat

# ==========================================
# TOLERANCE (DELTA)
# ==========================================
DELTA_KCAL = 0.10   # ±10% on calories
DELTA_MACRO = 0.10  # ±10% on macros

# ==========================================
# AUTOMATIC GRAM CALCULATION
# ==========================================
# Calories per gram: Protein=4, Carb=4, Fat=9
TARGET_PROT = (TARGET_KCAL * PCT_PROT) / 4
TARGET_CARB = (TARGET_KCAL * PCT_CARB) / 4
TARGET_FAT = (TARGET_KCAL * PCT_FAT) / 9

