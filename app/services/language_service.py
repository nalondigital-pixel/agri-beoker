from app.services.profile_service import get_profile


MESSAGES = {
    "voice_not_ready": {
        "english": "🎤 Voice note received, but voice transcription is not connected yet. Please type your request for now.",
        "shona": "🎤 Voice note yatambirwa, asi system haisati yagona kuinzwisisa. Ndapota nyorai zvamunoda parizvino.",
        "ndebele": "🎤 I-voice note yamukelwe, kodwa system ayikakwazi ukuyiqonda. Sicela ubhale okufunayo okwamanje.",
    },

    "main_menu": {
        "english": "Welcome back 👋\n\nWhat do you want to do?",
        "shona": "Mauya zvakare 👋\n\nMunoda kuita chii?",
        "ndebele": "Siyakwamukela futhi 👋\n\nUfuna ukwenzani?",
    },

    "buy_prompt": {
        "english": "What do you want to buy?\n\nExample: 10 bags maize in Chegutu",
        "shona": "Munoda kutenga chii?\n\nSemuenzaniso: 10 bags maize ku Chegutu",
        "ndebele": "Ufuna ukuthenga ini?\n\nIsibonelo: 10 bags maize eChegutu",
    },

    "sell_prompt": {
        "english": "What are you selling?\n\nExample: 4 goats in Kadoma",
        "shona": "Muri kutengesa chii?\n\nSemuenzaniso: 4 mbudzi ku Kadoma",
        "ndebele": "Uthengisa ini?\n\nIsibonelo: 4 mbudzi eKadoma",
    },

    "deals_coming": {
        "english": "Deal checking is coming next. For now, wait for WhatsApp updates when buyers/sellers respond.",
        "shona": "Kuona madeals kuri kuuya. Parizvino mirirai maWhatsApp updates kana vatengi/vatengesi vapindura.",
        "ndebele": "Ukuhlola ama-deals kuyeza. Okwamanje linda amaWhatsApp updates nxa abathengi/abathengisi bephendula.",
    },

    "listing_saved_with_matches": {
        "english": """
✅ Request saved.

We found {match_count} possible match(es).
We will notify you if someone shows interest.
""",
        "shona": """
✅ Zvamakumbira zvachengetwa.

Tawana vangangowirirana newe {match_count}.
Tichakuzivisai kana munhu afarira.
""",
        "ndebele": """
✅ Isicelo sakho sigciniwe.

Sithole abangafanelana lawe abangu-{match_count}.
Sizakwazisa nxa umuntu etshengisa ukuthanda.
""",
    },

    "listing_saved_no_matches": {
        "english": """
✅ Request saved.

We do not have a matching buyer/seller right now.
We will notify you when we find one.
""",
        "shona": """
✅ Zvamakumbira zvachengetwa.

Parizvino hatina munhu anoenderana nazvo.
Tichakuzivisai kana tawana.
""",
        "ndebele": """
✅ Isicelo sakho sigciniwe.

Okwamanje asikatholi umuntu ofanelanayo.
Sizakwazisa nxa simtholile.
""",
    },

    "buyer_match_alert": {
        "english": """
🚜 AGRI MATCH ALERT 🚜

Commodity: {commodity}
Quantity: {quantity}
Seller Location: {location}
Distance Match: {distance_match}
Match Score: {match_score}%
Why: {match_reasons}

Seller Trust: {seller_trust}

Choose an option below.
""",
        "shona": """
🚜 AGRI MATCH ALERT 🚜

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}
Kuswedera kwenzvimbo: {distance_match}
Match Score: {match_score}%
Chikonzero: {match_reasons}

Trust: {seller_trust}

Sarudzai pazasi.
""",
        "ndebele": """
🚜 AGRI MATCH ALERT 🚜

Impahla: {commodity}
Inani: {quantity}
Indawo: {location}
Ukusondelana kwendawo: {distance_match}
Match Score: {match_score}%
Isizatho: {match_reasons}

Trust: {seller_trust}

Khetha ngezansi.
""",
    },

    "buyer_interest_received": {
        "english": """
✅ Interest received.

We are asking the other person to approve contact sharing.
""",
        "shona": """
✅ Tawana kuti munofarira.

Tiri kukumbira mumwe munhu abvumire kugoverana manumber.
""",
        "ndebele": """
✅ Sithole ukuthi uyafuna.

Sicela omunye umuntu avume ukwabelana ngezinombolo.
""",
    },

    "buyer_declined": {
        "english": "✅ Noted. We will not continue with this match.",
        "shona": "✅ Zvanzwisiswa. Hatichazoendereri mberi ne match iyi.",
        "ndebele": "✅ Kuzwakale. Asisayikuqhubeka ngale match.",
    },

    "seller_approval_prompt": {
        "english": """
📢 MATCH INTEREST

Person interested: {buyer_name}
Commodity: {commodity}
Quantity: {quantity}
Location: {location}

What do you want to do?
""",
        "shona": """
📢 MUNHU AFARIRA

Munhu afarira: {buyer_name}
Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Munoda kuita sei?
""",
        "ndebele": """
📢 UMUNTU UYAFUNA

Ofunayo: {buyer_name}
Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Ufuna ukwenzani?
""",
    },

    "deal_approved_buyer": {
        "english": """
✅ DEAL APPROVED

Contact: {seller_name}
Phone: {seller_phone}

Commodity: {commodity}
Quantity: {quantity}
Location: {location}

Please contact them to arrange payment/collection.
""",
        "shona": """
✅ DEAL YABVUMIRWA

Munhu: {seller_name}
Nhamba: {seller_phone}

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Batai munhu uyu kuti muronge kubhadhara/kutora.
""",
        "ndebele": """
✅ IDEAL IVUNYIWE

Umuntu: {seller_name}
Inombolo: {seller_phone}

Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Xhumana laye ukuze lihlele ukukhokha/ukulanda.
""",
    },

    "contact_shared_seller": {
        "english": """
✅ CONTACT SHARED

Contact: {buyer_name}
Phone: {buyer_phone}

Commodity: {commodity}
Quantity: {quantity}
Location: {location}

Please contact them to complete the deal.
""",
        "shona": """
✅ MANUMBER AGOVERANWA

Munhu: {buyer_name}
Nhamba: {buyer_phone}

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Batai munhu uyu kuti mupedzise deal.
""",
        "ndebele": """
✅ IZINOMBOLO ZABELWE

Umuntu: {buyer_name}
Inombolo: {buyer_phone}

Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Xhumana laye ukuze liqedele i-deal.
""",
    },

    "seller_waiting_better_offer": {
        "english": "✅ Noted. We will keep this request active and look for a better match.",
        "shona": "✅ Zvanzwisiswa. Tichasiya chikumbiro ichi chiripo tichitsvaga match iri nani.",
        "ndebele": "✅ Kuzwakale. Sizagcina isicelo lesi sikhona sisadinga match engcono.",
    },

    "seller_cancelled_deal": {
        "english": "❌ Deal cancelled. We will not share contacts.",
        "shona": "❌ Deal yakanzurwa. Hatichagoverani manumber.",
        "ndebele": "❌ I-deal ikhanseliwe. Asisayabelani ngezinombolo.",
    },

    "daily_limit_reached": {
        "english": "You have reached today's request limit. Please try again tomorrow.",
        "shona": "Masvika palimit yezvikumbiro zvanhasi. Edzai zvakare mangwana.",
        "ndebele": "Usufike kulimit yezicelo zanamuhla. Zama futhi kusasa.",
    },

    "invalid_report_format": {
        "english": "Invalid report format. Use: REPORT 263XXXXXXXX reason",
        "shona": "Report haina kunyorwa zvakanaka. Shandisa: REPORT 263XXXXXXXX chikonzero",
        "ndebele": "I-report ayibhalwanga kuhle. Sebenzisa: REPORT 263XXXXXXXX isizatho",
    },

    "report_received": {
        "english": "✅ Report received. Our team will review this user.",
        "shona": "✅ Report yatambirwa. Team yedu ichaongorora munhu uyu.",
        "ndebele": "✅ I-report yamukelwe. Ithimba lethu lizahlola lomuntu.",
    },

    "feedback_prompt": {
        "english": """
Did you finish the trade for {commodity}? 🧐

Choose below:
✅ Successful
⚠️ Problem
""",
        "shona": """
Makapedza trade ye {commodity} here? 🧐

Sarudzai pazasi:
✅ Yakabudirira
⚠️ Pane problem
""",
        "ndebele": """
Liqedile i-trade ye {commodity}? 🧐

Khetha ngezansi:
✅ Iphumelele
⚠️ Kube leproblem
""",
    },

    "feedback_invalid": {
        "english": "Please choose Successful or Problem.",
        "shona": "Ndapota sarudzai Yakabudirira kana Problem.",
        "ndebele": "Sicela ukhethe Iphumelele kumbe Problem.",
    },

    "feedback_success": {
        "english": "✅ Thank you. Trust points updated for this successful trade.",
        "shona": "✅ Tatenda. Trust points dzawedzerwa nekuda kwe trade yabudirira.",
        "ndebele": "✅ Siyabonga. Ama trust points engeziwe ngenxa ye trade ephumelele.",
    },

    "feedback_reported": {
        "english": "⚠️ Report received. We will review this before affecting anyone’s reputation.",
        "shona": "⚠️ Report yatambirwa. Tichatanga taona nyaya iyi tisati tachinja reputation yemunhu.",
        "ndebele": "⚠️ I-report yamukelwe. Sizaqala siyihlole singakathinti reputation yomuntu.",
    },

    "feedback_deal_not_found": {
        "english": "Deal not found.",
        "shona": "Deal haina kuwanikwa.",
        "ndebele": "I-deal ayitholakalanga.",
    },
}


def get_user_language(phone: str) -> str:
    profile = get_profile(phone)

    if profile and profile.get("language"):
        return profile["language"]

    return "english"


def translate(phone: str, key: str, **kwargs) -> str:
    language = get_user_language(phone)

    template = (
        MESSAGES.get(key, {}).get(language)
        or MESSAGES.get(key, {}).get("english")
        or key
    )

    try:
        return template.format(**kwargs)
    except Exception:
        return template