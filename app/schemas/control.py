from pydantic import BaseModel, Field


class KillSwitchRequest(BaseModel):
    active: bool = Field(..., description="True to engage kill switch, False to resume normal autonomy")
    reason: str | None = Field(None, description="Optional justification or operator note for audit log")
    actor: str = Field("operator", description="Operator identity making the state change")


class ControlStateResponse(BaseModel):
    kill_switch_active: bool = Field(..., description="Whether autonomous actions are paused")
    financial_impact_threshold_inr: float = Field(..., description="Action monetary escalation threshold")
    auto_resolve_confidence_threshold: float = Field(..., description="Minimum confidence for zero-ticket auto resolution")
    clarify_confidence_threshold: float = Field(..., description="Threshold between clarifying question vs escalation")
    last_updated: str = Field(..., description="ISO timestamp of last control state change")
    reason: str | None = Field(None, description="Reason for current kill switch status")
    updated_by: str | None = Field(None, description="Operator who last toggled the kill switch")
