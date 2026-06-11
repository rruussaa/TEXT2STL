"""Curated CadQuery templates for common experimental demo objects.

The LLM remains the first generator, but these templates give the app a reliable
fallback when generated code is syntactically valid yet semantically weak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateMatch:
    name: str
    code: str


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _extract_number(text: str, patterns: tuple[str, ...]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def _build_vase_code(user_prompt: str) -> str:
    text = user_prompt.lower()
    number = r"(\d+(?:\.\d+)?)"

    height = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:tall|high|height)",
            rf"(?:height|tall|high)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )
    diameter = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:wide|diameter|across)",
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:wide\s+)?belly",
            rf"(?:diameter|width|belly)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )
    neck_diameter = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:neck|opening|mouth)",
            rf"(?:neck|opening|mouth)\s*(?:diameter|width)?\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )

    tall = "tall" in text or "high" in text
    short = "short" in text or "low" in text
    small = "small" in text or "mini" in text
    large = "large" in text or "big" in text
    wide = "wide" in text or "fat" in text or "broad" in text
    narrow = "narrow" in text or "slim" in text or "thin" in text
    flared = "flared" in text or "wide rim" in text or "wide mouth" in text or "flared rim" in text

    height_mm = height if height is not None else 58.0
    if height is None:
        if tall:
            height_mm = 82.0
        elif short:
            height_mm = 42.0
        elif small:
            height_mm = 48.0
        elif large:
            height_mm = 74.0
    height_mm = _clamp(height_mm, 30.0, 120.0)

    belly_radius = diameter / 2.0 if diameter is not None else 24.0
    if diameter is None:
        if narrow:
            belly_radius = 18.0
        elif wide:
            belly_radius = 31.0
        elif small:
            belly_radius = 19.0
        elif large:
            belly_radius = 30.0
    belly_radius = _clamp(belly_radius, 12.0, 42.0)

    wall = 2.4
    neck_radius = neck_diameter / 2.0 if neck_diameter is not None else 12.0
    if neck_diameter is None:
        if "narrow neck" in text or "small neck" in text or ("neck" in text and narrow):
            neck_radius = max(6.5, belly_radius * 0.42)
        elif "wide neck" in text or "wide mouth" in text:
            neck_radius = belly_radius * 0.72
        elif narrow:
            neck_radius = max(7.0, belly_radius * 0.48)
    neck_radius = _clamp(neck_radius, wall + 3.0, max(wall + 4.0, belly_radius - 2.0))

    rim_radius = neck_radius + 3.0
    if flared:
        rim_radius = max(neck_radius + 7.0, belly_radius * 0.88)
    elif "straight" in text:
        rim_radius = neck_radius + 1.5
    rim_radius = _clamp(rim_radius, neck_radius + 1.2, min(45.0, max(belly_radius + 8.0, neck_radius + 4.0)))

    base_radius = _clamp(belly_radius * 0.45, 6.5, 18.0)
    foot_radius = _clamp(max(base_radius + 3.0, belly_radius * 0.65), base_radius + 2.0, belly_radius)
    shoulder_radius = _clamp(max(neck_radius + 2.0, belly_radius * 0.72), neck_radius + 1.0, belly_radius)

    bottom_thickness = 3.2
    foot_z = height_mm * 0.13
    belly_z = height_mm * 0.46
    shoulder_z = height_mm * 0.70
    neck_z = height_mm * 0.86

    profile = [
        (0.0, 0.0),
        (base_radius, 0.0),
        (foot_radius, 0.0),
        (foot_radius * 0.95, foot_z),
        (belly_radius, belly_z),
        (shoulder_radius, shoulder_z),
        (neck_radius, neck_z),
        (rim_radius, height_mm),
        (max(rim_radius - wall, 2.5), height_mm),
        (max(neck_radius - wall, 2.5), neck_z),
        (max(shoulder_radius - wall, 2.5), shoulder_z),
        (max(belly_radius - wall, 2.5), belly_z),
        (max(base_radius - wall, 2.5), bottom_thickness),
        (0.0, bottom_thickness),
    ]
    point_lines = ",\n        ".join(f"({radius:.2f}, {z:.2f})" for radius, z in profile)

    return f'''def build_model():
    import cadquery as cq
    profile = [
        {point_lines},
    ]
    model = cq.Workplane("XZ").polyline(profile).close().revolve()
    return model
'''


def _build_adult_novelty_code(user_prompt: str) -> str:
    text = user_prompt.lower()
    number = r"(\d+(?:\.\d+)?)"

    length = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:long|length|tall|high)",
            rf"(?:length|long|tall|high)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )
    diameter = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:wide|diameter|thick)",
            rf"(?:diameter|width|thickness)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )

    small = "small" in text or "mini" in text
    large = "large" in text or "big" in text
    thin = "thin" in text or "slim" in text or "narrow" in text
    thick = "thick" in text or "wide" in text
    suction_base = "suction" in text or "wide base" in text or "flared base" in text

    length_mm = length if length is not None else 105.0
    if length is None:
        if small:
            length_mm = 78.0
        elif large:
            length_mm = 140.0
    length_mm = _clamp(length_mm, 55.0, 180.0)

    shaft_diameter = diameter if diameter is not None else 26.0
    if diameter is None:
        if thin:
            shaft_diameter = 20.0
        elif thick:
            shaft_diameter = 34.0
        elif small:
            shaft_diameter = 22.0
        elif large:
            shaft_diameter = 32.0
    shaft_radius = _clamp(shaft_diameter / 2.0, 8.0, 22.0)

    flange_radius = shaft_radius * (1.65 if suction_base else 1.45)
    flange_radius = _clamp(flange_radius, shaft_radius + 5.0, 35.0)
    flange_thickness = _clamp(shaft_radius * 0.32, 4.0, 8.0)
    transition_z = flange_thickness + _clamp(shaft_radius * 0.75, 6.0, 13.0)
    tip_start_z = max(transition_z + 10.0, length_mm - shaft_radius * 1.35)
    tip_length = max(8.0, length_mm - tip_start_z)
    top_radius = max(0.7, shaft_radius * 0.08)

    profile = [
        (0.0, 0.0),
        (flange_radius * 0.86, 0.0),
        (flange_radius, flange_thickness * 0.45),
        (flange_radius * 0.88, flange_thickness),
        (shaft_radius * 1.05, transition_z),
        (shaft_radius, transition_z + shaft_radius * 0.35),
        (shaft_radius, tip_start_z),
        (shaft_radius * 0.94, tip_start_z + tip_length * 0.25),
        (shaft_radius * 0.75, tip_start_z + tip_length * 0.50),
        (shaft_radius * 0.42, tip_start_z + tip_length * 0.75),
        (top_radius, length_mm),
        (0.0, length_mm),
    ]
    point_lines = ",\n        ".join(f"({radius:.2f}, {z:.2f})" for radius, z in profile)

    return f'''def build_model():
    import cadquery as cq
    shaft_radius = {shaft_radius:.2f}
    base_flange_radius = {flange_radius:.2f}
    rounded_tip_radius = {shaft_radius:.2f}
    profile = [
        {point_lines},
    ]
    model = cq.Workplane("XZ").polyline(profile).close().revolve()
    return model
'''

def _build_pyramid_code(user_prompt: str) -> str:
    text = user_prompt.lower()
    number = r"(\d+(?:\.\d+)?)"

    height = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:tall|high|height)",
            rf"(?:height|tall|high)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )
    base = _extract_number(
        text,
        (
            rf"{number}\s*(?:mm|millimeters?)?\s*(?:wide|base|across)",
            rf"(?:base|width)\s*(?:is|of|=|:)?\s*{number}\s*(?:mm|millimeters?)?",
        ),
    )

    small = "small" in text or "mini" in text
    large = "large" in text or "big" in text or "giza" in text
    flat_top = "flat top" in text or "truncated" in text

    base_mm = base if base is not None else 64.0
    height_mm = height if height is not None else 42.0
    if base is None:
        if small:
            base_mm = 42.0
        elif large:
            base_mm = 86.0
    if height is None:
        if small:
            height_mm = 30.0
        elif large:
            height_mm = 58.0
    base_mm = _clamp(base_mm, 20.0, 140.0)
    height_mm = _clamp(height_mm, 15.0, 110.0)

    plinth_height = _clamp(base_mm * 0.055, 2.0, 6.0)
    top_mm = 3.0 if flat_top else 0.8
    pyramid_height = max(8.0, height_mm - plinth_height)
    cap_z = plinth_height + pyramid_height
    entrance_width = _clamp(base_mm * 0.16, 5.0, 18.0)
    entrance_depth = _clamp(base_mm * 0.05, 1.2, 4.0)
    entrance_height = _clamp(height_mm * 0.20, 5.0, 20.0)

    return f'''def build_model():
    import cadquery as cq
    egyptian_pyramid_base = {base_mm:.2f}
    egyptian_pyramid_height = {height_mm:.2f}
    base_plinth = cq.Workplane("XY").box({base_mm + 8.0:.2f}, {base_mm + 8.0:.2f}, {plinth_height:.2f}, centered=(True, True, False))
    pyramid_body = (
        cq.Workplane("XY")
        .workplane(offset={plinth_height:.2f})
        .rect(egyptian_pyramid_base, egyptian_pyramid_base)
        .workplane(offset={pyramid_height:.2f})
        .rect({top_mm:.2f}, {top_mm:.2f})
        .loft(combine=True)
    )
    entrance = cq.Workplane("XY").box({entrance_width:.2f}, {entrance_depth:.2f}, {entrance_height:.2f}, centered=(True, True, False)).translate((0, {-base_mm / 2.0 - 0.25:.2f}, {plinth_height:.2f}))
    model = base_plinth.union(pyramid_body).union(entrance)
    return model
'''
AIRPLANE = '''def build_model():
    import cadquery as cq
    fuselage = cq.Workplane("XY").box(78, 14, 12, centered=(True, True, False)).translate((0, 0, 10))
    nose = cq.Workplane("XY").workplane(offset=10).circle(7).workplane(offset=15).circle(1.5).loft(combine=True).rotate((0, 0, 0), (0, 1, 0), 90).translate((46, 0, 6))
    wing_left = cq.Workplane("XY").box(34, 52, 3, centered=(True, True, False)).translate((-6, 28, 13))
    wing_right = cq.Workplane("XY").box(34, 52, 3, centered=(True, True, False)).translate((-6, -28, 13))
    tail_vertical = cq.Workplane("XY").box(5, 14, 24, centered=(True, True, False)).translate((-35, 0, 18))
    tail_left = cq.Workplane("XY").box(18, 28, 3, centered=(True, True, False)).translate((-33, 17, 17))
    tail_right = cq.Workplane("XY").box(18, 28, 3, centered=(True, True, False)).translate((-33, -17, 17))
    model = fuselage.union(nose).union(wing_left).union(wing_right).union(tail_vertical).union(tail_left).union(tail_right)
    return model
'''

VASE = '''def build_model():
    import cadquery as cq
    profile = [
        (10, 0), (18, 0), (17, 10), (24, 28), (16, 46), (18, 58),
        (12, 58), (10, 48), (17, 30), (12, 12), (13, 3), (10, 3),
    ]
    model = cq.Workplane("XZ").polyline(profile).close().revolve()
    return model
'''

PENCIL_HOLDER = '''def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").box(72, 48, 38, centered=(True, True, False)).edges("|Z").fillet(3)
    holes = [(-24, -11), (0, -11), (24, -11), (-24, 11), (0, 11), (24, 11)]
    model = base.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints(holes).hole(9, depth=33)
    return model
'''

OPEN_BOX = '''def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").box(62, 42, 28, centered=(True, True, False)).edges("|Z").fillet(2)
    inner = cq.Workplane("XY").box(56, 36, 27, centered=(True, True, False)).translate((0, 0, 4))
    model = outer.cut(inner)
    return model
'''

CUBE_HOLE = '''def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").box(30, 30, 30, centered=(True, True, True)).faces(">Z").workplane().hole(12, depth=34)
    return model
'''

CAR = '''def build_model():
    import cadquery as cq
    body = cq.Workplane("XY").box(64, 30, 14, centered=(True, True, False)).translate((0, 0, 8))
    cabin = cq.Workplane("XY").box(30, 24, 16, centered=(True, True, False)).translate((-4, 0, 22))
    wheel_fl = cq.Workplane("XZ").circle(6).extrude(5).translate((-22, -18, 8))
    wheel_fr = cq.Workplane("XZ").circle(6).extrude(5).translate((22, -18, 8))
    wheel_rl = cq.Workplane("XZ").circle(6).extrude(5).translate((-22, 13, 8))
    wheel_rr = cq.Workplane("XZ").circle(6).extrude(5).translate((22, 13, 8))
    model = body.union(cabin).union(wheel_fl).union(wheel_fr).union(wheel_rl).union(wheel_rr)
    return model
'''

CHAIR = '''def build_model():
    import cadquery as cq
    seat = cq.Workplane("XY").box(36, 36, 5, centered=(True, True, False)).translate((0, 0, 24))
    back = cq.Workplane("XY").box(36, 5, 34, centered=(True, True, False)).translate((0, 16, 26))
    legs = cq.Workplane("XY").pushPoints([(-14, -14), (14, -14), (-14, 14), (14, 14)]).rect(5, 5).extrude(24)
    model = legs.union(seat).union(back)
    return model
'''

TABLE = '''def build_model():
    import cadquery as cq
    top = cq.Workplane("XY").box(64, 42, 5, centered=(True, True, False)).translate((0, 0, 34))
    legs = cq.Workplane("XY").pushPoints([(-26, -16), (26, -16), (-26, 16), (26, 16)]).rect(5, 5).extrude(34)
    model = legs.union(top)
    return model
'''

ROCKET = '''def build_model():
    import cadquery as cq
    body = cq.Workplane("XY").circle(10).extrude(48)
    nose = cq.Workplane("XY").workplane(offset=48).circle(10).workplane(offset=18).circle(1.5).loft(combine=True)
    fin_a = cq.Workplane("XY").box(5, 18, 15, centered=(True, True, False)).translate((11, 0, 0))
    fin_b = cq.Workplane("XY").box(5, 18, 15, centered=(True, True, False)).translate((-11, 0, 0))
    fin_c = cq.Workplane("XY").box(18, 5, 15, centered=(True, True, False)).translate((0, 11, 0))
    fin_d = cq.Workplane("XY").box(18, 5, 15, centered=(True, True, False)).translate((0, -11, 0))
    model = body.union(nose).union(fin_a).union(fin_b).union(fin_c).union(fin_d)
    return model
'''

HOUSE = '''def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").box(52, 42, 32, centered=(True, True, False))
    roof = cq.Workplane("XY").rect(60, 50).workplane(offset=22).rect(6, 5).loft(combine=True).translate((0, 0, 32))
    door = cq.Workplane("XY").box(12, 2, 20, centered=(True, True, False)).translate((0, -22, 0))
    win_l = cq.Workplane("XY").box(10, 2, 10, centered=(True, True, False)).translate((-17, -22, 16))
    win_r = cq.Workplane("XY").box(10, 2, 10, centered=(True, True, False)).translate((17, -22, 16))
    model = base.union(roof).union(door).union(win_l).union(win_r)
    return model
'''

ROBOT = '''def build_model():
    import cadquery as cq
    body = cq.Workplane("XY").box(28, 18, 34, centered=(True, True, False)).translate((0, 0, 20))
    head = cq.Workplane("XY").box(22, 18, 18, centered=(True, True, False)).translate((0, 0, 55))
    arm_l = cq.Workplane("XY").box(8, 8, 28, centered=(True, True, False)).translate((-22, 0, 22))
    arm_r = cq.Workplane("XY").box(8, 8, 28, centered=(True, True, False)).translate((22, 0, 22))
    leg_l = cq.Workplane("XY").box(8, 8, 20, centered=(True, True, False)).translate((-8, 0, 0))
    leg_r = cq.Workplane("XY").box(8, 8, 20, centered=(True, True, False)).translate((8, 0, 0))
    antenna = cq.Workplane("XY").circle(2).extrude(12).translate((0, 0, 72))
    model = body.union(head).union(arm_l).union(arm_r).union(leg_l).union(leg_r).union(antenna)
    return model
'''

PHONE_STAND = '''def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").box(72, 46, 6, centered=(True, True, False))
    back = cq.Workplane("XY").box(72, 6, 48, centered=(True, True, False)).translate((0, 16, 12)).rotate((0, 0, 0), (1, 0, 0), -12)
    lip = cq.Workplane("XY").box(72, 8, 10, centered=(True, True, False)).translate((0, -17, 6))
    model = base.union(back).union(lip)
    return model
'''

BOAT = '''def build_model():
    import cadquery as cq
    hull = cq.Workplane("XY").rect(46, 14).workplane(offset=14).rect(72, 30).loft(combine=True)
    cabin = cq.Workplane("XY").box(24, 16, 12, centered=(True, True, False)).translate((4, 0, 14))
    mast = cq.Workplane("XY").circle(2).extrude(35).translate((-14, 0, 22))
    sail = cq.Workplane("XY").box(4, 24, 26, centered=(True, True, False)).translate((-8, 0, 25))
    model = hull.union(cabin).union(mast).union(sail)
    return model
'''

RING = '''def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(24).extrude(8)
    inner = cq.Workplane("XY").circle(13).extrude(12).translate((0, 0, -2))
    model = outer.cut(inner)
    return model
'''

SPHERE = '''def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").sphere(22)
    return model
'''

CONE = '''def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").circle(22).workplane(offset=45).circle(2).loft(combine=True)
    return model
'''

CYLINDER = '''def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").circle(18).extrude(42)
    return model
'''

TREE = '''def build_model():
    import cadquery as cq
    trunk = cq.Workplane("XY").circle(5).extrude(28)
    crown_low = cq.Workplane("XY").workplane(offset=22).circle(24).workplane(offset=20).circle(8).loft(combine=True)
    crown_high = cq.Workplane("XY").workplane(offset=38).circle(18).workplane(offset=20).circle(2).loft(combine=True)
    model = trunk.union(crown_low).union(crown_high)
    return model
'''

KEYCHAIN = '''def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").box(62, 26, 4, centered=(True, True, False)).edges("|Z").fillet(4)
    model = model.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints([(-24, 0)]).hole(5)
    return model
'''

BOWL = '''def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(12).workplane(offset=22).circle(32).loft(combine=True)
    inner = cq.Workplane("XY").workplane(offset=4).circle(8).workplane(offset=20).circle(26).loft(combine=True)
    model = outer.cut(inner)
    return model
'''

CUP = '''def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(21).extrude(42)
    inner = cq.Workplane("XY").circle(16).extrude(40).translate((0, 0, 5))
    grip_top = cq.Workplane("XY").box(5, 18, 5, centered=(True, True, False)).translate((23, 0, 29))
    grip_side = cq.Workplane("XY").box(5, 5, 22, centered=(True, True, False)).translate((23, 9, 13))
    grip_bottom = cq.Workplane("XY").box(5, 18, 5, centered=(True, True, False)).translate((23, 0, 11))
    model = outer.cut(inner).union(grip_top).union(grip_side).union(grip_bottom)
    return model
'''

LAMP = '''def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").circle(18).extrude(5)
    pole = cq.Workplane("XY").circle(3).extrude(42).translate((0, 0, 5))
    shade = cq.Workplane("XY").workplane(offset=42).circle(24).workplane(offset=18).circle(11).loft(combine=True)
    model = base.union(pole).union(shade)
    return model
'''

BENCH = '''def build_model():
    import cadquery as cq
    seat = cq.Workplane("XY").box(72, 22, 5, centered=(True, True, False)).translate((0, 0, 24))
    back = cq.Workplane("XY").box(72, 5, 26, centered=(True, True, False)).translate((0, 13, 30))
    legs = cq.Workplane("XY").pushPoints([(-28, -8), (28, -8), (-28, 8), (28, 8)]).rect(5, 5).extrude(24)
    model = legs.union(seat).union(back)
    return model
'''

STAIRS = '''def build_model():
    import cadquery as cq
    step1 = cq.Workplane("XY").box(64, 18, 6, centered=(True, True, False)).translate((0, -18, 0))
    step2 = cq.Workplane("XY").box(64, 18, 12, centered=(True, True, False)).translate((0, 0, 0))
    step3 = cq.Workplane("XY").box(64, 18, 18, centered=(True, True, False)).translate((0, 18, 0))
    model = step1.union(step2).union(step3)
    return model
'''

BRIDGE = '''def build_model():
    import cadquery as cq
    deck = cq.Workplane("XY").box(90, 24, 6, centered=(True, True, False)).translate((0, 0, 28))
    pillar_l = cq.Workplane("XY").box(8, 24, 28, centered=(True, True, False)).translate((-32, 0, 0))
    pillar_r = cq.Workplane("XY").box(8, 24, 28, centered=(True, True, False)).translate((32, 0, 0))
    rail_l = cq.Workplane("XY").box(90, 3, 10, centered=(True, True, False)).translate((0, -13, 34))
    rail_r = cq.Workplane("XY").box(90, 3, 10, centered=(True, True, False)).translate((0, 13, 34))
    model = deck.union(pillar_l).union(pillar_r).union(rail_l).union(rail_r)
    return model
'''

TEMPLATES: list[tuple[str, tuple[str, ...], str]] = [
    ("airplane", ("airplane", "plane", "aircraft", "jet"), AIRPLANE),
    ("pencil_holder", ("pencil holder", "pen holder", "holder with holes"), PENCIL_HOLDER),
    ("phone_stand", ("phone stand", "tablet stand"), PHONE_STAND),
    ("open_box", ("open box", "tray", "container", "small box"), OPEN_BOX),
    ("cube_hole", ("cube with", "cube", "hole through"), CUBE_HOLE),
    ("pyramid", ("pyramid", "egyptian pyramid", "egypt", "giza"), _build_pyramid_code("pyramid")),
    ("adult_novelty", ("dildo", "adult novelty", "adult toy", "novelty toy"), _build_adult_novelty_code("adult novelty")),
    ("vase", ("vase", "flower vase", "vessel"), VASE),
    ("car", ("car", "vehicle", "truck"), CAR),
    ("chair", ("chair", "stool"), CHAIR),
    ("table", ("table", "desk"), TABLE),
    ("rocket", ("rocket", "spaceship", "missile"), ROCKET),
    ("house", ("house", "home", "building"), HOUSE),
    ("robot", ("robot", "humanoid"), ROBOT),
    ("boat", ("boat", "ship"), BOAT),
    ("tree", ("tree", "pine", "fir"), TREE),
    ("keychain", ("keychain", "key chain", "tag"), KEYCHAIN),
    ("bowl", ("bowl",), BOWL),
    ("cup", ("cup", "mug"), CUP),
    ("lamp", ("lamp", "light"), LAMP),
    ("bench", ("bench",), BENCH),
    ("stairs", ("stairs", "staircase", "steps"), STAIRS),
    ("bridge", ("bridge",), BRIDGE),
    ("ring", ("ring", "washer", "donut", "tube"), RING),
    ("sphere", ("sphere", "ball", "globe"), SPHERE),
    ("cone", ("cone",), CONE),
    ("cylinder", ("cylinder",), CYLINDER),
]


def detect_template_name(user_prompt: str) -> str | None:
    text = user_prompt.lower()
    if "cube" in text and "hole" not in text:
        return None
    for name, keywords, _code in TEMPLATES:
        if _has_any(text, keywords):
            if name == "cube_hole" and "hole" not in text:
                continue
            return name
    return None


def get_template_code(user_prompt: str) -> str | None:
    name = detect_template_name(user_prompt)
    if not name:
        return None
    for template_name, _keywords, code in TEMPLATES:
        if template_name == name:
            if template_name == "pyramid":
                return _build_pyramid_code(user_prompt)
            if template_name == "adult_novelty":
                return _build_adult_novelty_code(user_prompt)
            if template_name == "vase":
                return _build_vase_code(user_prompt)
            return code
    return None
