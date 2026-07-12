from backend.training.calibrate_threshold import (
    build_threshold_results,
    meets_operating_constraints,
    select_deployment_threshold,
)


def test_threshold_selection_requires_both_operating_constraints():
    results = build_threshold_results(
        answerable_scores=[0.80, 0.85, 0.90, 0.95, 0.99],
        unanswerable_scores=[0.05, 0.10, 0.15, 0.20, 0.25],
    )

    selected, status = select_deployment_threshold(results)

    assert status == "validated_on_validation_split"
    assert selected is not None
    assert selected["false_refusal_rate"] <= 0.20
    assert selected["unsafe_answer_rate"] <= 0.10


def test_threshold_selection_refuses_to_recommend_an_all_refusal_policy():
    results = build_threshold_results(
        answerable_scores=[0.10, 0.20, 0.30],
        unanswerable_scores=[0.20, 0.30, 0.40],
    )

    selected, status = select_deployment_threshold(results)

    assert selected is None
    assert status == "no_threshold_meets_operating_constraints"


def test_operating_constraints_must_hold_on_the_holdout_metrics():
    assert meets_operating_constraints(
        {"false_refusal_rate": 0.20, "unsafe_answer_rate": 0.10}
    )
    assert not meets_operating_constraints(
        {"false_refusal_rate": 0.21, "unsafe_answer_rate": 0.0}
    )
    assert not meets_operating_constraints(
        {"false_refusal_rate": 0.0, "unsafe_answer_rate": 0.11}
    )
