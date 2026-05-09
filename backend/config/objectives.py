"""
Objective function configuration.
Defines available objectives and their parameters.
"""

# ==========================================
# AVAILABLE OBJECTIVE FUNCTIONS
# ==========================================
OBJECTIVES_CONFIG = {
    "cost": {
        "enabled": True,
        "default": False,
        "icon": "💰",
        "label": "Minimize Cost",
        "description": "Minimize total grocery cost",
        "params": {}
    },
    "preference": {
        "enabled": True,
        "default": False,
        "icon": "⭐",
        "label": "Maximize Preferences",
        "description": "Maximize use of preferred foods",
        "params": {}
    },
    "none": {
        "enabled": True,
        "default": True,
        "icon": "⚡",
        "label": "Quick Solution",
        "description": "Find any valid solution (fastest)",
        "params": {}
    },
}

# ==========================================
# SOLVER CONFIGURATION
# ==========================================
SOLVER_CONFIG = {
    "timeout": 60,      # seconds
    "gap_rel": 0.10,    # 10% gap from optimum
    "msg": 0,           # 0 = silent, 1 = verbose
}
