import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Base(DeclarativeBase):
    pass


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="hi")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    joined_on: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now
    )
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    kyc_status: Mapped[str] = mapped_column(String(32), default="verified")

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="merchant"
    )
    settlements: Mapped[list["Settlement"]] = relationship(
        back_populates="merchant"
    )
    devices: Mapped[list["Device"]] = relationship(back_populates="merchant")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="merchant")
    loan_profile: Mapped["LoanProfile | None"] = relationship(
        back_populates="merchant", uselist=False
    )
    loan_requests: Mapped[list["LoanRequest"]] = relationship(
        back_populates="merchant"
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    home_city: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="hi")
    travel_history: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_txn_merchant_status_ts", "merchant_id", "status", "ts"),)

    txn_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="upi")
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, index=True
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="transaction")
    disputes: Mapped[list["Dispute"]] = relationship(back_populates="transaction")


class Settlement(Base):
    __tablename__ = "settlements"
    __table_args__ = (Index("ix_settlement_merchant_date", "merchant_id", "date"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.id"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    expected: Mapped[float] = mapped_column(Float, nullable=False)
    actual: Mapped[float] = mapped_column(Float, nullable=False)
    gap: Mapped[float] = mapped_column(Float, nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="settlements")
    items: Mapped[list["SettlementItem"]] = relationship(
        back_populates="settlement"
    )


class SettlementItem(Base):
    __tablename__ = "settlement_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    settlement_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("settlements.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # refund_adjustment | fee | chargeback_hold
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    settlement: Mapped["Settlement"] = relationship(back_populates="items")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    txn_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("transactions.txn_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # pending | processed | failed | overdue
    initiated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now
    )
    expected_by: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    bank_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="refunds")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("merchants.id"), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String(64), default="Soundbox v3")
    battery: Mapped[int] = mapped_column(Integer, default=100)
    network: Mapped[str] = mapped_column(String(32), default="4G")
    last_seen: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, index=True
    )
    firmware: Mapped[str] = mapped_column(String(32), default="v2.4.1")

    merchant: Mapped["Merchant | None"] = relationship(back_populates="devices")
    events: Mapped[list["DeviceEvent"]] = relationship(back_populates="device")


class DeviceEvent(Base):
    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id"), nullable=False, index=True
    )
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, index=True
    )
    event: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # offline | low_battery | reboot

    device: Mapped["Device"] = relationship(back_populates="events")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="open"
    )  # open | in_progress | resolved | closed
    source: Mapped[str] = mapped_column(
        String(32), default="saarthi"
    )  # human | saarthi
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    eta: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now
    )
    case_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    checkup_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Full escalation dossier so humans never ask the merchant to repeat the story
    details_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="tickets")


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    txn_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("transactions.txn_id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="open"
    )  # open | under_review | won | lost
    deadline: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    evidence_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )

    transaction: Mapped["Transaction"] = relationship(back_populates="disputes")


class LoanProfile(Base):
    __tablename__ = "loan_profiles"

    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.id"), primary_key=True
    )
    monthly_volume: Mapped[float] = mapped_column(Float, default=0.0)
    vintage_months: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=700)
    eligible_limit: Mapped[float] = mapped_column(Float, default=0.0)

    merchant: Mapped["Merchant"] = relationship(back_populates="loan_profile")


class LoanRequest(Base):
    __tablename__ = "loan_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    tenure: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    emi: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="awaiting_approval"
    )  # awaiting_approval | approved | rejected | declined_by_merchant
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="loan_requests")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en")


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    root_cause: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    conditions_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_from_case: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    output: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    # R12 cost accounting (per step; the captain "finalize" step carries request totals)
    tier: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, index=True
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    previous_hash: Mapped[str] = mapped_column(
        String(64), default="GENESIS_HASH"
    )
    hash: Mapped[str] = mapped_column(
        String(64), default="UNVERIFIED"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=get_utc_now, index=True
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # merchant | traveller | ops_agent | admin
    merchant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    airline: Mapped[str] = mapped_column(String(64), nullable=False)
    from_iata: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    to_iata: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    dep_time: Mapped[str] = mapped_column(String(16), nullable=False)
    arr_time: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    stops: Mapped[int] = mapped_column(Integer, default=0)
    price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    refundable: Mapped[bool] = mapped_column(Boolean, default=False)
    on_time_pct: Mapped[float] = mapped_column(Float, default=90.0)
    date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    __table_args__ = (Index("ix_flight_route_date", "from_iata", "to_iata", "date"),)


class Airport(Base):
    __tablename__ = "airports"

    iata: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)


class Festival(Base):
    __tablename__ = "festivals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(64), default="National")


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="hi")
    expected_outcome: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # auto_resolve | escalate | ask_clarification | refuse
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)


# ---------------------------------------------------------------------------
# On-demand (R11) and cost-aware (R12) tables
# ---------------------------------------------------------------------------
class Checkup(Base):
    """One user-triggered check-up for ONE merchant. Doubles as the result cache (R12)."""

    __tablename__ = "checkups"
    __table_args__ = (
        Index("ix_checkup_merchant_scope_created", "merchant_id", "scope", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # settlement|device|payments|refunds|all
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # app|chat|voice|soundbox
    language: Mapped[str] = mapped_column(String(16), default="hi")
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)  # actor user id
    on_behalf: Mapped[bool] = mapped_column(Boolean, default=False)  # ops agent acting for merchant
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # resolved|no_issue|escalated
    findings_json: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    reply_text: Mapped[str] = mapped_column(Text, default="")
    ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tier: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cache_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now, index=True)


class UsageEvent(Base):
    """Ledger of requests and LLM calls used for quotas, budgets and cost metrics (R12).

    Kept in the DB (not process memory) so quotas hold across stateless workers.
    """

    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_user_kind_ts", "user_id", "kind", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)  # subject charged
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    case_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # request|llm_call|llm_cache_hit|checkup_cache_hit
    request_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tier: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now, index=True)


class OfferConsent(Base):
    """Persisted consent state so a declined offer is never shown again (R6)."""

    __tablename__ = "offer_consents"

    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="none")  # none|offered|declined|accepted
    offers_shown: Mapped[int] = mapped_column(Integer, default=0)
    last_offered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    declined_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)


class ConversationState(Base):
    """Short-lived dialogue state (slots, pending question) kept in the DB for stateless workers."""

    __tablename__ = "conversation_states"

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=get_utc_now)


class TravelBooking(Base):
    """Simulated bookings so a traveller can ask for status ON REQUEST (no watchers)."""

    __tablename__ = "travel_bookings"

    booking_ref: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customers.id"), nullable=False, index=True
    )
    flight_no: Mapped[str] = mapped_column(String(16), nullable=False)
    airline: Mapped[str] = mapped_column(String(64), nullable=False)
    from_iata: Mapped[str] = mapped_column(String(8), nullable=False)
    to_iata: Mapped[str] = mapped_column(String(8), nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    dep_time: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="on_time")  # on_time|delayed|cancelled
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    terminal: Mapped[str | None] = mapped_column(String(8), nullable=True)
    gate: Mapped[str | None] = mapped_column(String(8), nullable=True)
