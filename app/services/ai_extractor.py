from app.services.normalization_service import (
    fallback_extract_market_data,
    apply_normalization,
)


def extract_market_data(message: str, reporter_phone: str | None = None):
    extracted = fallback_extract_market_data(
        message,
        reporter_phone=reporter_phone,
    )

    extracted = apply_normalization(
        extracted,
        message,
        reporter_phone=reporter_phone,
    )

    print("Fallback Extracted:", extracted)

    return extracted