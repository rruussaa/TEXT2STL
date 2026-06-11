"""Local STL fallbacks for demo machines without CadQuery installed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import trimesh


def cadquery_available() -> bool:
    return importlib.util.find_spec("cadquery") is not None


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(center)
    return mesh


def _tube(
    outer_radius: float,
    inner_radius: float,
    height: float,
    center: tuple[float, float, float],
    sections: int = 48,
) -> trimesh.Trimesh:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    z0 = -height / 2
    z1 = height / 2

    for z in (z0, z1):
        for radius in (outer_radius, inner_radius):
            for index in range(sections):
                angle = 2 * np.pi * index / sections
                vertices.append((radius * np.cos(angle), radius * np.sin(angle), z))

    outer_bottom = 0
    inner_bottom = sections
    outer_top = sections * 2
    inner_top = sections * 3

    for index in range(sections):
        next_index = (index + 1) % sections

        ob0 = outer_bottom + index
        ob1 = outer_bottom + next_index
        ib0 = inner_bottom + index
        ib1 = inner_bottom + next_index
        ot0 = outer_top + index
        ot1 = outer_top + next_index
        it0 = inner_top + index
        it1 = inner_top + next_index

        faces.extend([(ob0, ob1, ot1), (ob0, ot1, ot0)])
        faces.extend([(ib0, it0, it1), (ib0, it1, ib1)])
        faces.extend([(ot0, ot1, it1), (ot0, it1, it0)])
        faces.extend([(ob0, ib0, ib1), (ob0, ib1, ob1)])

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.apply_translation(center)
    return mesh


def _cube_with_square_tunnel() -> trimesh.Trimesh:
    parts = [
        _box((30, 30, 7), (0, 0, -11.5)),
        _box((30, 30, 7), (0, 0, 11.5)),
        _box((30, 7, 14), (0, -11.5, 0)),
        _box((30, 7, 14), (0, 11.5, 0)),
    ]
    return trimesh.util.concatenate(parts)


def _open_box() -> trimesh.Trimesh:
    parts = [
        _box((60, 40, 2), (0, 0, 1)),
        _box((60, 2, 24), (0, -19, 15.1)),
        _box((60, 2, 24), (0, 19, 15.1)),
        _box((2, 34, 24), (-29, 0, 15.1)),
        _box((2, 34, 24), (29, 0, 15.1)),
    ]
    return trimesh.util.concatenate(parts)


def _pencil_holder() -> trimesh.Trimesh:
    parts = [_box((72, 48, 3), (0, 0, 1.5))]
    for x in (-24, 0, 24):
        for y in (-10, 10):
            parts.append(_tube(6, 3.5, 34, (x, y, 21)))
    return trimesh.util.concatenate(parts)


def _default_model() -> trimesh.Trimesh:
    return _box((40, 30, 20), (0, 0, 10))


def generate_local_experimental_stl(user_prompt: str, output_path: str) -> str:
    text = user_prompt.lower()
    if "vase" in text or "vaza" in text:
        mesh = _vase()
    elif "pencil" in text:
        mesh = _pencil_holder()
    elif "open box" in text or "box" in text:
        mesh = _open_box()
    elif "cube" in text and "hole" in text:
        mesh = _cube_with_square_tunnel()
    else:
        mesh = _default_model()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output))
    return str(output)
