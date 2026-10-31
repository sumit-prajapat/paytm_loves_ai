"""Pre-loaded support policy documents in English and Hindi for Saarthi RAG."""

SUPPORT_POLICIES = [
    {
        "id": "pol_settlement_deductions_en",
        "title": "Settlement Deductions and Adjustments",
        "language": "en",
        "text": """Paytm daily settlements are deposited every morning by 7:00 AM into the merchant's registered bank account.
Settlement gaps or shortfalls occur due to 3 standard reasons:
1. Refund Adjustments: When a customer transaction is refunded, the refunded amount is automatically deducted from the day's settlement.
2. MDR / Service Fees: Standard platform or processing fees (MDR on business transactions or monthly Soundbox rental).
3. Chargeback Holds: If a disputed transaction is flagged for investigation, the transaction amount is placed on temporary hold.
If expected minus actual settlement matches the sum of these line items, no action or complaint ticket is required.""",
    },
    {
        "id": "pol_settlement_deductions_hi",
        "title": "सेटलमेंट कटौती और समायोजन",
        "language": "hi",
        "text": """पेटीएम का दैनिक सेटलमेंट हर सुबह 7:00 बजे तक आपके बैंक खाते में जमा हो जाता है।
सेटलमेंट में कमी आने के तीन मुख्य कारण होते हैं:
1. रिफंड समायोजन (Refund Adjustment): यदि किसी ग्राहक का भुगतान रिफंड किया गया है, तो वह राशि सेटलमेंट से काट ली जाती है।
2. सुविधा शुल्क या किराया (MDR / Rental Fee): साउंडबॉक्स का मासिक किराया या प्रसंस्करण शुल्क।
3. विवादित होल्ड (Chargeback Hold): यदि किसी लेनदेन पर ग्राहक ने बैंक में विवाद दर्ज किया है, तो वह राशि जांच तक रोकी जाती है।
यदि काटा गया कुल पैसा इन मदों से मेल खाता है, तो कोई टिकट दर्ज करने की आवश्यकता नहीं है।""",
    },
    {
        "id": "pol_refund_timelines_en",
        "title": "Customer Refund Timelines and Overdue Policy",
        "language": "en",
        "text": """When a customer payment fails at the merchant store or an automatic refund is triggered:
1. UPI Transactions: Funds are typically reversed back to the customer bank within 24 to 48 hours.
2. Debit/Credit Card & NetBanking: Refunds take between 3 to 7 working days.
3. Bank Reference (UTR / RRN): Once initiated, a unique bank reference number is generated.
Overdue Threshold: If a refund is not credited within 7 business days from the initiation date, it is classified as overdue and must be escalated to a human banking specialist with the bank reference code.""",
    },
    {
        "id": "pol_refund_timelines_hi",
        "title": "रिफंड समय-सीमा और देरी की नीति",
        "language": "hi",
        "text": """यदि ग्राहक का भुगतान असफल हो जाता है या रिफंड शुरू किया जाता है:
1. यूपीआई (UPI): पैसा सामान्यतः 24 से 48 घंटे के भीतर ग्राहक के खाते में वापस आ जाता है।
2. कार्ड और नेटबैंकिंग: 3 से 7 कार्यदिवस का समय लगता है।
3. बैंक रेफरेंस नंबर (UTR/RRN): रिफंड शुरू होते ही बैंक संदर्भ संख्या जारी की जाती है।
देरी की नीति: यदि 7 दिनों के बाद भी रिफंड पूरा नहीं होता है, तो इसे विलंबित (overdue) माना जाता है और बैंक अधिकारी को तुरंत जांच के लिए भेजा जाता है।""",
    },
    {
        "id": "pol_soundbox_offline_en",
        "title": "Paytm Soundbox Offline Troubleshooting",
        "language": "en",
        "text": """If the Paytm Soundbox stops voice payment announcements or appears offline:
1. Low Battery Check: If the battery level drops below 20%, the device enters power save mode. Connect to the charger immediately; the red light turns green when charged.
2. Network Connectivity: Soundbox uses an integrated 4G SIM. Restart the device by holding down the power button for 3 seconds.
3. Audio Test: Press the plus and minus volume buttons simultaneously to trigger a test chime.
4. Auto-Ticketing: If the device does not send heartbeats for more than 4 hours after a restart attempt, Saarthi automatically logs a replacement ticket with 24-48 hours technician visit ETA.""",
    },
    {
        "id": "pol_soundbox_offline_hi",
        "title": "साउंडबॉक्स ऑफलाइन समस्या निवारण",
        "language": "hi",
        "text": """यदि साउंडबॉक्स से आवाज नहीं आ रही है या वह ऑफलाइन दिख रहा है:
1. बैटरी जांच: यदि बैटरी 20% से कम है, तो डिवाइस बंद हो सकता है। तुरंत चार्जर लगाएं।
2. नेटवर्क रीस्टार्ट: पावर बटन को 3 सेकंड तक दबाकर बंद करें और फिर चालू करें ताकि 4G नेटवर्क रीकनेक्ट हो सके।
3. आवाज टेस्ट: प्लस और माइनस बटन एक साथ दबाकर टेस्ट साउंड सुनें।
4. ऑटो-टिकट: यदि रीस्टार्ट के बाद भी 4 घंटे तक साउंडबॉक्स चालू नहीं होता, तो सारथी स्वचालित रूप से 24-48 घंटे के भीतर सर्विस टिकट बना देता है।""",
    },
    {
        "id": "pol_chargeback_dispute_en",
        "title": "Chargeback and Fraud Dispute Handling",
        "language": "en",
        "text": """A chargeback occurs when a cardholder or account owner contacts their issuing bank claiming an unauthorized transaction.
Rules:
1. Autonomous AI agents must NEVER reject or settle chargebacks autonomously.
2. Any chargeback case must be immediately escalated to a human risk specialist along with transaction details, CCTV/bill evidence submission deadlines, and risk score.
3. Merchant has 7 days from the notification date to submit store receipt or delivery acknowledgment.""",
    },
    {
        "id": "pol_chargeback_dispute_hi",
        "title": "चार्ज Giuseppe विवाद और धोखाधड़ी सुरक्षा",
        "language": "hi",
        "text": """चार्ज Giuseppe तब होता है जब कोई ग्राहक अपने बैंक से दावा करता है कि उसने यह लेनदेन नहीं किया है।
नियम:
1. एआई कभी भी अपने आप चार्ज Giuseppe को बंद या अस्वीकार नहीं कर सकता।
2. प्रत्येक चार्ज Giuseppe विवाद को तुरंत मानव विशेषज्ञ को भेजा जाना अनिवार्य है।
3. व्यापारी के पास बिल या साक्ष्य जमा करने के लिए 7 दिनों का समय होता है।""",
    },
    {
        "id": "pol_loan_eligibility_en",
        "title": "Paytm Merchant Working Capital Loan Eligibility & Consent-First Rules",
        "language": "en",
        "text": """Paytm Merchant Cash Advance / Working Capital Loans provide collateral-free financing.
Eligibility Criteria:
- Minimum 3 months of consistent Paytm Soundbox or QR transaction history.
- Average monthly collection exceeding INR 25,000.
- Daily automatic repayment (EDI) deducted seamlessly from morning settlements.
Consent-First Selling Rule:
- The AI agent may propose at most ONE loan offer per interaction.
- The offer must only be presented AFTER a merchant problem has been successfully resolved.
- If the merchant says 'no', 'nahi chahiye', or declines, the AI must immediately cease offers and log the decline.""",
    },
    {
        "id": "pol_loan_eligibility_hi",
        "title": "व्यापारी ऋण (लोन) पात्रता और सहमति नियम",
        "language": "hi",
        "text": """पेटीएम व्यापारी लोन बिना किसी गारंटी (कोलेटरल-फ्री) के कार्यशील पूंजी प्रदान करता है।
पात्रता शर्तें:
- कम से कम 3 महीने का सक्रिय QR या साउंडबॉक्स उपयोग।
- मासिक व्यापार कम से कम ₹25,000।
- दैनिक ईएमआई हर सुबह के सेटलमेंट से अपने आप कट जाती है।
सहमति का नियम:
- एआई केवल एक बार ही लोन का सुझाव दे सकता है, वह भी तब जब व्यापारी की समस्या का समाधान हो चुका हो।
- यदि व्यापारी मना कर दे ('नहीं चाहिए'), तो एआई तुरंत रुक जाएगा और दोबारा प्रस्ताव नहीं देगा।""",
    },
    {
        "id": "pol_travel_cancellation_en",
        "title": "Domestic Flight Booking and Cancellation Policies",
        "language": "en",
        "text": """Domestic flights within India are subject to airline fare conditions:
1. Refundable Fares: Eligible for refund minus airline cancellation charges up to 2 hours prior to scheduled departure.
2. Non-Refundable Fares: Only government passenger fees (UDF/PSF) are refundable upon cancellation.
3. Free Cancellation Add-on: Full refund if cancelled up to 24 hours before departure.
4. Human Review & Pay: The AI assistant generates the optimal travel roadmap and reservation summary, but never authorizes payments or enters PINs. Final payment is always human-executed on the Paytm secure checkout screen.""",
    },
    {
        "id": "pol_travel_cancellation_hi",
        "title": "घरेलू उड़ान बुकिंग और रद्दीकरण नीति",
        "language": "hi",
        "text": """भारत में घरेलू उड़ानों के नियम:
1. रिफंडेबल टिकट: प्रस्थान से 2 घंटे पहले तक एयरलाइन शुल्क काटकर पैसा वापस मिलता है।
2. नॉन-रिफंडेबल टिकट: केवल सरकारी टैक्स वापस मिलता है, मूल किराया नहीं।
3. भुगतान का नियम: एआई सहायक केवल सबसे अच्छी उड़ानों की तुलना और अनुशंसा करता है। भुगतान हमेशा उपयोगकर्ता स्वयं 'रिव्यू और पे' बटन दबाकर अपने सुरक्षित पेटीएम पिन से करता है।""",
    },
    {
        "id": "pol_pin_otp_safety_en",
        "title": "Paytm Security & Zero PIN/OTP Policy",
        "language": "en",
        "text": """Security Non-Negotiable Rules:
1. Paytm, its employees, and Saarthi AI will NEVER ask for your UPI PIN, ATM PIN, OTP, password, or CVV.
2. If any customer or merchant enters or states a PIN or OTP in chat or voice, Saarthi must immediately REFUSE to process, issue a scam warning, and redact the credentials.
3. UPI PIN is only needed to SEND money, never to RECEIVE money.""",
    },
    {
        "id": "pol_pin_otp_safety_hi",
        "title": "सुरक्षा और पिन/ओटीपी नियम",
        "language": "hi",
        "text": """सुरक्षा का सबसे महत्वपूर्ण नियम:
1. पेटीएम या सारथी कभी भी आपका यूपीआई पिन, ओटीपी, या पासवर्ड नहीं मांगता।
2. पैसे प्राप्त करने के लिए कभी पिन दर्ज करने की आवश्यकता नहीं होती।
3. यदि कोई व्यक्ति आपसे पिन या ओटीपी मांगता है तो वह धोखाधड़ी (फ्रॉड) है।""",
    },
    {
        "id": "pol_festival_preparation_en",
        "title": "Festival Surge Support and Proactive Preparedness",
        "language": "en",
        "text": """During major Indian festivals (Diwali, Eid, Holi, Durga Puja), merchant footfall spikes by 300%.
1. Saarthi proactively scans device battery levels and network heartbeats 2 to 3 days before festival peaks.
2. If battery health is below 30% or firmware is outdated, Saarthi proactively sends a voice alert to ensure zero downtime during festive rush hours.""",
    },
    {
        "id": "pol_festival_preparation_hi",
        "title": "त्योहार तैयारी और अग्रिम चेतावनी",
        "language": "hi",
        "text": """दिवाली, होली, ईद जैसे बड़े त्योहारों में दुकान पर ग्राहकों की भीड़ 3 गुना बढ़ जाती है।
1. सारथी त्योहार से 2-3 दिन पहले ही साउंडबॉक्स की बैटरी और नेटवर्क की जांच करता है।
2. यदि बैटरी कम है, तो अग्रिम आवाज संदेश भेजकर व्यापारी को चार्ज करने की सलाह दी जाती है ताकि त्योहार के दिन कोई बाधा न आए।""",
    },
]
