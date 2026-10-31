"""Deterministic tools layer used by specialist agents (thin wrappers over business services).

Ensures all financial figures, calculations, and dates come from deterministic functions (Rule R1).
"""
from app.services.device_service import device_service
from app.services.loan_service import loan_service
from app.services.number_validator import number_validator
from app.services.playbook_service import playbook_service
from app.services.settlement_service import settlement_service
from app.services.templates import templates
from app.services.travel_service import travel_service

__all__ = [
    "settlement_service",
    "device_service",
    "loan_service",
    "travel_service",
    "playbook_service",
    "number_validator",
    "templates",
]
