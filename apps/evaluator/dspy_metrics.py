"""
DSPy-compatible metric functions for optimization.

These metrics evaluate the quality of DSPy predictions during optimization.
They mirror the scoring approach used in the existing evaluation harnesses.
"""
import dspy
from typing import Any, Optional


def keyword_match_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """
    Metric based on keyword matching (mirrors current evaluation).

    Checks if expected keywords appear in the prediction answer.

    Args:
        example: DSPy example with expected_content field
        prediction: DSPy prediction with answer field
        trace: Optional execution trace (not used)

    Returns:
        Score between 0.0 and 1.0
    """
    expected_keywords = example.get("expected_content", [])
    if not expected_keywords:
        return 1.0  # No expectations = pass

    answer = str(prediction.answer).lower()

    # Count matching keywords
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in answer)

    # Return ratio
    score = hits / len(expected_keywords)

    return score


def binary_keyword_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> bool:
    """
    Binary metric: pass if all keywords found, fail otherwise.

    This is useful for optimizers like BootstrapFewShot that need boolean metrics.

    Args:
        example: DSPy example with expected_content field
        prediction: DSPy prediction with answer field
        trace: Optional execution trace (not used)

    Returns:
        True if ≥80% of keywords match, False otherwise
    """
    score = keyword_match_metric(example, prediction, trace)
    return score >= 0.8  # 80% of keywords must match


def weighted_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """
    Weighted metric combining multiple factors (mirrors 3-component evaluation).

    Components:
    - Content score (keywords): 50%
    - Completeness (answer length): 30%
    - Reasoning quality: 20%

    Args:
        example: DSPy example
        prediction: DSPy prediction
        trace: Optional execution trace

    Returns:
        Weighted score between 0.0 and 1.0
    """
    # Component 1: Content score from keywords (50%)
    content_score = keyword_match_metric(example, prediction, trace)

    # Component 2: Completeness score (30%)
    answer = str(prediction.answer)
    if not answer or len(answer) < 10:
        completeness_score = 0.0
    elif "error" in answer.lower() or "cannot" in answer.lower():
        completeness_score = 0.3
    elif len(answer) < 50:
        completeness_score = 0.5
    elif len(answer) < 100:
        completeness_score = 0.75
    else:
        completeness_score = 1.0

    # Component 3: Reasoning quality (20%)
    # Check if reasoning is present and substantial
    reasoning = getattr(prediction, 'reasoning', '')
    if not reasoning:
        reasoning_score = 0.5  # No reasoning is neutral
    elif len(reasoning) < 20:
        reasoning_score = 0.6
    elif len(reasoning) < 50:
        reasoning_score = 0.8
    else:
        reasoning_score = 1.0

    # Weighted combination
    total_score = (
        content_score * 0.5 +
        completeness_score * 0.3 +
        reasoning_score * 0.2
    )

    return total_score


def strict_keyword_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """
    Strict keyword metric requiring 100% keyword match.

    Use this for questions with precise expected answers (e.g., numerical queries).

    Args:
        example: DSPy example
        prediction: DSPy prediction
        trace: Optional execution trace

    Returns:
        1.0 if all keywords match, 0.0 otherwise
    """
    score = keyword_match_metric(example, prediction, trace)
    return 1.0 if score == 1.0 else 0.0


def lenient_keyword_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> bool:
    """
    Lenient keyword metric requiring only 50% keyword match.

    Use this for broader questions where partial answers are acceptable.

    Args:
        example: DSPy example
        prediction: DSPy prediction
        trace: Optional execution trace

    Returns:
        True if ≥50% of keywords match
    """
    score = keyword_match_metric(example, prediction, trace)
    return score >= 0.5


def create_evaluation_metric(threshold: float = 0.7, use_weighted: bool = True) -> callable:
    """
    Factory function to create metric with custom threshold.

    Args:
        threshold: Minimum score to pass (0.0-1.0)
        use_weighted: Use weighted_metric vs keyword_match_metric

    Returns:
        Metric function suitable for DSPy optimization
    """
    base_metric = weighted_metric if use_weighted else keyword_match_metric

    def metric(example, prediction, trace=None):
        score = base_metric(example, prediction, trace)
        return score >= threshold

    return metric


def category_aware_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """
    Category-aware metric that adjusts scoring based on question category.

    Different categories have different difficulty levels and expectations.

    Args:
        example: DSPy example with category field
        prediction: DSPy prediction
        trace: Optional execution trace

    Returns:
        Category-adjusted score
    """
    base_score = weighted_metric(example, prediction, trace)

    category = example.get("category", "")

    # Adjust score based on category difficulty
    # Easier categories get higher thresholds
    # Harder categories get more lenient thresholds
    if category in ["property_info", "document_listing"]:
        # These are straightforward lookups - expect high accuracy
        adjustment = 1.0
    elif category in ["transactions", "compliance"]:
        # Medium difficulty - numerical or filtering queries
        adjustment = 1.0
    elif category in ["aggregations", "airbnb_monthly", "airbnb_quarterly"]:
        # Harder - requires calculation or complex filtering
        adjustment = 0.95  # Slightly more lenient
    elif category in ["governance", "formation"]:
        # Document-heavy - may have more variability
        adjustment = 0.90
    else:
        # Unknown category - neutral
        adjustment = 1.0

    return base_score * adjustment


def answer_length_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """
    Metric based on answer length appropriateness.

    Penalizes answers that are too short or excessively long.

    Args:
        example: DSPy example
        prediction: DSPy prediction
        trace: Optional execution trace

    Returns:
        Score based on answer length
    """
    answer = str(prediction.answer)
    length = len(answer)

    # Optimal length range: 100-500 characters
    if length < 50:
        return 0.3  # Too short
    elif length < 100:
        return 0.7  # Short but acceptable
    elif length <= 500:
        return 1.0  # Ideal length
    elif length <= 1000:
        return 0.9  # Long but acceptable
    else:
        return 0.7  # Too verbose


# Default metric for general use
default_metric = binary_keyword_metric


if __name__ == "__main__":
    # Test metrics with sample predictions
    print("Testing DSPy metrics...\n")

    # Create sample example
    example = dspy.Example(
        question="What properties does Poolula LLC own?",
        expected_content=["property", "address", "Montrose"],
        category="property_info"
    ).with_inputs("question")

    # Test with good prediction
    good_prediction = dspy.Prediction(
        answer="Poolula LLC owns a rental property located at 900 S 9th St, Montrose, CO 81401.",
        reasoning="Looking at the database, I found one property record with the Montrose address."
    )

    print("Good prediction:")
    print(f"  Keyword match: {keyword_match_metric(example, good_prediction):.2f}")
    print(f"  Binary metric: {binary_keyword_metric(example, good_prediction)}")
    print(f"  Weighted metric: {weighted_metric(example, good_prediction):.2f}")
    print(f"  Category-aware: {category_aware_metric(example, good_prediction):.2f}")

    # Test with poor prediction
    poor_prediction = dspy.Prediction(
        answer="I don't know.",
        reasoning="No data available."
    )

    print("\nPoor prediction:")
    print(f"  Keyword match: {keyword_match_metric(example, poor_prediction):.2f}")
    print(f"  Binary metric: {binary_keyword_metric(example, poor_prediction)}")
    print(f"  Weighted metric: {weighted_metric(example, poor_prediction):.2f}")
    print(f"  Category-aware: {category_aware_metric(example, poor_prediction):.2f}")

    # Test with partial prediction
    partial_prediction = dspy.Prediction(
        answer="There is a property in Montrose.",
        reasoning="Found property information in the database."
    )

    print("\nPartial prediction:")
    print(f"  Keyword match: {keyword_match_metric(example, partial_prediction):.2f}")
    print(f"  Binary metric: {binary_keyword_metric(example, partial_prediction)}")
    print(f"  Weighted metric: {weighted_metric(example, partial_prediction):.2f}")
    print(f"  Category-aware: {category_aware_metric(example, partial_prediction):.2f}")

    print("\n✅ Metrics test complete!")
