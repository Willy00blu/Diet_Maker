"""
Pipeline module - Interface between frontend and backend.

This module defines the contracts (dataclasses) and services that allow
the GUI to communicate with the backend without knowing its internals.
"""

from pipeline.contracts import DietRequest, DietResponse, NutritionTargets, AxiomConfig
from pipeline.diet_service import DietService

__all__ = [
    "DietRequest",
    "DietResponse",
    "NutritionTargets",
    "AxiomConfig",
    "DietService",
]
