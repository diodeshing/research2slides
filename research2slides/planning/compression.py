from __future__ import annotations

from research2slides.exceptions import PlanningError
from research2slides.models import CompressionInfo, PresentationPlan


ROLE_GROUPS = (
    {"problem"},
    {"core_insight", "contributions"},
    {"method_overview", "method_component"},
    {"experiments", "ablation", "analysis"},
    {"limitations"},
    {"conclusion", "takeaway"},
)


def compress_plan(plan: PresentationPlan, time_budget_seconds: int) -> PresentationPlan:
    if time_budget_seconds <= 0:
        raise PlanningError("time budget must be positive")
    if plan.estimated_total_seconds <= time_budget_seconds:
        return plan.model_copy(
            update={
                "compression": CompressionInfo(
                    time_budget_seconds=time_budget_seconds,
                    omitted_unit_ids=[],
                )
            },
            deep=True,
        )

    required_ids: set[str] = set()
    for group in ROLE_GROUPS:
        candidates = [unit for unit in plan.units if unit.role in group]
        if candidates:
            required_ids.add(max(candidates, key=lambda unit: (unit.importance, -unit.order)).unit_id)
    if not required_ids:
        required_ids.add(max(plan.units, key=lambda unit: (unit.importance, -unit.order)).unit_id)
    required = [unit for unit in plan.units if unit.unit_id in required_ids]
    required_seconds = sum(unit.estimated_seconds for unit in required)
    if required_seconds > time_budget_seconds:
        raise PlanningError(
            f"Time budget {time_budget_seconds}s is below the {required_seconds}s narrative minimum"
        )

    selected_ids = set(required_ids)
    remaining = sorted(
        (unit for unit in plan.units if unit.unit_id not in selected_ids),
        key=lambda unit: (-unit.importance, unit.order),
    )
    total = required_seconds
    for unit in remaining:
        if total + unit.estimated_seconds <= time_budget_seconds:
            selected_ids.add(unit.unit_id)
            total += unit.estimated_seconds

    selected = [unit.model_copy(deep=True) for unit in plan.units if unit.unit_id in selected_ids]
    for order, unit in enumerate(selected, start=1):
        unit.order = order
    omitted = [unit.unit_id for unit in plan.units if unit.unit_id not in selected_ids]
    return plan.model_copy(
        update={
            "units": selected,
            "estimated_total_seconds": sum(unit.estimated_seconds for unit in selected),
            "compression": CompressionInfo(
                time_budget_seconds=time_budget_seconds,
                omitted_unit_ids=omitted,
            ),
        },
        deep=True,
    )
