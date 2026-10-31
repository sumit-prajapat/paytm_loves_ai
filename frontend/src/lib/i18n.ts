/** UI chrome strings and landing page copy. Agent replies come from the backend. */
import type { Lang } from "@/types/contracts";

export type Key =
  | "mic.hold" | "mic.release" | "mic.cancel" | "stt.fail" | "stt.listening" | "scam" | "escalated" | "human" | "pay" | "pay.note"
  | "simulated" | "you.checked" | "type.here" | "welcome" | "welcome.sub" | "settlement" | "soundbox" | "refund" | "payments"
  | "understood" | "more.detail" | "online" | "assistant" | "typing" | "recheck" | "raise.issue" | "insist" | "trip.placeholder"
  | "choose.this" | "why" | "listen" | "yes.ok" | "no.more" | "loan.yes" | "loan.no" | "apply" | "check.all" | "pulse"
  | "advice" | "offline" | "send" | "elder" | "lowdata" | "clear" | "how.known" | "type.instead" | "audio.unavailable"
  // Landing page keys
  | "landing.hero.title" | "landing.hero.sub" | "landing.hero.cta.settlement" | "landing.hero.cta.voice" | "landing.hero.cta.try"
  | "landing.badge.humanApproval" | "landing.badge.auditLog" | "landing.badge.killSwitch" | "landing.badge.onDemand"
  | "landing.problem.title" | "landing.problem.sub" | "landing.problem.botTitle" | "landing.problem.botDesc" | "landing.problem.saarthiTitle" | "landing.problem.saarthiDesc"
  | "landing.how.title" | "landing.how.sub"
  | "landing.how.step1.title" | "landing.how.step1.desc"
  | "landing.how.step2.title" | "landing.how.step2.desc"
  | "landing.how.step3.title" | "landing.how.step3.desc"
  | "landing.how.step4.title" | "landing.how.step4.desc"
  | "landing.how.step5.title" | "landing.how.step5.desc"
  | "landing.care.title" | "landing.care.desc" | "landing.care.tag" | "landing.care.cta"
  | "landing.travel.title" | "landing.travel.desc" | "landing.travel.tag" | "landing.travel.cta"
  | "landing.voice.title" | "landing.voice.sub" | "landing.voice.tag1" | "landing.voice.tag2" | "landing.voice.tag3"
  | "landing.trust.title" | "landing.trust.sub"
  | "landing.trust.point1" | "landing.trust.point2" | "landing.trust.point3" | "landing.trust.point4"
  | "landing.metrics.title" | "landing.metrics.sub" | "landing.metrics.disclaimer"
  | "landing.faq.title" | "landing.faq.sub"
  | "landing.faq.q1" | "landing.faq.a1"
  | "landing.faq.q2" | "landing.faq.a2"
  | "landing.faq.q3" | "landing.faq.a3"
  | "landing.faq.q4" | "landing.faq.a4"
  | "landing.footer.credits" | "landing.footer.builtFor";

const S: Record<Key, Record<"hinglish" | "hi" | "en", string>> = {
  "mic.hold": { hinglish: "Daba ke boliye", hi: "दबा के बोलिए", en: "Hold to speak" },
  "mic.release": { hinglish: "Chhodne par bhejega", hi: "छोड़ने पर भेजेगा", en: "Release to send" },
  "mic.cancel": { hinglish: "Cancel ke liye bahar khiskaiye", hi: "रद्द करने के लिए बाहर खिसकाइए", en: "Slide away to cancel" },
  "stt.fail": { hinglish: "Samajh nahi aaya, dobara boliye ya likhiye", hi: "समझ नहीं आया, दोबारा बोलिए या लिखिए", en: "Didn't catch that, try again or type" },
  "stt.listening": { hinglish: "Sun raha hoon…", hi: "सुन रहा हूँ…", en: "Listening…" },
  scam: { hinglish: "Saarthi kabhi PIN, OTP ya password nahi maangta.", hi: "सारथी कभी PIN, OTP या पासवर्ड नहीं माँगता।", en: "Saarthi never asks for PIN, OTP or passwords." },
  escalated: { hinglish: "Hamari team ye dekh rahi hai. Aapko dobara batane ki zaroorat nahi.", hi: "हमारी टीम यह देख रही है। आपको दोबारा बताने की ज़रूरत नहीं।", en: "Our team is on it. You won't need to repeat yourself." },
  human: { hinglish: "Insaan se baat karein", hi: "इंसान से बात करें", en: "Talk to a person" },
  pay: { hinglish: "Review and Pay", hi: "देखें और भुगतान करें", en: "Review and Pay" },
  "pay.note": { hinglish: "Payment aap khud karenge. Saarthi kabhi PIN nahi dekhta.", hi: "भुगतान आप खुद करेंगे। सारथी कभी PIN नहीं देखता।", en: "You make the payment yourself. Saarthi never sees your PIN." },
  simulated: { hinglish: "Simulated data", hi: "सिम्युलेटेड डेटा", en: "Simulated data" },
  "you.checked": { hinglish: "Aapne check kiya", hi: "आपने जाँच की", en: "You asked" },
  "type.here": { hinglish: "Likhiye…", hi: "लिखिए…", en: "Type a message…" },
  welcome: { hinglish: "Namaste", hi: "नमस्ते", en: "Namaste" },
  "welcome.sub": { hinglish: "Bol ke ya likh ke poochiye, ya ek button dabaiye", hi: "बोलकर या लिखकर पूछिए, या एक बटन दबाइए", en: "Ask by voice or text, or tap a check" },
  settlement: { hinglish: "Settlement (aaj ka paisa)", hi: "सेटलमेंट (आज का पैसा)", en: "Settlement (today's money)" },
  soundbox: { hinglish: "Soundbox", hi: "साउंडबॉक्स", en: "Soundbox" },
  refund: { hinglish: "Refund", hi: "रिफ़ंड", en: "Refund" },
  payments: { hinglish: "Payments", hi: "पेमेंट", en: "Payments" },
  understood: { hinglish: "Samajh gaya 👍", hi: "समझ गया 👍", en: "Got it 👍" },
  "more.detail": { hinglish: "Aur detail", hi: "और जानकारी", en: "More detail" },
  online: { hinglish: "aapka sahayak · online", hi: "आपका सहायक · ऑनलाइन", en: "your assistant · online" },
  assistant: { hinglish: "Saarthi", hi: "सारथी", en: "Saarthi" },
  typing: { hinglish: "Saarthi kaam kar raha hai…", hi: "सारथी काम कर रहा है…", en: "Saarthi is working…" },
  recheck: { hinglish: "Phir se check karein", hi: "फिर से जाँचें", en: "Re-check" },
  "raise.issue": { hinglish: "Shikayat darj karein", hi: "शिकायत दर्ज करें", en: "Raise an issue" },
  insist: { hinglish: "Phir bhi ticket banayein", hi: "फिर भी टिकट बनाएँ", en: "Create a ticket anyway" },
  "trip.placeholder": { hinglish: "Kahan jaana hai? Bol ke batayein…", hi: "कहाँ जाना है? बोलकर बताइए…", en: "Where do you want to go?" },
  "choose.this": { hinglish: "Ye wala chuniye", hi: "यह वाला चुनिए", en: "Choose this" },
  why: { hinglish: "Kyun? score dekhein", hi: "क्यों? स्कोर देखें", en: "Why? see score" },
  listen: { hinglish: "Sunein", hi: "सुनिए", en: "Listen" },
  "yes.ok": { hinglish: "Haan, ye theek hai", hi: "हाँ, ये ठीक है", en: "Yes, this is fine" },
  "no.more": { hinglish: "Nahi, aur dikhayein", hi: "नहीं, और दिखाइए", en: "No, show more" },
  "loan.yes": { hinglish: "Haan, batayein", hi: "हाँ, बताइए", en: "Yes, tell me" },
  "loan.no": { hinglish: "Nahi chahiye", hi: "नहीं चाहिए", en: "Not interested" },
  apply: { hinglish: "Apply karein", hi: "आवेदन करें", en: "Apply" },
  "check.all": { hinglish: "Sab check karein", hi: "सब जाँचें", en: "Check everything" },
  pulse: { hinglish: "Aaj ka hisaab", hi: "आज का हिसाब", en: "Morning pulse" },
  advice: { hinglish: "Tyohaar salah", hi: "त्योहार सलाह", en: "Festival tips" },
  offline: { hinglish: "Backend se connection nahi hai", hi: "बैकएंड से कनेक्शन नहीं है", en: "Backend not reachable" },
  send: { hinglish: "Bhejein", hi: "भेजें", en: "Send" },
  elder: { hinglish: "Bade akshar", hi: "बड़े अक्षर", en: "Elder mode" },
  lowdata: { hinglish: "Kam data", hi: "कम डेटा", en: "Low data" },
  clear: { hinglish: "Chat saaf karein", hi: "चैट साफ़ करें", en: "Clear chat" },
  "how.known": { hinglish: "kaise pata chala?", hi: "कैसे पता चला?", en: "how do we know?" },
  "type.instead": { hinglish: "Type kar dijiye, ya neeche se chuniye", hi: "लिख दीजिए, या नीचे से चुनिए", en: "Type it, or pick a phrase below" },
  "audio.unavailable": { hinglish: "Audio uplabdh nahi", hi: "ऑडियो उपलब्ध नहीं", en: "Audio unavailable" },

  // Landing Page Copy
  "landing.hero.title": {
    hinglish: "A chatbot answers questions. A teammate closes the loop.",
    hi: "चैटबॉट सिर्फ सवाल सुनता है, सारथी समाधान तक साथ निभाता है।",
    en: "A chatbot answers questions. A teammate closes the loop.",
  },
  "landing.hero.sub": {
    hinglish: "Bharat ke vyapariyon aur yatriyon ke liye banaya gaya voice-first AI sahayak. Soundbox, Phone aur Ops Console me sampoorna swachh sahyog.",
    hi: "भारत के व्यापारियों और यात्रियों के लिए समर्पित वॉइस-फर्स्ट एआई साथी। साउंडबॉक्स, फ़ोन और कन्सोल में पारदर्शी और प्रामाणिक कार्यप्रणाली।",
    en: "An autonomous, voice-first AI teammate tailored for Indian merchants and travellers. Seamlessly integrated across Soundbox, Mobile, and Ops Console.",
  },
  "landing.hero.cta.settlement": {
    hinglish: "Check my settlement",
    hi: "मेरा सेटलमेंट जाँचें",
    en: "Check my settlement",
  },
  "landing.hero.cta.voice": {
    hinglish: "Talk in Hindi 🎙️",
    hi: "हिंदी में बात करें 🎙️",
    en: "Talk in Hindi 🎙️",
  },
  "landing.hero.cta.try": {
    hinglish: "Try Saarthi",
    hi: "सारथी आज़माएँ",
    en: "Try Saarthi",
  },
  "landing.badge.humanApproval": {
    hinglish: "Human approval on money",
    hi: "पैसे के लेन-देन पर मानवीय मंज़ूरी",
    en: "Human approval on money",
  },
  "landing.badge.auditLog": {
    hinglish: "Tamper-evident audit chain",
    hi: "सुरक्षित ऑडिट लॉग चेन",
    en: "Tamper-evident audit chain",
  },
  "landing.badge.killSwitch": {
    hinglish: "Instant kill switch",
    hi: "त्वरित किल स्विच नियंत्रण",
    en: "Instant kill switch",
  },
  "landing.badge.onDemand": {
    hinglish: "Strictly On-Demand · No background scanning",
    hi: "केवल माँग पर सक्रिय · पृष्ठभूमि में कोई ट्रैकिंग नहीं",
    en: "Strictly On-Demand · Zero background scanning",
  },
  "landing.problem.title": {
    hinglish: "Why traditional chatbots fail in Bharat",
    hi: "पारंपरिक चैटबॉट भारत में क्यों असफल होते हैं?",
    en: "Why traditional chatbots fail in Bharat",
  },
  "landing.problem.sub": {
    hinglish: "Indian merchants don't want support tickets or scripted bots. They need instant, reliable closure.",
    hi: "भारतीय व्यापारियों को लंबे टिकट नहीं, बल्कि उनके खातों और साउंडबॉक्स का सीधा और सच्चा समाधान चाहिए।",
    en: "Merchants and travellers need actions and accountable resolution, not canned replies and endless tickets.",
  },
  "landing.problem.botTitle": {
    hinglish: "Traditional Chatbot",
    hi: "पारंपरिक चैटबॉट",
    en: "Traditional Chatbot",
  },
  "landing.problem.botDesc": {
    hinglish: "FAQ link thrower, invents numbers, leaves tickets hanging for 48 hours, never connects to Soundbox or bank feeds.",
    hi: "केवल लिंक्स भेजना, काल्पनिक उत्तर देना, 48 घंटे तक टिकट लटकाना, और साउंडबॉक्स या बैंक से कोई तालमेल न होना।",
    en: "Passes links, invents explanations, creates lingering tickets, and cannot verify Soundbox or banking status.",
  },
  "landing.problem.saarthiTitle": {
    hinglish: "Saarthi Autonomous Teammate",
    hi: "सारथी: स्वायत्त एआई साथी",
    en: "Saarthi Autonomous Teammate",
  },
  "landing.problem.saarthiDesc": {
    hinglish: "Inspects live ledger, triggers hardware diagnostic on Soundbox, resolves zero-ticket settlement queries, and escalates with structured traces.",
    hi: "लाइव लेज़र की जाँच, साउंडबॉक्स की हार्डवेयर डायग्नोस्टिक्स, बिना टिकट सेटलमेंट स्पष्टता, और पारदर्शी मानवीय हैंडऑफ़।",
    en: "Audits live ledgers, pings hardware diagnostics, delivers zero-ticket closures, and escalates with crystal-clear traces.",
  },
  "landing.how.title": {
    hinglish: "How Saarthi Works",
    hi: "सारथी कैसे कार्य करता है?",
    en: "How Saarthi Works",
  },
  "landing.how.sub": {
    hinglish: "Five transparent steps from query to accountable resolution.",
    hi: "सवाल से लेकर समाधान तक पाँच पारदर्शी चरण।",
    en: "Five transparent steps from query to accountable resolution.",
  },
  "landing.how.step1.title": {
    hinglish: "1. Understand",
    hi: "१. समझना (Understand)",
    en: "1. Understand",
  },
  "landing.how.step1.desc": {
    hinglish: "Natural Indic voice (Hindi, Hinglish, English) parsed with zero prompt injection risks.",
    hi: "भारतीय भाषाओं (हिंदी, हिंग्लिश, अंग्रेज़ी) में बोली गई बात को सही संदर्भ और सुरक्षा के साथ समझना।",
    en: "Natural Indic voice processing with strict prompt-injection and sensitive token guards.",
  },
  "landing.how.step2.title": {
    hinglish: "2. Decide",
    hi: "२. निर्णय (Decide)",
    en: "2. Decide",
  },
  "landing.how.step2.desc": {
    hinglish: "Deterministic Tier-0 rule matching avoids unnecessary LLM cost; falls back to Gemini reasoning only when needed.",
    hi: "टियर-0 गणितीय नियमों से तेज़ और सटीक जाँच; केवल ज़रूरत पड़ने पर सुरक्षित जेमिनी रीज़निंग।",
    en: "Deterministic Tier-0 matching cuts latency and cost, invoking Gemini LLM reasoning only when required.",
  },
  "landing.how.step3.title": {
    hinglish: "3. Act",
    hi: "३. कार्य (Act)",
    en: "3. Act",
  },
  "landing.how.step3.desc": {
    hinglish: "Queries ledger, pings Soundbox over SIM/battery, and calculates un-settled balance down to the paisa.",
    hi: "खाता बही की समीक्षा, साउंडबॉक्स नेटवर्क और बैटरी की जाँच, और पैसे-पैसे का सटीक हिसाब।",
    en: "Inspects settlement ledgers, checks Soundbox connectivity, and tallies balances to the exact rupee.",
  },
  "landing.how.step4.title": {
    hinglish: "4. Escalate",
    hi: "४. हैंडऑफ़ (Escalate)",
    en: "4. Escalate",
  },
  "landing.how.step4.desc": {
    hinglish: "Whenever ambiguity or financial risk arises, hands off instantly to human ops with a one-page structured summary.",
    hi: "जटिल या संवेदनशील मामलों में तुरंत मानव ऑपरेटर को पूर्ण संदर्भ और समरी के साथ अग्रेषित करना।",
    en: "Immediately transitions ambiguous or high-risk cases to human operators with an auditable summary.",
  },
  "landing.how.step5.title": {
    hinglish: "5. Sell in context",
    hi: "५. अवसर (Sell in context)",
    en: "5. Sell in context",
  },
  "landing.how.step5.desc": {
    hinglish: "Offers working-capital credit only after solving the merchant's query, requiring explicit two-step human consent.",
    hi: "व्यापारी की समस्या हल होने के बाद ही वर्किंग कैपिटल लोन का पारदर्शी प्रस्ताव, पूर्ण सहमति के साथ।",
    en: "Contextual working capital offers surfaced only after resolution, requiring explicit merchant consent.",
  },
  "landing.care.title": {
    hinglish: "Saarthi Care",
    hi: "सारथी केयर (व्यापारी मित्र)",
    en: "Saarthi Care",
  },
  "landing.care.desc": {
    hinglish: "For Ramesh and 10M+ kirana store owners. Settlement breakdown, Soundbox network test, zero-ticket dispute explanation, and consent-first credit.",
    hi: "रमेश और देश भर के लाखों किराना दुकानदारों के लिए। सेटलमेंट का तुरंत हिसाब, साउंडबॉक्स का हाल और सुरक्षित क्रेडिट सुविधा।",
    en: "Proactive merchant support: settlement reconciliation, device telemetry diagnostics, dispute explanations, and consent-first credit.",
  },
  "landing.care.tag": {
    hinglish: "Merchant Ecosystem",
    hi: "व्यापारी समाधान",
    en: "Merchant Ecosystem",
  },
  "landing.care.cta": {
    hinglish: "Open Merchant Chat",
    hi: "व्यापारी चैट खोलें",
    en: "Open Merchant Chat",
  },
  "landing.travel.title": {
    hinglish: "Saarthi Travel",
    hi: "सारथी ट्रेवल (यात्रा सहायक)",
    en: "Saarthi Travel",
  },
  "landing.travel.desc": {
    hinglish: "Autonomous flight concierge. Discovers routes, ranks by price vs duration, highlights top picks, and safely hands over to user for Review and Pay.",
    hi: "स्वायत्त यात्रा साथी। फ्लाइट्स की खोज, समय और किराये का संतुलन, और अंतिम भुगतान के लिए सुरक्षित मानवीय हैंडऑफ़।",
    en: "Autonomous flight concierge: builds route roadmaps, compares 3 ranked options, and hands over to the human to Review & Pay.",
  },
  "landing.travel.tag": {
    hinglish: "Consumer Concierge",
    hi: "उपभोक्ता यात्रा",
    en: "Consumer Concierge",
  },
  "landing.travel.cta": {
    hinglish: "Plan a Flight",
    hi: "फ्लाइट खोजें",
    en: "Plan a Flight",
  },
  "landing.voice.title": {
    hinglish: "Built for Indic Voice & Bharat Diversity",
    hi: "भारतीय आवाज़ों और भाषाओं के लिए निर्मित",
    en: "Built for Indic Voice & Bharat Diversity",
  },
  "landing.voice.sub": {
    hinglish: "Designed for Hindi, Hinglish, Marathi, and English. Large touch targets and high-contrast typography suited for elder merchants.",
    hi: "हिंदी, हिंग्लिश, मराठी और अंग्रेज़ी का सहज समर्थन। बुजुर्ग व्यापारियों के लिए सुलभ बड़े बटन और स्पष्ट अक्षर।",
    en: "Natural multilingual support with elder mode, ultra-low data friendliness, and voice-first interaction design.",
  },
  "landing.voice.tag1": {
    hinglish: "Multilingual Indic Speech",
    hi: "बहुभाषी भारतीय आवाज़",
    en: "Multilingual Indic Speech",
  },
  "landing.voice.tag2": {
    hinglish: "Elder-Friendly Mode",
    hi: "बुजुर्गों के लिए विशेष मोड",
    en: "Elder-Friendly Mode",
  },
  "landing.voice.tag3": {
    hinglish: "Offline & Low Bandwidth Ready",
    hi: "कम डेटा और ऑफ़लाइन सुलभ",
    en: "Offline & Low Bandwidth Ready",
  },
  "landing.trust.title": {
    hinglish: "Zero-Trust Security & On-Demand Guarantee",
    hi: "पूर्ण सुरक्षा और ऑन-डिमांड गारंटी",
    en: "Zero-Trust Security & On-Demand Guarantee",
  },
  "landing.trust.sub": {
    hinglish: "Saarthi operates under strict mathematical and financial guardrails. Nothing is left to hallucination.",
    hi: "सारथी कड़े गणितीय और वित्तीय नियमों के तहत काम करता है। कोई भ्रम या मनगढ़ंत आंकड़े नहीं।",
    en: "Operates under deterministic guardrails designed for zero data leakage and strict autonomy limits.",
  },
  "landing.trust.point1": {
    hinglish: "Strictly On-Demand: No background scanning, no stealth listening, runs solely when triggered.",
    hi: "पूर्णतः ऑन-डिमांड: पृष्ठभूमि में कोई ऑडियो रिकॉर्डिंग या स्कैनिंग नहीं, केवल आपके आदेश पर सक्रिय।",
    en: "Strictly On-Demand: Zero background scanning or background telemetry; runs only when triggered.",
  },
  "landing.trust.point2": {
    hinglish: "Human Approval on Money: AI never triggers payments or bookings autonomously. The user always reviews & enters UPI/PIN.",
    hi: "पैसों पर मानवीय नियंत्रण: एआई कभी खुद भुगतान या टिकट बुक नहीं करता। उपयोगकर्ता खुद पिन डालते हैं।",
    en: "Human Approval on Money: The AI never executes financial transactions autonomously. Users always pay directly.",
  },
  "landing.trust.point3": {
    hinglish: "Cryptographic Audit Chain: Every decision, tool run, and handoff is hashed into a SHA-256 tamper-evident log.",
    hi: "सुरक्षित ऑडिट चेन: प्रत्येक निर्णय और टूल रन SHA-256 हैश के साथ पारदर्शी रिकॉर्ड में दर्ज होता है।",
    en: "Cryptographic Audit Chain: Every reasoning step and tool call is sealed into a SHA-256 tamper-evident ledger.",
  },
  "landing.trust.point4": {
    hinglish: "Global Kill Switch: Ops administrators can pause autonomy in a single click, instantly routing all tasks to humans.",
    hi: "ग्लोबल किल स्विच: एडमिनिस्ट्रेटर एक क्लिक में एआई स्वायत्तता रोक सकते हैं, जिससे सारे कार्य इंसानों के पास चले जाते हैं।",
    en: "Global Kill Switch: Administrators can instantly pause AI autonomy with one toggle, rerouting all actions to humans.",
  },
  "landing.metrics.title": {
    hinglish: "Simulated Impact & System Telemetry",
    hi: "सिस्टम मेट्रिक्स और कार्यप्रणाली",
    en: "Simulated Impact & System Telemetry",
  },
  "landing.metrics.sub": {
    hinglish: "Real-time metrics fetched directly from backend `/metrics` endpoint (zero invented numbers).",
    hi: "बैकएंड `/metrics` एपीआई से प्राप्त वास्तविक समय के आंकड़े (काल्पनिक आंकड़े नहीं)।",
    en: "Real-time telemetry fetched directly from backend `/metrics` endpoint with zero invented metrics.",
  },
  "landing.metrics.disclaimer": {
    hinglish: "Data shown is simulated for hackathon evaluation and derived from backend contracts.",
    hi: "यह डेटा हैकथॉन मूल्यांकन के लिए सिम्युलेटेड है और बैकएंड अनुबंधों से प्राप्त है।",
    en: "Data shown is simulated for hackathon evaluation and sourced directly from backend contracts.",
  },
  "landing.faq.title": {
    hinglish: "Frequently Asked Questions",
    hi: "अक्सर पूछे जाने वाले सवाल",
    en: "Frequently Asked Questions",
  },
  "landing.faq.sub": {
    hinglish: "Everything you need to know about Saarthi's architecture and safety.",
    hi: "सारथी की तकनीक और सुरक्षा से जुड़ी अहम बातें।",
    en: "Everything you need to know about Saarthi's architecture and safety.",
  },
  "landing.faq.q1": {
    hinglish: "Does Saarthi ever initiate payments or debit accounts automatically?",
    hi: "क्या सारथी कभी अपने आप पैसे काट सकता है या टिकट बुक कर सकता है?",
    en: "Does Saarthi ever initiate payments or debit accounts automatically?",
  },
  "landing.faq.a1": {
    hinglish: "Never. Saarthi prepares the options, validates availability, and gives a 'Review & Pay' handover. The human must explicitly tap and approve.",
    hi: "बिल्कुल नहीं। सारथी केवल विकल्प तैयार करता है और 'देखें और भुगतान करें' स्क्रीन सौंपता है। भुगतान हमेशा इंसान ही करते हैं।",
    en: "Never. Saarthi compiles routes and breakdowns, then performs a 'Review & Pay' handover. Financial execution is strictly human.",
  },
  "landing.faq.q2": {
    hinglish: "Does the Soundbox listen to store conversations continuously?",
    hi: "क्या साउंडबॉक्स दुकान की बातें लगातार सुनता रहता है?",
    en: "Does the Soundbox listen to store conversations continuously?",
  },
  "landing.faq.a2": {
    hinglish: "No. Saarthi is strictly on-demand. Audio capture is activated only when the merchant presses a button or taps the mic.",
    hi: "नहीं। सारथी केवल ऑन-डिमांड है। माइक तभी चालू होता है जब व्यापारी बटन दबाते हैं या स्क्रीन पर टैप करते हैं।",
    en: "No. Saarthi is strictly on-demand. Microphones and audio feeds remain dormant until explicitly triggered by the user.",
  },
  "landing.faq.q3": {
    hinglish: "How does Tier-0 deterministic routing save latency and costs?",
    hi: "टियर-0 नियम कैसे समय और लागत बचाते हैं?",
    en: "How does Tier-0 deterministic routing save latency and costs?",
  },
  "landing.faq.a3": {
    hinglish: "Routine settlement checks and device health queries are answered in ~20ms by deterministic python logic, bypassing LLM API charges completely.",
    hi: "रोज़मर्रा के सेटलमेंट और साउंडबॉक्स की स्थिति मात्र 20ms में स्थानीय कोड द्वारा जांची जाती है, जिससे अनावश्यक खर्च बचता है।",
    en: "Common inquiries like settlement tallies and device battery are computed in ~20ms using local deterministic handlers, bypassing LLM costs.",
  },
  "landing.faq.q4": {
    hinglish: "What happens when an LLM hallucination or injection is detected?",
    hi: "यदि कोई दुर्भावनापूर्ण या भ्रामक इनपुट आए तो क्या होता है?",
    en: "What happens when an LLM hallucination or injection is detected?",
  },
  "landing.faq.a4": {
    hinglish: "Our Guardian agent intercepts the prompt, blocks sensitive leaks (PIN/OTP requests), and forwards the thread to Ops Console for human review.",
    hi: "गार्डियन एजेंट तुरंत उस इनपुट को रोकता है, संवेदनशील डेटा छिपाता है, और ऑपरेटर की समीक्षा के लिए टिकट बनाता है।",
    en: "The Guardian safety agent intercepts the payload, redacts sensitive requests, and escalates the interaction to human operators.",
  },
  "landing.footer.credits": {
    hinglish: "Hero visual & logo badge: User-provided Paytm ❤️ Ai sticker. Additional assets by Unsplash / Pexels.",
    hi: "हीरो और लोगो छवि: यूज़र द्वारा उपलब्ध कराया गया Paytm ❤️ Ai स्टीकर।",
    en: "Hero visual & logo badge: User-provided Paytm ❤️ Ai sticker. Additional photography via Unsplash / Pexels.",
  },
  "landing.footer.builtFor": {
    hinglish: "Built for Paytm AI Hackathon · Autonomous AI Teammates",
    hi: "पेटीएम एआई हैकथॉन के लिए निर्मित · स्वायत्त एआई साथी",
    en: "Built for Paytm AI Hackathon · Autonomous AI Teammates",
  },
};

export function t(key: Key, lang: Lang | null | undefined): string {
  const l = lang === "hi" ? "hi" : lang === "en" ? "en" : "hinglish";
  return S[key]?.[l] ?? S[key]?.en ?? key;
}

export const LANG_LABEL: Record<Lang, string> = { hi: "हिं", hinglish: "Hinglish", en: "EN", mr: "मरा" };
