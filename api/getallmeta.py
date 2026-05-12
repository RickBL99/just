import os
import io
import re
import json
import subprocess
import builtins
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from PIL import Image

# Register HEIC/HEIF support if pillow-heif is available. ExifTool reads HEIC
# metadata natively without this; this only affects thumbnail generation.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_AVAILABLE = True
except ImportError:
    HEIC_AVAILABLE = False

import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)

# ---------- logging ----------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = logging.FileHandler('mylog.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# ---------- constants ----------
router = APIRouter()
templates = Jinja2Templates(directory="templates/")

UPLOAD_BASE = "uploaded_files"
METADATA_CACHE = "_metadata.json"
THUMB_PREFIX = "_thumb_"

META_SUFFIXES = (
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".psd",
    ".heic", ".heif",
    ".raw", ".dng", ".cr2", ".nef", ".sr2",
)

# Formats Pillow can usually open for thumbnails. RAW formats fall through to placeholder.
# HEIC/HEIF require pillow-heif (registered above); without it Image.open will raise
# and the thumb route will return the SVG placeholder.
PIL_THUMB_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".psd",
                 ".heic", ".heif"}

# Don't include these keys in the on-page table, the XLSX, or the PDF
SKIP_KEYS = {"SourceFile", "ExifToolVersion", "FileName", "Directory", "gps_data"}

PLACEHOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" preserveAspectRatio="xMidYMid slice">'
    '<rect width="200" height="200" fill="#F4F1EA"/>'
    '<text x="100" y="95" font-family="ui-monospace,monospace" font-size="11" '
    'fill="#8E8B83" text-anchor="middle" letter-spacing="2">NO</text>'
    '<text x="100" y="115" font-family="ui-monospace,monospace" font-size="11" '
    'fill="#8E8B83" text-anchor="middle" letter-spacing="2">PREVIEW</text>'
    '</svg>'
)

try:
    LANCZOS = Image.Resampling.LANCZOS  # Pillow >= 9.1
except AttributeError:  # pragma: no cover
    LANCZOS = Image.LANCZOS


# ---------- GPS parsing ----------
# ExifTool's default output looks like:  "37 deg 46' 29.64\" N"
# Sometimes minutes/seconds are missing; sometimes the hemisphere isn't in the
# value string and lives in GPSLatitudeRef / GPSLongitudeRef instead.
_DMS_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*deg(?:\s*(\d+(?:\.\d+)?)')?(?:\s*(\d+(?:\.\d+)?)\")?\s*([NSEW])?",
    re.IGNORECASE,
)


def _parse_dms(value):
    """Parse an ExifTool GPS value into a decimal degrees float, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    # Plain numeric string?
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    m = _DMS_RE.search(value)
    if not m:
        return None
    deg = float(m.group(1) or 0)
    minutes = float(m.group(2) or 0)
    seconds = float(m.group(3) or 0)
    hemi = (m.group(4) or "").upper()
    sign = -1.0 if deg < 0 else 1.0
    decimal = sign * (abs(deg) + minutes / 60.0 + seconds / 3600.0)
    if hemi in ("S", "W") and decimal > 0:
        decimal = -decimal
    return decimal


def _gps_to_decimal(value, ref):
    """Convert ExifTool GPS to decimal degrees, applying hemisphere ref if needed."""
    d = _parse_dms(value)
    if d is None:
        return None
    if d > 0 and ref:
        r = str(ref).strip().upper()
        if r.startswith("S") or r.startswith("W"):
            d = -d
    return d


# ---------- helpers ----------
def _session_dir(request: Request) -> Path:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=403, detail="No session cookie")
    return Path(UPLOAD_BASE) / session_id


def _is_image_file(name: str) -> bool:
    if name.startswith(THUMB_PREFIX) or name == METADATA_CACHE:
        return False
    return name.lower().endswith(META_SUFFIXES)


def _extract_all(fullpath: str):
    """Run exiftool on every image in the directory and return [[filename, data], ...]."""
    results = []
    for filename in sorted(os.listdir(fullpath)):
        if not _is_image_file(filename):
            continue
        filepath = os.path.join(fullpath, filename)
        try:
            output = subprocess.check_output(["exiftool", "-j", filepath])
            data = json.loads(output)[0]

            gps_data = {}
            if "GPSLatitude" in data and "GPSLongitude" in data:
                lat = _gps_to_decimal(data.get("GPSLatitude"), data.get("GPSLatitudeRef"))
                lon = _gps_to_decimal(data.get("GPSLongitude"), data.get("GPSLongitudeRef"))
                if lat is not None and lon is not None:
                    gps_data = {
                        "latitude": lat,
                        "longitude": lon,
                        "lat_raw": data.get("GPSLatitude"),
                        "lon_raw": data.get("GPSLongitude"),
                    }
            data["gps_data"] = gps_data

            results.append([filename, data])
            logger.debug(f"Metadata retrieved successfully for {filename}")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"exiftool error on {filename}: "
                f"{e.output.decode('utf-8', errors='replace')} (rc={e.returncode})"
            )
            raise
    return results


def _build_gps_points(all_metadata):
    """Build a flat list of points (with the original file index) for the map."""
    points = []
    for i, (fname, meta) in enumerate(all_metadata, 1):
        gps = (meta or {}).get("gps_data") or {}
        lat = gps.get("latitude")
        lon = gps.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            points.append({
                "index": i,
                "filename": fname,
                "latitude": float(lat),
                "longitude": float(lon),
            })
    return points


def _load_cached(request: Request):
    session_dir = _session_dir(request)
    cache = session_dir / METADATA_CACHE
    if cache.exists():
        with open(cache) as f:
            return json.load(f)
    # Fallback: regenerate if the upload folder is still there
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="No upload session found")
    try:
        data = _extract_all(str(session_dir))
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to extract metadata")
    try:
        with open(cache, "w") as f:
            json.dump(data, f, default=str)
    except Exception as e:
        logger.warning(f"Could not write metadata cache: {e}")
    return data


# ---------- main view ----------
@router.post("/api/getallmeta")
async def getallmeta(request: Request, image_number: str = Query(None)):
    logger.debug("Waiting 5s before getting cookie")
    time.sleep(5)

    session_id = request.cookies.get("session_id")
    fullpath = os.path.join(UPLOAD_BASE, session_id)
    logger.debug(f"Full path: {fullpath}")

    if not os.path.exists(fullpath):
        return templates.TemplateResponse(
            "error.html",
            context={"request": request, "error_message": "Please upload some images to get started."},
            status_code=404,
            media_type="text/html",
        )

    logger.debug("Waiting 5s to ensure all files are available")
    time.sleep(5)

    try:
        all_metadata = _extract_all(fullpath)
    except subprocess.CalledProcessError as e:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error_message": "Error retrieving metadata",
                "error_code": e.returncode,
            },
            status_code=500,
            media_type="text/html",
        )

    # Cache so /api/download/* don't have to re-run exiftool
    try:
        with open(os.path.join(fullpath, METADATA_CACHE), "w") as f:
            json.dump(all_metadata, f, default=str)
    except Exception as e:
        logger.warning(f"Failed to write metadata cache: {e}")

    gps_points = _build_gps_points(all_metadata)

    context = {"isinstance": builtins.isinstance}
    return templates.TemplateResponse(
        "getallmeta.html",
        context={
            "request": request,
            "all_metadata": all_metadata,
            "context": context,
            "fullpath": fullpath,
            "gps_points": gps_points,
        },
        status_code=200,
        media_type="text/html",
    )


# ---------- thumbnail ----------
@router.get("/api/thumb/{filename}")
async def thumb(request: Request, filename: str):
    """Return a small JPEG thumbnail, falling back to an SVG placeholder."""
    if filename.startswith(THUMB_PREFIX) or filename == METADATA_CACHE:
        return Response(content=PLACEHOLDER_SVG, media_type="image/svg+xml")

    session_dir = _session_dir(request)
    src = session_dir / filename
    if not src.exists() or not src.is_file():
        return Response(content=PLACEHOLDER_SVG, media_type="image/svg+xml")

    ext = src.suffix.lower()
    thumb_path = session_dir / f"{THUMB_PREFIX}{filename}.jpg"

    if thumb_path.exists():
        return FileResponse(
            str(thumb_path),
            media_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    if ext in PIL_THUMB_EXT:
        try:
            with Image.open(src) as img:
                img.thumbnail((240, 240), LANCZOS)
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", img.size, (251, 249, 244))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(str(thumb_path), "JPEG", quality=82, optimize=True)
            return FileResponse(
                str(thumb_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "private, max-age=3600"},
            )
        except Exception as e:
            logger.warning(f"Thumbnail generation failed for {filename}: {e}")

    return Response(content=PLACEHOLDER_SVG, media_type="image/svg+xml")


# ---------- XLSX download ----------
@router.get("/api/download/xlsx")
async def download_xlsx(request: Request):
    all_metadata = _load_cached(request)

    rows = []
    for fname, meta in all_metadata:
        row = {"Filename": fname}
        for k, v in meta.items():
            if k in SKIP_KEYS:
                continue
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            elif not isinstance(v, (str, int, float, bool, type(None))):
                v = str(v)
            row[k] = v
        rows.append(row)

    df = pd.DataFrame(rows)
    if "Filename" in df.columns:
        cols = ["Filename"] + sorted(c for c in df.columns if c != "Filename")
        df = df[cols]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Metadata", index=False)
        ws = writer.sheets["Metadata"]
        for idx, col in enumerate(df.columns, start=1):
            sample_len = df[col].astype(str).map(len).max() if len(df) else 0
            width = min(max(len(str(col)) + 2, int(sample_len) + 2, 12), 60)
            ws.column_dimensions[ws.cell(1, idx).column_letter].width = width
        ws.freeze_panes = "A2"

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="justthemeta-results.xlsx"'},
    )


# ---------- PDF download ----------
@router.get("/api/download/pdf")
async def download_pdf(request: Request):
    all_metadata = _load_cached(request)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="JustTheMeta — Metadata Report",
        author="JustTheMeta",
    )

    styles = getSampleStyleSheet()
    kicker = ParagraphStyle(
        "Kicker", parent=styles["Normal"], fontName="Courier",
        fontSize=8, textColor=colors.HexColor("#D9381E"),
        spaceAfter=4, leading=10, alignment=0,
    )
    title = ParagraphStyle(
        "Title", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=28, textColor=colors.HexColor("#0B0B0A"),
        alignment=0, spaceAfter=4, leading=32,
    )
    sub = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, textColor=colors.HexColor("#4A4844"),
        spaceAfter=24, leading=14,
    )
    file_kicker = ParagraphStyle(
        "FK", parent=styles["Normal"], fontName="Courier-Bold",
        fontSize=8, textColor=colors.HexColor("#D9381E"),
        spaceAfter=3, leading=10,
    )
    file_title = ParagraphStyle(
        "FT", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=14, textColor=colors.HexColor("#0B0B0A"),
        spaceAfter=8, leading=18,
    )

    story = [
        Paragraph("EXIF · IPTC · XMP · GPS REPORT", kicker),
        Paragraph("Just the meta.", title),
        Paragraph(
            f"{len(all_metadata)} file{'s' if len(all_metadata) != 1 else ''} analyzed · "
            f"Extracted via ExifTool",
            sub,
        ),
    ]

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B0B0A")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#FBF9F4")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("FONTNAME",   (0, 1), (0, -1), "Courier"),
        ("FONTNAME",   (1, 1), (1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 7.5),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR",  (0, 1), (0, -1), colors.HexColor("#4A4844")),
        ("TEXTCOLOR",  (1, 1), (1, -1), colors.HexColor("#0B0B0A")),
        ("LINEBELOW",  (0, 0), (-1, 0), 0.5, colors.HexColor("#0B0B0A")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#FBF9F4"), colors.HexColor("#F4F1EA")]),
    ])

    for i, (fname, meta) in enumerate(all_metadata, 1):
        header = [
            Paragraph(f"FILE {i:03d} / {len(all_metadata):03d}", file_kicker),
            Paragraph(fname, file_title),
        ]

        rows_data = [["Field", "Value"]]
        for k, v in meta.items():
            if k in SKIP_KEYS:
                continue
            val = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            if len(val) > 300:
                val = val[:300] + "…"
            rows_data.append([str(k), val])

        t = Table(rows_data, colWidths=[1.9 * inch, 5.0 * inch], repeatRows=1)
        t.setStyle(table_style)

        story.append(KeepTogether(header))
        story.append(t)
        story.append(Spacer(1, 0.25 * inch))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="justthemeta-results.pdf"'},
    )