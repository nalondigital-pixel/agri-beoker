from app.services.normalization_service import (
    fallback_extract_market_data,
    apply_normalization,
)


def extract_market_data(message: str):
    """
    Temporary fallback-only extractor to avoid AI rate limits during testing.
    """

    extracted = fallback_extract_market_data(message)
    extracted = apply_normalization(extracted, message)

    print("Fallback Extracted:", extracted)

    return extracted