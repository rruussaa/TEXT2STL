"""STL validation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import trimesh


def _empty_report(path: str) -> dict:
    return {
        "file_exists": False,
        "file_size_bytes": 0,
        "triangle_count": 0,
        "bounds_mm": [0.0, 0.0, 0.0],
        "volume_mm3": 0.0,
        "is_watertight": False,
        "fits_printer": False,
        "warnings": ["STL file is empty"],
        "path": path,
    }


def validate_stl(path: str, printer_bounds: Sequence[float] = (256, 256, 256)) -> dict:
    stl_path = Path(path)
    if not stl_path.exists():
        report = _empty_report(path)
        report["warnings"] = ["STL file does not exist"]
        return report

    file_size = stl_path.stat().st_size
    if file_size <= 0:
        return _empty_report(path)

    warnings: list[str] = []
    try:
        mesh = trimesh.load_mesh(stl_path, force="mesh")
    except Exception as exc:
        return {
            "file_exists": True,
            "file_size_bytes": file_size,
            "triangle_count": 0,
            "bounds_mm": [0.0, 0.0, 0.0],
            "volume_mm3": 0.0,
            "is_watertight": False,
            "fits_printer": False,
            "warnings": [f"Could not load STL: {exc}"],
            "path": str(stl_path),
        }

    triangle_count = int(len(getattr(mesh, "faces", [])))
    bounds_mm = [round(float(value), 3) for value in getattr(mesh, "extents", [0, 0, 0])]
    volume = float(getattr(mesh, "volume", 0.0) or 0.0)
    volume_mm3 = round(volume, 3)
    is_watertight = bool(getattr(mesh, "is_watertight", False))
    fits_printer = all(size <= bound for size, bound in zip(bounds_mm, printer_bounds))

    if triangle_count <= 0:
        warnings.append("STL file is empty")
    if not is_watertight:
        warnings.append("Mesh is not watertight")
    if not fits_printer:
        warnings.append("Model does not fit printer bounds")
    if any(0 < size < 1.0 for size in bounds_mm):
        warnings.append("Model is too small")
    if any(size > 240 for size in bounds_mm) or volume_mm3 > 0.75 * 256 * 256 * 256:
        warnings.append("Model is suspiciously large")
    if volume_mm3 <= 0:
        warnings.append("Volume is zero or negative")

    return {
        "file_exists": True,
        "file_size_bytes": file_size,
        "triangle_count": triangle_count,
        "bounds_mm": bounds_mm,
        "volume_mm3": volume_mm3,
        "is_watertight": is_watertight,
        "fits_printer": fits_printer,
        "warnings": warnings,
        "path": str(stl_path),
    }


def validation_passed(report: dict) -> bool:
    return bool(
        report.get("file_exists")
        and report.get("file_size_bytes", 0) > 0
        and report.get("triangle_count", 0) > 0
        and report.get("volume_mm3", 0) > 0
        and report.get("fits_printer")
        and not report.get("warnings")
    )

