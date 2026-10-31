import uuid
from typing import Any


class MockPaymentLinkGenerator:
    """Generates secure payment review links for HUMAN checkout.

    Strictly satisfies Rule R3: The AI never authorizes or confirms payments autonomously.
    """

    @staticmethod
    def create_payment_order(
        amount: float,
        description: str,
        customer_id: str | None = None,
        merchant_id: str | None = None,
    ) -> dict[str, Any]:
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        link = f"https://securegw-stage.paytm.in/order/checkout?order_id={order_id}&amount={amount}"

        return {
            "order_id": order_id,
            "amount_inr": amount,
            "description": description,
            "status": "awaiting_human_upi_pin",
            "payment_link": link,
            "review_and_pay_button": {
                "text": "Review and Pay on Paytm",
                "target_url": link,
                "requires_upi_pin": True,
            },
            "guardrail_notice": "HUMAN PAYMENT ONLY: Saarthi agent cannot auto-debit accounts or input PINs.",
        }


payment_adapter = MockPaymentLinkGenerator()
