from typing import Any


class MetricsService:
    """Maintains live counters for tickets prevented, auto-resolutions, escalations,

    support savings, and loan lead conversions.
    """

    def __init__(self) -> None:
        self.tickets_prevented: int = 142
        self.auto_resolved: int = 98
        self.escalated: int = 12
        self.loan_leads: int = 24
        self.total_resolution_seconds: float = 3450.0
        self.total_resolved_cases: int = 98
        self.cost_per_ticket_inr: float = 180.0  # Industry standard support cost per human ticket

    def record_auto_resolve(self, duration_seconds: float = 2.5, is_proactive: bool = False) -> None:
        self.auto_resolved += 1
        if is_proactive:
            self.tickets_prevented += 1
        self.total_resolved_cases += 1
        self.total_resolution_seconds += duration_seconds

    def record_escalation(self) -> None:
        self.escalated += 1

    def record_loan_lead(self) -> None:
        self.loan_leads += 1

    def get_metrics(self) -> dict[str, Any]:
        total_handled = self.auto_resolved + self.escalated
        escalation_rate = round((self.escalated / max(total_handled, 1)) * 100, 1)
        support_cost_saved = round((self.tickets_prevented + self.auto_resolved) * self.cost_per_ticket_inr, 2)
        avg_res_sec = round(self.total_resolution_seconds / max(self.total_resolved_cases, 1), 1)

        return {
            "tickets_prevented": self.tickets_prevented,
            "auto_resolved": self.auto_resolved,
            "escalated": self.escalated,
            "escalation_rate_pct": escalation_rate,
            "support_cost_saved_inr": support_cost_saved,
            "loan_leads": self.loan_leads,
            "avg_resolution_seconds": avg_res_sec,
            "disclaimer": "ALL FIGURES ARE MEASURED ON SIMULATED DATA",
        }


metrics_service = MetricsService()
