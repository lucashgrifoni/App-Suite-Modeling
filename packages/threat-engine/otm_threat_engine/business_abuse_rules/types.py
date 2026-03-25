from __future__ import annotations

from collections.abc import Callable

from otm_core_schema import StrideCategory

AddBusinessHeuristic = Callable[
    ...,
    None,
]


def add_call(
    add: AddBusinessHeuristic,
    *,
    hid: str,
    title: str,
    description: str,
    stride: StrideCategory,
    likelihood: int,
    impact: int,
    target_component_id: str | None = None,
    target_data_flow_id: str | None = None,
    target_asset_id: str | None = None,
) -> None:
    add(
        hid=hid,
        title=title,
        description=description,
        stride=stride,
        likelihood=likelihood,
        impact=impact,
        target_component_id=target_component_id,
        target_data_flow_id=target_data_flow_id,
        target_asset_id=target_asset_id,
    )
