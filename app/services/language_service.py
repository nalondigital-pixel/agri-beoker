from app.services.profile_service import get_profile


MESSAGES = {
    "listing_saved_with_matches": {
        "english": """
✅ Listing saved.

We found {match_count} possible buyer(s).
We will notify you if a buyer shows interest.
""",
        "shona": """
✅ Listing yachengetwa.

Tawana vangangotenga {match_count}.
Tichakuzivisai kana mutengi afarira.
""",
        "ndebele": """
✅ I-listing igciniwe.

Sithole abangathenga abangu-{match_count}.
Sizakwazisa nxa umthengi etshengisa ukuthanda.
""",
    },

    "listing_saved_no_matches": {
        "english": """
✅ Listing saved.

We do not have a matching buyer right now.
We will notify you when we find one.
""",
        "shona": """
✅ Listing yachengetwa.

Parizvino hatina mutengi anoenderana nayo.
Tichakuzivisai kana tawana.
""",
        "ndebele": """
✅ I-listing igciniwe.

Okwamanje asikatholi umthengi ofanelanayo.
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

Reply:
✅ 1 = Interested
❌ 2 = Not interested
""",
        "shona": """
🚜 AGRI MATCH ALERT 🚜

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo yemutengesi: {location}
Kuswedera kwenzvimbo: {distance_match}

Trust yemutengesi: {seller_trust}

Pindura:
✅ 1 = Ndinofarira
❌ 2 = Handifariri
""",
        "ndebele": """
🚜 AGRI MATCH ALERT 🚜

Impahla: {commodity}
Inani: {quantity}
Indawo yomthengisi: {location}
Ukusondelana kwendawo: {distance_match}

Trust yomthengisi: {seller_trust}

Phendula:
✅ 1 = Ngiyafuna
❌ 2 = Angifuni
""",
    },

    "buyer_interest_received": {
        "english": """
✅ Interest received.

We are asking the seller to approve contact sharing.
""",
        "shona": """
✅ Tawana kuti munofarira.

Tiri kukumbira mutengesi abvumire kugoverana manumber.
""",
        "ndebele": """
✅ Sithole ukuthi uyafuna.

Sicela umthengisi avume ukwabelana ngezinombolo.
""",
    },

    "seller_approval_prompt": {
        "english": """
📢 BUYER INTEREST

Buyer: {buyer_name}
Commodity: {commodity}
Quantity: {quantity}
Location: {location}

What do you want to do?

✅ 1 = Share contacts now
⏳ 2 = Wait for better offer
❌ 3 = Cancel this deal
""",
        "shona": """
📢 MUTENGI AFARIRA

Mutengi: {buyer_name}
Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Munoda kuita sei?

✅ 1 = Goveranai manumber izvozvi
⏳ 2 = Mirira offer iri nani
❌ 3 = Kanzura deal iyi
""",
        "ndebele": """
📢 UMTHENGI UYAFUNA

Umthengi: {buyer_name}
Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Ufuna ukwenzani?

✅ 1 = Yabelana ngezinombolo khathesi
⏳ 2 = Linda enye i-offer engcono
❌ 3 = Khansela le deal
""",
    },

    "deal_approved_buyer": {
        "english": """
✅ DEAL APPROVED

Seller: {seller_name}
Seller contact: {seller_phone}

Commodity: {commodity}
Quantity: {quantity}
Location: {location}

Please contact the seller to arrange payment/collection.
""",
        "shona": """
✅ DEAL YABVUMIRWA

Mutengesi: {seller_name}
Nhamba yemutengesi: {seller_phone}

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Batai mutengesi kuti muronge kubhadhara/kutora.
""",
        "ndebele": """
✅ IDEAL IVUNYIWE

Umthengisi: {seller_name}
Inombolo yomthengisi: {seller_phone}

Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Xhumana lomthengisi ukuze lihlele ukukhokha/ukulanda.
""",
    },

    "contact_shared_seller": {
        "english": """
✅ CONTACT SHARED

Buyer: {buyer_name}
Buyer contact: {buyer_phone}

Commodity: {commodity}
Quantity: {quantity}
Location: {location}

Please contact the buyer to complete the deal.
""",
        "shona": """
✅ MANUMBER AGOVERANWA

Mutengi: {buyer_name}
Nhamba yemutengi: {buyer_phone}

Chinhu: {commodity}
Huwandu: {quantity}
Nzvimbo: {location}

Batai mutengi kuti mupedzise deal.
""",
        "ndebele": """
✅ IZINOMBOLO ZABELWE

Umthengi: {buyer_name}
Inombolo yomthengi: {buyer_phone}

Impahla: {commodity}
Inani: {quantity}
Indawo: {location}

Xhumana lomthengi ukuze liqedele i-deal.
""",
    },

    "seller_waiting_better_offer": {
        "english": "✅ Noted. We will keep this listing active and look for a better match.",
        "shona": "✅ Zvanzwisiswa. Tichasiya listing iyi iripo tichitsvaga mutengi ari nani.",
        "ndebele": "✅ Kuzwakale. Sizagcina i-listing ikhona sisadinga umthengi ongcono.",
    },

    "seller_cancelled_deal": {
        "english": "❌ Deal cancelled. We will not share contacts.",
        "shona": "❌ Deal yakanzurwa. Hatichagoverani manumber.",
        "ndebele": "❌ I-deal ikhanseliwe. Asisayabelani ngezinombolo.",
    },

    "daily_limit_reached": {
        "english": "You have reached today's listing limit. Please try again tomorrow.",
        "shona": "Masvika palimit yemalisting yanhasi. Edzai zvakare mangwana.",
        "ndebele": "Usufike kulimit yama-listing yanamuhla. Zama futhi kusasa.",
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

Press:
✅ 1 = Yes, trade was successful
⚠️ 2 = No, the other person did not come
""",
        "shona": """
Makapedza trade ye {commodity} here? 🧐

Dzvanyai:
✅ 1 = Ehe, trade yakabudirira
⚠️ 2 = Kwete, mumwe munhu haana kuuya
""",
        "ndebele": """
Liqedile i-trade ye {commodity}? 🧐

Cindezela:
✅ 1 = Yebo, i-trade iphumelele
⚠️ 2 = Hatshi, omunye umuntu kafikanga
""",
    },

    "feedback_invalid": {
        "english": "Please reply 1 if trade was successful, or 2 if the other person did not come.",
        "shona": "Pindurai 1 kana trade yakabudirira, kana 2 kana mumwe munhu asina kuuya.",
        "ndebele": "Phendula 1 nxa i-trade iphumelele, kumbe 2 nxa omunye umuntu engafikanga.",
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