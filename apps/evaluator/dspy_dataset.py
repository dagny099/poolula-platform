"""
Convert Poolula evaluation dataset to DSPy format.
"""
import json
from pathlib import Path
from typing import List, Tuple
import dspy


def load_dspy_examples(
    jsonl_path: str = "apps/evaluator/poolula_eval_set.jsonl",
    split_ratio: float = 0.75
) -> Tuple[List[dspy.Example], List[dspy.Example]]:
    """
    Load evaluation questions and convert to DSPy examples.

    Args:
        jsonl_path: Path to JSONL file with questions
        split_ratio: Train/dev split ratio (0.75 = 75% train, 25% dev)

    Returns:
        (trainset, devset) tuple of DSPy examples
    """
    examples = []

    with open(jsonl_path) as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)

            # Create DSPy Example
            # Note: We don't have ground truth answers, so we use expected_content as hints
            example = dspy.Example(
                question=item["question"],
                # For optimization, DSPy needs answer field
                # Since we don't have ground truth answers, use expected keywords as proxy
                answer=" ".join(item.get("expected_content", [])),
                # Keep metadata for evaluation
                expected_tools=item.get("expected_tools", []),
                expected_content=item.get("expected_content", []),
                category=item.get("category", ""),
                type=item.get("type", "")
            ).with_inputs("question")  # Mark question as input field

            examples.append(example)

    # Split into train/dev
    split_idx = int(len(examples) * split_ratio)
    trainset = examples[:split_idx]
    devset = examples[split_idx:]

    print(f"Loaded {len(examples)} examples:")
    print(f"  Train: {len(trainset)}")
    print(f"  Dev: {len(devset)}")

    return trainset, devset


def create_few_shot_examples() -> List[dspy.Example]:
    """
    Create high-quality hand-crafted examples for few-shot prompting.

    These are used as demonstrations in prompts to guide the model.
    """
    examples = [
        dspy.Example(
            question="What properties does Poolula LLC own?",
            answer="Poolula LLC owns one rental property located at 900 S 9th St, Montrose, CO 81401. This property was acquired on April 15, 2024 with an initial basis of $336,000."
        ).with_inputs("question"),

        dspy.Example(
            question="What was my rental income in July 2025?",
            answer="Your rental income in July 2025 was $3,960.10 from Airbnb reservations. This represents the gross earnings from 15 bookings during that month."
        ).with_inputs("question"),

        dspy.Example(
            question="What insurance policies does Poolula have?",
            answer="Poolula LLC has a Travelers Insurance landlord policy covering the rental property. The policy was renewed effective May 5th, 2025 and renews annually each May."
        ).with_inputs("question"),

        dspy.Example(
            question="What is the business purpose of Poolula LLC?",
            answer="Poolula LLC is a Colorado limited liability company formed for the purpose of acquiring, owning, managing, and operating real property for investment purposes. The company may engage in any lawful business activity."
        ).with_inputs("question"),
    ]

    return examples


def load_airbnb_examples(
    jsonl_path: str = "apps/evaluator/airbnb_eval_set.jsonl",
    split_ratio: float = 0.8
) -> Tuple[List[dspy.Example], List[dspy.Example]]:
    """
    Load Airbnb-specific evaluation questions with ground truth.

    The Airbnb evaluator has CSV-backed ground truth, so these examples
    are more reliable for optimization.

    Args:
        jsonl_path: Path to Airbnb JSONL file
        split_ratio: Train/dev split ratio

    Returns:
        (trainset, devset) tuple
    """
    examples = []

    try:
        with open(jsonl_path) as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)

                # Airbnb questions have validation parameters
                # We can use these to create more specific examples
                example = dspy.Example(
                    question=item["question"],
                    answer=" ".join(item.get("expected_content", [])),
                    expected_tools=item.get("expected_tools", []),
                    expected_content=item.get("expected_content", []),
                    category=item.get("category", ""),
                    validation_type=item.get("validation_type", ""),
                    validation_params=item.get("validation_params", {})
                ).with_inputs("question")

                examples.append(example)

        split_idx = int(len(examples) * split_ratio)
        trainset = examples[:split_idx]
        devset = examples[split_idx:]

        print(f"Loaded {len(examples)} Airbnb examples:")
        print(f"  Train: {len(trainset)}")
        print(f"  Dev: {len(devset)}")

        return trainset, devset

    except FileNotFoundError:
        print(f"Warning: {jsonl_path} not found, returning empty sets")
        return [], []


def combine_datasets(
    poolula_train: List[dspy.Example],
    poolula_dev: List[dspy.Example],
    airbnb_train: List[dspy.Example],
    airbnb_dev: List[dspy.Example]
) -> Tuple[List[dspy.Example], List[dspy.Example]]:
    """
    Combine Poolula and Airbnb datasets for comprehensive training.

    Args:
        poolula_train, poolula_dev: Poolula examples
        airbnb_train, airbnb_dev: Airbnb examples

    Returns:
        (combined_train, combined_dev) tuple
    """
    combined_train = poolula_train + airbnb_train
    combined_dev = poolula_dev + airbnb_dev

    print(f"\nCombined dataset:")
    print(f"  Train: {len(combined_train)} ({len(poolula_train)} Poolula + {len(airbnb_train)} Airbnb)")
    print(f"  Dev: {len(combined_dev)} ({len(poolula_dev)} Poolula + {len(airbnb_dev)} Airbnb)")

    return combined_train, combined_dev


if __name__ == "__main__":
    # Test loading
    print("Testing dataset loading...\n")

    # Load Poolula questions
    print("Loading Poolula evaluation set:")
    poolula_train, poolula_dev = load_dspy_examples()

    print("\nSample Poolula question:")
    print(f"  Q: {poolula_train[0].question}")
    print(f"  Expected keywords: {poolula_train[0].expected_content}")
    print(f"  Category: {poolula_train[0].category}")

    # Load Airbnb questions
    print("\n" + "="*60)
    print("Loading Airbnb evaluation set:")
    airbnb_train, airbnb_dev = load_airbnb_examples()

    if airbnb_train:
        print("\nSample Airbnb question:")
        print(f"  Q: {airbnb_train[0].question}")
        print(f"  Expected keywords: {airbnb_train[0].expected_content}")

    # Load few-shot examples
    print("\n" + "="*60)
    print("Hand-crafted few-shot examples:")
    few_shot = create_few_shot_examples()
    print(f"  Count: {len(few_shot)}")
    for i, ex in enumerate(few_shot, 1):
        print(f"\n  [{i}] Q: {ex.question}")
        print(f"      A: {ex.answer[:80]}...")

    print("\n✅ Dataset loading test complete!")
