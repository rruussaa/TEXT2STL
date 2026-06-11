"""Build lightweight interactive STL preview figures for Streamlit."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh


def _load_mesh(path: str) -> trimesh.Trimesh:
    loaded = trimesh.load(str(Path(path)), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        meshes = [geometry for geometry in loaded.geometry.values()]
        if not meshes:
            raise ValueError("STL scene has no geometry.")
        return trimesh.util.concatenate(meshes)
    return loaded


def build_stl_preview_figure(path: str, max_faces: int = 20000):
    import plotly.graph_objects as go

    mesh = _load_mesh(path)
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)

    if vertices.size == 0 or faces.size == 0:
        raise ValueError("STL mesh has no previewable geometry.")

    if len(faces) > max_faces:
        step = max(1, len(faces) // max_faces)
        faces = faces[::step][:max_faces]

    x = vertices[:, 0]
    y = vertices[:, 1]
    z = vertices[:, 2]

    figure = go.Figure(
        data=[
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                color="#6fb1d6",
                opacity=1.0,
                flatshading=False,
                lighting={
                    "ambient": 0.45,
                    "diffuse": 0.75,
                    "fresnel": 0.15,
                    "roughness": 0.65,
                    "specular": 0.25,
                },
                lightposition={"x": 120, "y": -160, "z": 220},
                hoverinfo="skip",
            )
        ]
    )
    figure.update_layout(
        height=480,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="white",
        scene={
            "aspectmode": "data",
            "camera": {"eye": {"x": 1.5, "y": -1.7, "z": 1.2}},
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "zaxis": {"visible": False},
        },
    )
    return figure
