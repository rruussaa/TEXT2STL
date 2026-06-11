"""Validated schemas used by the stable pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NamePlateSpec(BaseModel):
    object_type: Literal["name_plate"] = "name_plate"

    width_mm: float = Field(default=100, ge=20, le=220)
    height_mm: float = Field(default=35, ge=10, le=120)
    thickness_mm: float = Field(default=3, ge=1, le=10)

    text: str = Field(default="AI LAB", min_length=1, max_length=40)

    text_depth_mm: float = Field(default=0.8, ge=0.2, le=3)

    raised_text: bool = True

    rounded_corners: bool = True
    corner_radius_mm: float = Field(default=2, ge=0, le=10)

    mounting_holes: int = Field(default=0, ge=0, le=4)
    hole_diameter_mm: float = Field(default=4, ge=2, le=8)


def validate_name_plate_spec(data: dict[str, Any]) -> NamePlateSpec:
    if hasattr(NamePlateSpec, "model_validate"):
        return NamePlateSpec.model_validate(data)
    return NamePlateSpec.parse_obj(data)


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

