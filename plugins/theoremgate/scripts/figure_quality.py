#!/usr/bin/env python3
"""Dependency-free structural audits for publication figures."""

from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


SIZE_CLASSES = {
    "single_column": {"target_width_in": 3.25, "max_height_in": 4.8},
    "double_column": {"target_width_in": 6.75, "max_height_in": 7.5},
    "full_page": {"target_width_in": 6.75, "max_height_in": 8.5},
}
VECTOR_SUFFIXES = {".pdf", ".svg"}


def _number(value: str) -> float | None:
    match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", str(value or ""))
    return float(match.group(1)) if match else None


def _length_inches(value: str) -> float | None:
    match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(in|pt|px|cm|mm)?\s*$", str(value or ""), re.I)
    if not match:
        return None
    number, unit = float(match.group(1)), (match.group(2) or "px").lower()
    return number * {"in": 1.0, "pt": 1 / 72.0, "px": 1 / 96.0, "cm": 1 / 2.54, "mm": 1 / 25.4}[unit]


def _pdf_dimensions(path: Path) -> tuple[float, float, int]:
    data = path.read_bytes()
    match = re.search(
        rb"/MediaBox\s*\[\s*([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s*\]",
        data,
    )
    if not match:
        raise ValueError("PDF figure has no readable MediaBox")
    x0, y0, x1, y1 = map(float, match.groups())
    if x1 <= x0 or y1 <= y0:
        raise ValueError("PDF figure has invalid page dimensions")
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    return (x1 - x0) / 72.0, (y1 - y0) / 72.0, pages


def _svg_dimensions(path: Path) -> tuple[float, float, list[float]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"SVG figure is malformed: {exc}") from exc
    width, height = _length_inches(root.get("width", "")), _length_inches(root.get("height", ""))
    viewbox = [float(item) for item in re.split(r"[ ,]+", root.get("viewBox", "").strip()) if item]
    if (not width or not height) and len(viewbox) == 4 and viewbox[2] > 0 and viewbox[3] > 0:
        width, height = viewbox[2] / 96.0, viewbox[3] / 96.0
    if not width or not height:
        raise ValueError("SVG figure requires width/height or a valid viewBox")
    font_sizes = []
    for element in root.iter():
        direct = _number(element.get("font-size", ""))
        if direct:
            font_sizes.append(direct)
        style = element.get("style", "")
        match = re.search(r"font-size\s*:\s*([0-9.]+)", style)
        if match:
            font_sizes.append(float(match.group(1)))
    return width, height, font_sizes


def _png_dimensions(path: Path) -> tuple[int, int, float | None]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG figure is malformed")
    width, height = struct.unpack(">II", data[16:24])
    dpi = None
    cursor = 8
    while cursor + 12 <= len(data):
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        payload = data[cursor + 8:cursor + 8 + length]
        if kind == b"pHYs" and len(payload) == 9 and payload[8] == 1:
            x_ppm = struct.unpack(">I", payload[:4])[0]
            dpi = x_ppm * 0.0254
            break
        cursor += 12 + length
    return width, height, dpi


def audit_figure(path: Path, size_class: str, *, panels: int = 1, role: str = "main") -> dict:
    if size_class not in SIZE_CLASSES:
        raise ValueError(f"unknown figure size class: {size_class}")
    if not isinstance(panels, int) or isinstance(panels, bool) or panels < 1 or panels > 12:
        raise ValueError("figure panels must be an integer between 1 and 12")
    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".svg", ".png"}:
        raise ValueError("figure must be PDF, SVG, or PNG")
    warnings, errors = [], []
    width = height = None
    details = {"format": suffix[1:], "vector_master": suffix in VECTOR_SUFFIXES}
    if suffix == ".pdf":
        width, height, pages = _pdf_dimensions(path)
        details["pages"] = pages
        if pages != 1:
            errors.append("PDF figure must contain exactly one page")
    elif suffix == ".svg":
        width, height, font_sizes = _svg_dimensions(path)
        details["detected_font_sizes"] = font_sizes
    else:
        pixels_w, pixels_h, dpi = _png_dimensions(path)
        details.update({"pixel_width": pixels_w, "pixel_height": pixels_h, "embedded_dpi": dpi})
        target_width = SIZE_CLASSES[size_class]["target_width_in"]
        effective_dpi = pixels_w / target_width
        details["effective_dpi_at_target_width"] = round(effective_dpi, 1)
        if effective_dpi < 300:
            errors.append("raster figure is below 300 DPI at its declared paper width")
        warnings.append("PNG is a preview/raster fallback; use PDF or SVG as the publication master")
        width, height = target_width, target_width * pixels_h / pixels_w
    aspect = width / height
    target = SIZE_CLASSES[size_class]
    scale_factor = target["target_width_in"] / width
    scaled_height = height * scale_factor
    details.update({
        "width_in": round(width, 3), "height_in": round(height, 3),
        "aspect_ratio": round(aspect, 3), "target_width_in": target["target_width_in"],
        "scale_factor_to_paper": round(scale_factor, 3), "scaled_height_in": round(scaled_height, 3),
        "max_height_in": target["max_height_in"], "panels": panels, "role": role,
    })
    if scaled_height > target["max_height_in"] + 0.05:
        errors.append("figure is taller than the declared manuscript size class permits")
    if scale_factor > 1.2:
        warnings.append("figure must be enlarged substantially at paper size; linework may look weak")
    if scale_factor < 0.55:
        warnings.append("figure will be reduced substantially; text and markers need visual review")
    if suffix == ".svg" and details.get("detected_font_sizes"):
        if min(details["detected_font_sizes"]) * scale_factor < 7:
            warnings.append("SVG contains text smaller than 7 pt at declared paper size")
    if aspect < 0.45:
        warnings.append("figure is unusually tall and may disrupt paper layout")
    if aspect > 3.2:
        warnings.append("figure is unusually wide; labels may become unreadable after scaling")
    if panels > 1 and size_class == "single_column" and panels > 2:
        warnings.append("more than two panels in a single-column figure will usually be unreadable")
    return {
        "schema_version": 1, "artifact": "figure_quality_report", "path": str(path),
        "size_class": size_class, "details": details, "errors": errors, "warnings": warnings,
        "structurally_valid": not errors,
        "publication_master_eligible": not errors and suffix in VECTOR_SUFFIXES,
    }
