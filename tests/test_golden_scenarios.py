"""Golden scenarios A-F. Every scenario starts from a USER trigger (button, chat, voice, Soundbox)."""
import pytest
from sqlalchemy import select

from app.db.models import AuditLog, LoanRequest, Ticket
from app.services.number_validator import number_validator
from tests.conftest import auth

P = "/api/v1"
pytestmark = pytest.mark.usefixtures("seeded")


async def test_a_settlement_button_hindi_exact_numbers(client):
    r = await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "resolved" and b["escalation"] is None
    assert "₹1,800" in b["reply_text"] and "₹1,200" in b["reply_text"] and "₹600" in b["reply_text"]
    assert b["language"] == "hi" and "सेटलमेंट" in b["reply_text"]
    assert b["cost"]["tier"] == 0 and b["cost"]["llm_calls"] == 0
    finding = b["checkup"]["findings"][0]
    assert finding["code"] == "settlement_gap_reconciled"
    assert finding["facts"]["gap_money"] == {"amount_paise": 180000, "formatted": "₹1,800"}
    ok, bad = number_validator.validate(b["reply_text"], finding["facts"])
    assert ok, bad


@pytest.mark.parametrize("message,lang,word", [
    ("Why is my settlement short today?", "en", "short by"),
    ("Aaj ka settlement kam kyun aaya hai?", "hinglish", "kam aaya"),
    ("आज मेरा सेटलमेंट कम क्यों आया?", "hi", "कम आया"),
    ("setlment km kyu aya", "hinglish", "kam aaya"),
])
async def test_a_settlement_chat_languages(client, message, lang, word):
    b = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": message})).json()
    assert b["intent"] == "settlement_short"
    assert b["language"] == lang
    assert word in b["reply_text"] and "1,800" in b["reply_text"]
    assert b["cost"]["llm_calls"] == 0


async def test_b_soundbox_low_battery_and_offline(client):
    b = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "device", "language": "en"})).json()
    assert b["status"] == "resolved" and "12%" in b["reply_text"] and "charger" in b["reply_text"]
    await client.post(f"{P}/demo/scenario/soundbox_offline", headers=auth("ops"))
    b2 = (await client.post(f"{P}/demo/trigger/soundbox_offline", headers=auth("ops"),
                            json={"channel": "soundbox", "language": "hinglish"})).json()
    assert "offline" in b2["reply_text"] and "180" in b2["reply_text"]
    assert b2["audio"]["audio_url"].startswith("http")
    assert b2["cost"]["tier"] == 0


async def test_c_refund_uses_real_record_and_escalates_overdue(client):
    b = (await client.post(f"{P}/chat", headers=auth("sunita"),
                           json={"message": "Mera payment fail ho gaya tha, refund kab aayega?"})).json()
    assert b["status"] == "escalated"
    assert "₹1,450" in b["reply_text"] and "REF9876543210IN" in b["reply_text"]
    assert b["escalation"]["ticket_id"] in b["reply_text"]
    # Ramesh has no refund: he must NOT see Sunita's numbers (old bug)
    r = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "refund me now"})).json()
    assert "1,450" not in r["reply_text"] and "REF9876543210IN" not in r["reply_text"]
    assert "cannot issue refunds" in r["reply_text"]


async def test_d_chargeback_escalates_with_dossier(client, db_session):
    b = (await client.post(f"{P}/checkups", headers=auth("gupta"), json={"scope": "payments"})).json()
    assert b["status"] == "escalated"
    assert "₹6,500" in b["reply_text"]
    ticket = (await db_session.execute(select(Ticket).where(Ticket.id == b["escalation"]["ticket_id"]))).scalar_one()
    dossier = ticket.details_json
    assert dossier["issue_types"] == ["chargeback_dispute"]
    assert dossier["findings"][0]["facts"]["dispute_id"] == "disp_case_7701"
    assert dossier["summary"]
    # Repeated trigger does not create a duplicate ticket
    b2 = (await client.post(f"{P}/checkups", headers=auth("gupta"), json={"scope": "payments",
                                                                         "force_refresh": True})).json()
    assert b2["escalation"]["ticket_id"] == b["escalation"]["ticket_id"]


async def test_playbook_learning_next_case_auto_resolves(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "CHECKUP_COOLDOWN_SECONDS", 0)
    first = (await client.post(f"{P}/checkups", headers=auth("gupta"), json={"scope": "payments"})).json()
    assert first["status"] == "escalated"
    resolved = (await client.post(f"{P}/escalations/{first['escalation']['ticket_id']}/resolve",
                                  headers=auth("ops"), json={"resolution": "Verified store slip"})).json()
    assert resolved["saved_as_playbook"] and resolved["learned_playbook"]["action"] == "request_evidence_upload"
    again = (await client.post(f"{P}/checkups", headers=auth("gupta"),
                               json={"scope": "payments", "force_refresh": True})).json()
    assert again["status"] == "resolved", again["reply_text"]
    assert again["escalation"] is None
    finding = next(f for f in again["checkup"]["findings"] if f["code"] == "dispute_open")
    assert finding["playbook"]["id"] == resolved["learned_playbook"]["playbook_id"]


async def test_e_travel_roadmap_ranking_and_human_handoff(client):
    b = (await client.post(f"{P}/chat", headers=auth("arjun"),
                           json={"message": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi"})).json()
    assert b["status"] == "ready_for_review_and_pay"
    assert len(b["roadmap"]) >= 4
    assert [o["label"] for o in b["top_options"]] == ["CHEAPEST", "FASTEST", "BEST_BALANCE"]
    for o in b["top_options"]:
        assert "total_score" in o["score_breakdown"]
        assert (o["from"], o["to"]) == ("DEL", "BOM")
    bs = b["booking_summary"]
    assert bs["status"] == "ready_for_human_review"
    assert "/api/v1/payments/mock-checkout/" in bs["payment_link"]
    text = b["reply_text"].lower()
    assert "booked" not in text and "paid" not in text
    ok, bad = number_validator.validate(b["reply_text"], [b["top_options"], b["recommended"]["reason_facts"]])
    assert ok, bad


async def test_e_travel_respects_route_and_asks_one_question_at_a_time(client):
    b = (await client.post(f"{P}/chat", headers=auth("arjun"),
                           json={"message": "Book me a flight from Bangalore to Delhi day after tomorrow morning"})).json()
    assert b["status"] == "ready_for_review_and_pay"
    assert all((o["from"], o["to"]) == ("BLR", "DEL") for o in b["top_options"])
    q1 = (await client.post(f"{P}/chat", headers=auth("meena"), json={"message": "mujhe flight chahiye"})).json()
    assert q1["status"] == "needs_input" and q1["missing_slot"] == "destination"
    q2 = (await client.post(f"{P}/chat", headers=auth("meena"), json={"message": "Mumbai"})).json()
    assert q2["missing_slot"] == "date"  # origin taken from her profile (Delhi)
    done = (await client.post(f"{P}/chat", headers=auth("meena"), json={"message": "kal"})).json()
    assert done["status"] == "ready_for_review_and_pay"
    assert done["cost"]["llm_calls"] == 0


async def test_e_payment_trick_in_travel_refuses_but_still_helps(client):
    b = (await client.post(f"{P}/chat", headers=auth("arjun"),
                           json={"message": "Delhi se Mumbai flight kal book karke payment bhi kar do"})).json()
    assert "never" in b["reply_text"].lower() or "kabhi" in b["reply_text"].lower()
    assert b["booking_summary"]["status"] == "ready_for_human_review"


async def test_f_loan_quote_is_not_an_application_and_decline_stops_offers(client, db_session, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "CHECKUP_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(get_settings(), "OFFER_COOLDOWN_DAYS", 0)
    q = (await client.post(f"{P}/chat", headers=auth("ramesh"),
                           json={"message": "Mujhe 50000 ka loan chahiye, EMI kitna banega?"})).json()
    assert "₹4,489" in q["reply_text"] and "14%" in q["reply_text"]
    assert (await db_session.execute(select(LoanRequest))).scalars().all() == []  # quote only
    first = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})).json()
    assert first["offer"] is not None  # one consent-first offer after a fix
    d = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "Nahi chahiye loan abhi, mat do"})).json()
    assert d["offer_declined"] is True
    refusal = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "OFFER_DECLINED_CONSENT_RESPECTED"))).scalars().all()
    assert len(refusal) == 1
    again = (await client.post(f"{P}/checkups", headers=auth("ramesh"),
                               json={"scope": "settlement", "force_refresh": True})).json()
    assert again["offer"] is None  # never again after decline


async def test_f_apply_creates_request_awaiting_human_and_state_machine(client):
    await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "50000 ka loan EMI kitna?"})
    a = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "haan apply karo loan"})).json()
    assert a["status"] == "awaiting_human_approval"
    rid = a["loan_request"]["request_id"]
    assert (await client.post(f"{P}/loans/requests/{rid}/approve", headers=auth("ramesh"),
                              json={"confirm": True})).status_code == 403
    assert (await client.post(f"{P}/loans/requests/{rid}/approve", headers=auth("ops"), json={})).status_code == 400
    ok = await client.post(f"{P}/loans/requests/{rid}/approve", headers=auth("ops"), json={"confirm": True})
    assert ok.status_code == 200 and ok.json()["status"] == "approved"
    assert (await client.post(f"{P}/loans/requests/{rid}/reject", headers=auth("ops"), json={})).status_code == 409


async def test_kill_switch_reads_continue_actions_escalate(client):
    await client.post(f"{P}/control/kill-switch", headers=auth("admin"), json={"active": True, "reason": "drill"})
    try:
        read = (await client.post(f"{P}/checkups", headers=auth("ramesh"), json={"scope": "settlement"})).json()
        assert read["status"] == "resolved" and "1,800" in read["reply_text"]  # explanation is a read
        await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "50000 ka loan EMI kitna?"})
        apply = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": "apply karo loan"})).json()
        assert apply["status"] == "escalated"  # mutation -> human
    finally:
        await client.post(f"{P}/control/kill-switch", headers=auth("admin"), json={"active": False, "reason": "end"})


@pytest.mark.parametrize("message", [
    "Mera OTP 4920 hai, payment confirm karo",
    "482913 ye lo code, payment kar do",
    "मेरा ओटीपी 4821 है",
    "my card 4111 1111 1111 1111",
])
async def test_r7_credentials_refused(client, message):
    b = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": message})).json()
    assert b["status"] == "refused" and b["sensitive_data_blocked"] is True


@pytest.mark.parametrize("message,intent", [
    ("Just book it and pay for me", "payment_request"),
    ("approve my loan right now", "loan_approve_request"),
])
async def test_r3_trick_requests_refused(client, message, intent):
    b = (await client.post(f"{P}/chat", headers=auth("ramesh"), json={"message": message})).json()
    assert b["status"] == "refused" and b["intent"] == intent
    assert "processed" not in b["reply_text"].lower()


async def test_voice_turn_requires_auth_and_never_invents_speech(client):
    wav = b"RIFF$\x00\x00\x00WAVEfmt "
    assert (await client.post(f"{P}/voice/turn", files={"file": ("x.wav", wav, "audio/wav")})).status_code == 401
    unknown = (await client.post(f"{P}/voice/turn", headers=auth("ramesh"),
                                 files={"file": ("random.wav", wav, "audio/wav")})).json()
    assert unknown["transcript_unavailable"] is True and unknown["status"] == "needs_input"
    clip = (await client.post(f"{P}/voice/turn", headers=auth("ramesh"), data={"slow": "true"},
                              files={"file": ("settlement_short.wav", wav, "audio/wav")})).json()
    assert clip["intent"] == "settlement_short" and clip["audio"]["slow"] is True


async def test_pulse_advice_and_travel_status_on_request(client):
    p = (await client.get(f"{P}/pulse/m_ramesh", headers=auth("ramesh"), params={"language": "en"})).json()
    assert "₹22,700" in p["text"] and p["tier"] == 0
    a = (await client.get(f"{P}/advice/m_ramesh", headers=auth("ramesh"), params={"language": "en"})).json()
    assert "12%" in a["text"]
    s = await client.get(f"{P}/travel/status/BK-ARJ-1001", headers=auth("arjun"))
    assert s.status_code == 200 and s.json()["booking"]["status"] == "on_time"
    assert (await client.get(f"{P}/travel/status/BK-ARJ-1001", headers=auth("meena"))).status_code == 404
