"""
Food configuration.
Each food can be enabled/disabled, selectable or not,
and has a preference rating.
"""

# ==========================================
# FOOD CONFIGURATION (GUI DEFAULTS)
# ==========================================
# - enabled: show/hide the food in the UI
# - selectable: allow the solver to choose it automatically
#               If False, the food is visible but never auto-selected
# - preference: 1-5 stars (3 = neutral default, 5 = highly preferred)
# - name: for reference only
#
# With objective "preference", the system will favour foods
# with higher preference ratings.

FOODS_CONFIG = {
    "1":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Greek Yogurt"},
    "2":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Whole Eggs"},
    "3":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Egg Whites"},
    "4":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Turkey Breast"},
    "5":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Rusk Crackers"},
    "6":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Oats"},
    "7":  {"enabled": True, "selectable": False, "preference": 3, "name": "Whole Grain Cookies"},
    "8":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Whole Wheat Pasta"},
    "9":  {"enabled": True, "selectable": True,  "preference": 3, "name": "Basmati Rice"},
    "10": {"enabled": True, "selectable": False, "preference": 3, "name": "Spelt"},
    "11": {"enabled": True, "selectable": True,  "preference": 3, "name": "Chicken Breast"},
    "12": {"enabled": True, "selectable": True,  "preference": 3, "name": "Beef Steak"},
    "13": {"enabled": True, "selectable": True,  "preference": 3, "name": "Lean Burger Patty"},
    "14": {"enabled": True, "selectable": True,  "preference": 3, "name": "Fresh Salmon"},
    "15": {"enabled": True, "selectable": True,  "preference": 3, "name": "Cod"},
    "16": {"enabled": True, "selectable": True,  "preference": 3, "name": "Canned Tuna (natural)"},
    "17": {"enabled": True, "selectable": True,  "preference": 3, "name": "Smoked Salmon"},
    "18": {"enabled": True, "selectable": True,  "preference": 3, "name": "Canned Chickpeas"},
    "19": {"enabled": True, "selectable": False, "preference": 3, "name": "Lentils"},
    "20": {"enabled": True, "selectable": True,  "preference": 3, "name": "Borlotti Beans"},
    "21": {"enabled": True, "selectable": True,  "preference": 3, "name": "Whole Grain Bread"},
    "22": {"enabled": True, "selectable": True,  "preference": 3, "name": "Potatoes"},
    "23": {"enabled": True, "selectable": True,  "preference": 3, "name": "Rice Cakes"},
    "24": {"enabled": True, "selectable": False, "preference": 3, "name": "Whole Grain Crackers"},
    "25": {"enabled": True, "selectable": True,  "preference": 3, "name": "Parmesan Cheese"},
    "26": {"enabled": True, "selectable": True,  "preference": 3, "name": "Walnuts"},
    "27": {"enabled": True, "selectable": True,  "preference": 3, "name": "Almonds"},
    "28": {"enabled": True, "selectable": True,  "preference": 3, "name": "Extra Virgin Olive Oil"},
    "29": {"enabled": True, "selectable": True,  "preference": 3, "name": "Avocado"},
    "30": {"enabled": True, "selectable": True,  "preference": 3, "name": "Zucchini"},
    "31": {"enabled": True, "selectable": False, "preference": 3, "name": "Mixed Salad"},
    "32": {"enabled": True, "selectable": True,  "preference": 3, "name": "Spinach"},
    "33": {"enabled": True, "selectable": False, "preference": 3, "name": "Broccoli"},
    "34": {"enabled": True, "selectable": False, "preference": 3, "name": "Apple"},
    "35": {"enabled": True, "selectable": True,  "preference": 3, "name": "Banana"},
    "36": {"enabled": True, "selectable": True,  "preference": 3, "name": "Orange"},
    "37": {"enabled": True, "selectable": False, "preference": 3, "name": "Ricotta Cheese"},
    "38": {"enabled": True, "selectable": False, "preference": 3, "name": "Cottage Cheese"},
    "39": {"enabled": True, "selectable": True,  "preference": 3, "name": "Bresaola"},
    "40": {"enabled": True, "selectable": True,  "preference": 3, "name": "Lean Prosciutto"},
    "41": {"enabled": True, "selectable": True,  "preference": 3, "name": "Whey Protein"},
    "42": {"enabled": True, "selectable": False, "preference": 3, "name": "Kefir"},
    "43": {"enabled": True, "selectable": False, "preference": 3, "name": "Couscous"},
    "44": {"enabled": True, "selectable": False, "preference": 3, "name": "Quinoa"},
    "45": {"enabled": True, "selectable": False, "preference": 3, "name": "Potato Gnocchi"},
    "46": {"enabled": True, "selectable": False, "preference": 3, "name": "Polenta"},
    "47": {"enabled": True, "selectable": False, "preference": 3, "name": "Rye Bread"},
    "48": {"enabled": True, "selectable": False, "preference": 3, "name": "Sweet Potatoes"},
    "49": {"enabled": True, "selectable": True,  "preference": 3, "name": "Pork Loin"},
    "50": {"enabled": True, "selectable": True,  "preference": 3, "name": "Lean Ground Beef"},
    "51": {"enabled": True, "selectable": False, "preference": 3, "name": "Sea Bream"},
    "52": {"enabled": True, "selectable": False, "preference": 3, "name": "Shrimp"},
    "53": {"enabled": True, "selectable": True,  "preference": 3, "name": "Swordfish"},
    "54": {"enabled": True, "selectable": True,  "preference": 3, "name": "Canned Mackerel"},
    "55": {"enabled": True, "selectable": True,  "preference": 3, "name": "Frozen Peas"},
    "56": {"enabled": True, "selectable": False, "preference": 3, "name": "Edamame"},
    "57": {"enabled": True, "selectable": False, "preference": 3, "name": "Plain Tofu"},
    "58": {"enabled": True, "selectable": False, "preference": 3, "name": "Chickpea Hummus"},
    "59": {"enabled": True, "selectable": True,  "preference": 3, "name": "Dark Chocolate 85%"},
    "60": {"enabled": True, "selectable": True,  "preference": 3, "name": "Peanut Butter"},
    "61": {"enabled": True, "selectable": True,  "preference": 3, "name": "Chia/Flax Seeds"},
    "63": {"enabled": True, "selectable": True,  "preference": 3, "name": "Carrots"},
    "64": {"enabled": True, "selectable": True,  "preference": 3, "name": "Green Beans"},
    "65": {"enabled": True, "selectable": False, "preference": 3, "name": "Fennel"},
    "66": {"enabled": True, "selectable": False, "preference": 3, "name": "Bell Peppers"},
    "67": {"enabled": True, "selectable": False, "preference": 3, "name": "Cauliflower"},
    "68": {"enabled": True, "selectable": True,  "preference": 3, "name": "Pear"},
    "69": {"enabled": True, "selectable": False, "preference": 3, "name": "Kiwi"},
    "70": {"enabled": True, "selectable": False, "preference": 3, "name": "Mixed Berries"},
}
