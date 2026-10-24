from services.peer_relevance_service import (
    apply_peer_relevance_to_benchmarks,
    generate_peer_relevance,
)
from services.peer_valuation_service import generate_peer_benchmarks
from services.valuation_quality_adjustment_service import (
    apply_quality_adjustment_to_benchmarks,
    calculate_quality_adjustment,
)
from services.valuation_v4_service import generate_valuation_v4


def generate_valuation_v43(
    symbol,
    company_data,
):
    """
    Fully orchestrated Valuation V4.3 pipeline.

    Pipeline:
        Raw peer benchmarks
            ↓
        Quality adjustment
            ↓
        Automatic peer relevance
            ↓
        Relevance-adjusted benchmark reliability
            ↓
        Multi-method V4 valuation

    Peer quality changes benchmark multiples.

    Peer relevance changes benchmark reliability.

    These concepts are deliberately kept separate.
    """

    if not isinstance(company_data, dict):
        return {
            "status": "UNAVAILABLE",
            "message": "Invalid company data.",
        }

    # ======================================================
    # 1. RAW PEER BENCHMARKS
    # ======================================================

    peer_benchmarks = generate_peer_benchmarks(symbol)

    if peer_benchmarks.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "message": peer_benchmarks.get(
                "message",
                "Peer benchmarks unavailable.",
            ),
            "peer_benchmarks": peer_benchmarks,
        }

    # ======================================================
    # 2. QUALITY ADJUSTMENT
    # ======================================================

    quality_result = calculate_quality_adjustment(
        company_data,
        peer_benchmarks,
    )

    quality_adjusted_benchmarks = apply_quality_adjustment_to_benchmarks(
        peer_benchmarks,
        quality_result,
    )

    # ======================================================
    # 3. AUTOMATIC PEER RELEVANCE
    # ======================================================

    peer_relevance = generate_peer_relevance(
        symbol,
        company_data,
        peer_benchmarks,
    )

    # ======================================================
    # 4. RELEVANCE-ADJUSTED RELIABILITY
    # ======================================================

    final_benchmarks = apply_peer_relevance_to_benchmarks(
        quality_adjusted_benchmarks,
        peer_relevance,
    )

    # ======================================================
    # 5. MULTI-METHOD VALUATION
    # ======================================================

    valuation = generate_valuation_v4(
        company_data,
        final_benchmarks,
    )

    # ======================================================
    # 6. COMPLETE V4.3 RESULT
    # ======================================================

    return {
        "status": valuation.get(
            "status",
            "UNAVAILABLE",
        ),
        "version": "V4.3",
        "symbol": str(symbol or "").strip().upper(),
        "valuation": valuation,
        "peer_relevance": peer_relevance,
        "quality_adjustment": quality_result,
        "raw_peer_benchmarks": peer_benchmarks,
        "quality_adjusted_benchmarks": (quality_adjusted_benchmarks),
        "final_benchmarks": final_benchmarks,
    }
