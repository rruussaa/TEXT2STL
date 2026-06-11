"""CadQuery generator for stable name plate models."""

from __future__ import annotations

from pathlib import Path

try:
    import cadquery as cq
except ModuleNotFoundError:
    cq = None

from app.schemas import NamePlateSpec


BLOCK_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "?": ("11110", "00001", "00001", "00110", "00100", "00000", "00100"),
}


def _safe_corner_radius(spec: NamePlateSpec) -> float:
    max_radius = min(spec.width_mm, spec.height_mm) / 2 - 0.5
    return max(0.0, min(spec.corner_radius_mm, max_radius))


def _hole_points(spec: NamePlateSpec) -> list[tuple[float, float]]:
    count = int(spec.mounting_holes)
    if count <= 0:
        return []

    margin = max(7.0, spec.hole_diameter_mm * 2.0)
    margin_x = min(margin, spec.width_mm / 2 - spec.hole_diameter_mm)
    margin_y = min(margin, spec.height_mm / 2 - spec.hole_diameter_mm)
    left = -spec.width_mm / 2 + margin_x
    right = spec.width_mm / 2 - margin_x
    bottom = -spec.height_mm / 2 + margin_y
    top = spec.height_mm / 2 - margin_y

    if count == 1:
        return [(left, 0.0)]
    if count == 2:
        return [(left, 0.0), (right, 0.0)]
    if count == 3:
        return [(left, bottom), (right, bottom), (0.0, top)]
    return [(left, bottom), (right, bottom), (left, top), (right, top)]


def _base_plate(spec: NamePlateSpec) -> cq.Workplane:
    radius = _safe_corner_radius(spec)
    model = cq.Workplane("XY").box(
        spec.width_mm,
        spec.height_mm,
        spec.thickness_mm,
        centered=(True, True, False),
    )
    if spec.rounded_corners and radius > 0:
        model = model.edges("|Z").fillet(radius)
    return model


def _add_holes(model: cq.Workplane, spec: NamePlateSpec) -> cq.Workplane:
    points = _hole_points(spec)
    if not points:
        return model
    return (
        model.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(points)
        .hole(spec.hole_diameter_mm)
    )


def _text_column_count(text: str) -> int:
    total = 0
    for char in text:
        total += 3 if char == " " else 5
        total += 1
    return max(1, total - 1)


def _block_text_solid(spec: NamePlateSpec, text: str, depth: float) -> cq.Workplane | None:
    text = text.upper()
    total_cols = _text_column_count(text)
    cell = min((spec.width_mm * 0.72) / total_cols, (spec.height_mm * 0.44) / 7)
    cell = max(0.7, cell)
    total_width = total_cols * cell
    total_height = 7 * cell
    z_base = spec.thickness_mm if spec.raised_text else spec.thickness_mm - depth

    solid: cq.Workplane | None = None
    cursor_col = 0
    for char in text:
        if char == " ":
            cursor_col += 4
            continue
        pattern = BLOCK_FONT.get(char, BLOCK_FONT["?"])
        for row_index, row in enumerate(pattern):
            for col_index, value in enumerate(row):
                if value != "1":
                    continue
                x = -total_width / 2 + (cursor_col + col_index + 0.5) * cell
                y = total_height / 2 - (row_index + 0.5) * cell
                pixel = (
                    cq.Workplane("XY")
                    .box(cell * 0.82, cell * 0.82, depth, centered=(True, True, False))
                    .translate((x, y, z_base))
                )
                solid = pixel if solid is None else solid.union(pixel)
        cursor_col += 6
    return solid


def _block_text_boxes(spec: NamePlateSpec, text: str, depth: float) -> list[tuple[float, float, float, float, float, float]]:
    text = text.upper()
    total_cols = _text_column_count(text)
    cell = min((spec.width_mm * 0.72) / total_cols, (spec.height_mm * 0.44) / 7)
    cell = max(0.7, cell)
    total_width = total_cols * cell
    total_height = 7 * cell
    z_base = spec.thickness_mm if spec.raised_text else spec.thickness_mm
    boxes: list[tuple[float, float, float, float, float, float]] = []

    cursor_col = 0
    for char in text:
        if char == " ":
            cursor_col += 4
            continue
        pattern = BLOCK_FONT.get(char, BLOCK_FONT["?"])
        for row_index, row in enumerate(pattern):
            for col_index, value in enumerate(row):
                if value != "1":
                    continue
                x = -total_width / 2 + (cursor_col + col_index + 0.5) * cell
                y = total_height / 2 - (row_index + 0.5) * cell
                boxes.append((x, y, z_base, cell * 0.82, cell * 0.82, depth))
        cursor_col += 6
    return boxes


def _add_block_text(model: cq.Workplane, spec: NamePlateSpec) -> cq.Workplane:
    text = spec.text.strip() or "AI LAB"
    depth = spec.text_depth_mm if spec.raised_text else min(spec.text_depth_mm, spec.thickness_mm * 0.8)
    text_solid = _block_text_solid(spec, text, depth)
    if text_solid is None:
        return model
    if spec.raised_text:
        return model.union(text_solid)
    return model.cut(text_solid)


def _add_native_text(model: cq.Workplane, spec: NamePlateSpec) -> cq.Workplane:
    text = spec.text.strip() or "AI LAB"
    font_size = min(spec.height_mm * 0.42, spec.width_mm / max(len(text) * 0.58, 1.0))
    font_size = max(4.0, font_size)

    workplane = model.faces(">Z").workplane(centerOption="CenterOfBoundBox")
    if spec.raised_text:
        return workplane.text(
            text,
            fontsize=font_size,
            distance=spec.text_depth_mm,
            cut=False,
            combine=True,
            clean=True,
            halign="center",
            valign="center",
        )

    cut_depth = min(spec.text_depth_mm, max(0.2, spec.thickness_mm * 0.8))
    return workplane.text(
        text,
        fontsize=font_size,
        distance=cut_depth,
        cut=True,
        combine=False,
        clean=True,
        halign="center",
        valign="center",
    )


def _add_text(model: cq.Workplane, spec: NamePlateSpec) -> cq.Workplane:
    try:
        return _add_native_text(model, spec)
    except Exception:
        return _add_block_text(model, spec)


def build_name_plate(spec: NamePlateSpec) -> cq.Workplane:
    if cq is None:
        raise RuntimeError("CadQuery is not installed.")
    model = _base_plate(spec)
    model = _add_holes(model, spec)
    model = _add_text(model, spec)
    return model


def _box_triangles(
    center_x: float,
    center_y: float,
    base_z: float,
    width: float,
    height: float,
    depth: float,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    x0 = center_x - width / 2
    x1 = center_x + width / 2
    y0 = center_y - height / 2
    y1 = center_y + height / 2
    z0 = base_z
    z1 = base_z + depth
    vertices = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    index_faces = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    ]
    return [(vertices[a], vertices[b], vertices[c]) for a, b, c in index_faces]


def _write_ascii_stl(
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]],
    output_path: str,
) -> str:
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("solid text2stl_fallback\n")
        for triangle in triangles:
            handle.write("  facet normal 0 0 0\n")
            handle.write("    outer loop\n")
            for vertex in triangle:
                handle.write(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
            handle.write("    endloop\n")
            handle.write("  endfacet\n")
        handle.write("endsolid text2stl_fallback\n")
    return output_path


def _generate_fallback_name_plate(spec: NamePlateSpec, output_path: str) -> str:
    triangles = _box_triangles(
        0,
        0,
        0,
        spec.width_mm,
        spec.height_mm,
        spec.thickness_mm,
    )
    if spec.raised_text:
        for box in _block_text_boxes(spec, spec.text.strip() or "AI LAB", spec.text_depth_mm):
            triangles.extend(_box_triangles(*box))
    return _write_ascii_stl(triangles, output_path)


def generate_name_plate(spec: NamePlateSpec, output_path: str) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if cq is None:
        return _generate_fallback_name_plate(spec, str(output))
    model = build_name_plate(spec)
    cq.exporters.export(model, str(output))
    return str(output)
