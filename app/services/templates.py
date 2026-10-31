"""Deterministic response templates and number-to-Hindi speech formatting

to ensure zero LLM hallucination of financial or timeline numbers.
"""

HINDI_NUMBERS = {
    0: "shunya",
    1: "ek",
    2: "do",
    3: "teen",
    4: "chaar",
    5: "paanch",
    6: "chhah",
    7: "saat",
    8: "aath",
    9: "nau",
    10: "das",
    11: "gyarah",
    12: "barah",
    13: "terah",
    14: "chaudah",
    15: "pandrah",
    16: "solah",
    17: "satrah",
    18: "atharah",
    19: "unnees",
    20: "bees",
    25: "pachees",
    30: "tees",
    40: "chaalis",
    50: "pachaas",
    60: "saath",
    70: "sattar",
    80: "assi",
    90: "nabbe",
    100: "ek sau",
}


def number_to_spoken_hindi(n: float | int) -> str:
    """Converts common numbers to spoken Hindi (e.g. 1800 -> 'atharah sau', 50000 -> 'pachaas hazaar')."""
    n = int(round(n))
    if n == 0:
        return "shunya"
    if n < 0:
        return f"minus {number_to_spoken_hindi(abs(n))}"

    if n >= 100000:
        lakhs = n // 100000
        rem = n % 100000
        lakh_word = HINDI_NUMBERS.get(lakhs, str(lakhs)) + " lakh"
        if rem == 0:
            return lakh_word
        return f"{lakh_word} {number_to_spoken_hindi(rem)}"

    if n >= 1000:
        # Check hundreds format like 1800 -> atharah sau
        if n % 100 == 0 and n <= 9900:
            hundreds = n // 100
            if hundreds in HINDI_NUMBERS:
                return f"{HINDI_NUMBERS[hundreds]} sau"

        thousands = n // 1000
        rem = n % 1000
        th_word = HINDI_NUMBERS.get(thousands, str(thousands)) + " hazaar"
        if rem == 0:
            return th_word
        return f"{th_word} {number_to_spoken_hindi(rem)}"

    if n >= 100:
        hundreds = n // 100
        rem = n % 100
        h_word = HINDI_NUMBERS.get(hundreds, str(hundreds)) + " sau"
        if rem == 0:
            return h_word
        return f"{h_word} {number_to_spoken_hindi(rem)}"

    return HINDI_NUMBERS.get(n, str(n))


class TemplateEngine:
    """Pre-built deterministic templates for Saarthi merchant & travel scenarios."""

    @staticmethod
    def settlement_explanation(
        name: str,
        gap: float,
        refund_adj: float,
        fee: float,
        chargeback_hold: float = 0.0,
        language: str = "hi",
    ) -> str:
        gap_int = int(round(gap))
        refund_int = int(round(refund_adj))
        fee_int = int(round(fee))

        if language == "hi" or language == "hinglish":
            parts = []
            if refund_adj > 0:
                parts.append(f"₹{refund_int:,} refund adjust hua")
            if fee > 0:
                parts.append(f"₹{fee_int:,} fees")
            if chargeback_hold > 0:
                parts.append(f"₹{int(round(chargeback_hold)):,} chargeback hold")
            breakdown = " aur ".join(parts) if parts else "koi katoti nahi"
            return f"{name} ji, aaj ka settlement ₹{gap_int:,} kam aaya hai. {breakdown}. Aapko kuch karne ki zaroorat nahi."
        else:
            return f"{name}, today's settlement is short by ₹{gap_int:,} due to ₹{refund_int:,} refund adjustment and ₹{fee_int:,} fees. No action is required."

    @staticmethod
    def soundbox_spoken_settlement(name: str, gap: float, refund_adj: float, fee: float) -> str:
        gap_hindi = number_to_spoken_hindi(gap)
        ref_hindi = number_to_spoken_hindi(refund_adj)
        fee_hindi = number_to_spoken_hindi(fee)
        return f"{name} ji, aaj ka settlement {gap_hindi} rupaye kam aaya hai. {ref_hindi} rupaye refund adjust hua aur {fee_hindi} rupaye fees. Aapko kuch karne ki zaroorat nahi."

    @staticmethod
    def soundbox_offline_instruction(battery: int, language: str = "hi") -> str:
        if language == "hi" or language == "hinglish":
            return f"Soundbox ki battery {battery}% hai. Kripya charger lagaiye aur network check kijiye."
        return f"Soundbox battery is at {battery}%. Please connect the charger and verify cellular connectivity."

    @staticmethod
    def refund_status_explanation(amount: float, bank_ref: str | None, status: str, language: str = "hi") -> str:
        amt_int = int(round(amount))
        ref_str = f"Bank Ref {bank_ref}" if bank_ref else "bank reference"
        if status == "overdue":
            if language == "hi" or language == "hinglish":
                return f"Aapka ₹{amt_int:,} ka refund samay seema se zyada vilambit hai. Humne ise prathmikta par banking team ko bhej diya hai ({ref_str})."
            return f"Your refund of ₹{amt_int:,} is overdue beyond the standard SLA. Escalated to banking team with {ref_str}."
        else:
            if language == "hi" or language == "hinglish":
                return f"Aapka ₹{amt_int:,} ka refund {ref_str} par process ho raha hai. Isme 3 se 7 din lagte hain."
            return f"Your refund of ₹{amt_int:,} is being processed under {ref_str}. Standard processing takes 3 to 7 business days."

    @staticmethod
    def loan_offer_proposal(eligible_limit: float, language: str = "hi") -> str:
        lim_int = int(round(eligible_limit))
        if language == "hi" or language == "hinglish":
            return f"Aapke behtar QR record ke adhar par ₹{lim_int:,} tak ka pre-approved loan uplabdh hai. Kya aap iski jankari chahte hain?"
        return f"Based on your store collections, you are eligible for an instant working capital loan up to ₹{lim_int:,}. Would you like to know more?"

    @staticmethod
    def loan_emi_explanation(amount: float, tenure_months: int, emi: float, rate_pct: float, language: str = "hi") -> str:
        amt_int = int(round(amount))
        emi_int = int(round(emi))
        if language == "hi" or language == "hinglish":
            return f"₹{amt_int:,} ke liye {tenure_months} mahine ki EMI ₹{emi_int:,} hogi ({rate_pct}% annual rate par). Daily subah settlement se adjust hoti hai."
        return f"For ₹{amt_int:,} across {tenure_months} months, the EMI will be ₹{emi_int:,} per month ({rate_pct}% interest), auto-debited daily."

    @staticmethod
    def travel_recommendation_reason(diff_price: float, saved_minutes: int, has_free_cancellation: bool, language: str = "hi") -> str:
        diff_int = int(round(abs(diff_price)))
        cancel_text = "aur free cancellation hai" if has_free_cancellation else "aur behtar timing hai"
        if language == "hi" or language == "hinglish":
            if diff_price >= 0:
                return f"Ye ₹{diff_int:,} zyada hai par {saved_minutes} minute jaldi pahunchata hai {cancel_text}."
            else:
                return f"Ye ₹{diff_int:,} sasta hai aur {saved_minutes} minute jaldi pahunchata hai {cancel_text}."
        return f"This option is ₹{diff_int:,} {'more' if diff_price >= 0 else 'cheaper'} but reaches {saved_minutes} minutes faster with {'free cancellation' if has_free_cancellation else 'optimal timings'}."


templates = TemplateEngine()
