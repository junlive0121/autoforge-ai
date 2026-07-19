"""Build the judge-facing demo video from verified local product footage."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1920
HEIGHT = 1080
BACKGROUND = "#080A10"
CARD = "#121722"
TEXT = "#F5F7FA"
DIM = "#A4AEBD"
PURPLE = "#7567F8"
TEAL = "#55D6C8"
GREEN = "#70E1A4"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--narration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assets = args.assets_dir.resolve()
    project = args.project_dir.resolve()
    assets.mkdir(parents=True, exist_ok=True)
    _create_slides(assets, project)

    segments = [
        ("01-input.png", 13.0, False),
        ("02-progress.png", 18.0, False),
        ("03-complete.png", 7.0, False),
        ("04-inspectable.png", 13.0, False),
        (str(project / "final.mp4"), 17.0, True),
        ("05-gpt.png", 18.0, False),
        ("06-codex.png", 28.0, False),
        ("07-reliability.png", 14.0, False),
        ("08-close.png", 8.0, False),
    ]
    segment_paths: list[Path] = []
    for index, (name, duration, is_video) in enumerate(segments, start=1):
        source = Path(name) if Path(name).is_absolute() else assets / name
        destination = assets / f"segment-{index:02d}.mp4"
        if is_video:
            _render_video_segment(source, destination, duration)
        else:
            _render_still_segment(source, destination, duration)
        segment_paths.append(destination)

    concat_file = assets / "segments.txt"
    concat_file.write_text(
        "".join(f"file '{_concat_escape(path)}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    visual_track = assets / "visual-track.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(visual_track),
        ]
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(visual_track),
            "-i",
            str(args.narration.resolve()),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(args.output.resolve()),
        ]
    )


def _create_slides(assets: Path, project: Path) -> None:
    frames = [project / f"image_{index}.png" for index in range(1, 4)]
    canvas, draw = _base_slide(
        "INSPECTABLE BY DESIGN",
        "Teachers see the plan, script, storyboard, and every frame.",
    )
    for index, frame in enumerate(frames):
        image = Image.open(frame).convert("RGB")
        image.thumbnail((520, 300))
        x = 130 + index * 570
        y = 330
        canvas.paste(image, (x, y))
        draw.rounded_rectangle(
            (x - 5, y - 5, x + image.width + 5, y + image.height + 5),
            radius=12,
            outline=(85, 214, 200),
            width=4,
        )
    _bullets(
        draw,
        [
            "Learning objective remains explicit",
            "Exact narration and shot order stay reviewable",
            "Sample mode is labeled and reproducible",
        ],
        x=150,
        y=720,
        columns=3,
    )
    canvas.save(assets / "04-inspectable.png")

    canvas, draw = _base_slide(
        "GPT-5.6 TERRA",
        "The reasoning layer for the live classroom workflow.",
    )
    _code_card(
        draw,
        [
            'openai_model: str = Field(',
            '    default="gpt-5.6-terra"',
            ")",
            "",
            "Director    → audience-aware lesson plan",
            "Writer      → concise teaching script",
            "Storyboard  → validated narration + visuals",
        ],
        x=150,
        y=310,
        width=1620,
        height=560,
    )
    draw.text(
        (150, 920),
        "Structured educational decisions before expensive media generation.",
        font=_font(34, bold=True),
        fill=GREEN,
    )
    canvas.save(assets / "05-gpt.png")

    canvas, draw = _base_slide(
        "CODEX AS ENGINEERING COLLABORATOR",
        "Build Week decisions were audited, implemented, tested, and documented.",
    )
    _decision_card(
        draw,
        "01",
        "Product",
        "Pivot from a generic generator to a teacher-facing Education entry.",
        150,
        300,
    )
    _decision_card(
        draw,
        "02",
        "Reliability",
        "Make structured validation and atomic media publication first-class.",
        990,
        300,
    )
    _decision_card(
        draw,
        "03",
        "Scope",
        "Ship a coherent judging build instead of unrelated SaaS infrastructure.",
        150,
        610,
    )
    _decision_card(
        draw,
        "04",
        "Evidence",
        "Add runnable sample mode, regression tests, and prior-versus-new disclosure.",
        990,
        610,
    )
    canvas.save(assets / "06-codex.png")

    canvas, draw = _base_slide(
        "RELIABILITY IS A PRODUCT FEATURE",
        "Generated media is treated as data integrity—not as a file-exists check.",
    )
    draw.text((150, 315), "27", font=_font(220, bold=True), fill=GREEN)
    draw.text((470, 380), "tests passing", font=_font(70, bold=True), fill=TEXT)
    _bullets(
        draw,
        [
            "Path containment + atomic JSON",
            "Storyboard contract validation",
            "Decoded image + stream verification",
            "Real narration-duration assembly",
            "Restart-aware project lifecycle",
            "Redacted public failure messages",
        ],
        x=150,
        y=650,
        columns=2,
    )
    canvas.save(assets / "07-reliability.png")

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((110, 100, 1810, 980), radius=58, fill=CARD)
    draw.text((180, 220), "AUTOFORGE", font=_font(48, bold=True), fill=TEAL)
    draw.text((180, 305), "CLASSROOM", font=_font(122, bold=True), fill=TEXT)
    draw.text(
        (180, 525),
        "A lesson objective in.",
        font=_font(58),
        fill=DIM,
    )
    draw.text(
        (180, 610),
        "A validated lesson video out.",
        font=_font(58, bold=True),
        fill=GREEN,
    )
    draw.rounded_rectangle((180, 780, 670, 860), radius=18, fill=PURPLE)
    draw.text((220, 800), "OPENAI BUILD WEEK", font=_font(30, bold=True), fill=TEXT)
    canvas.save(assets / "08-close.png")


def _base_slide(kicker: str, title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((150, 105), kicker, font=_font(34, bold=True), fill=TEAL)
    wrapped = _wrap(title, 44)
    draw.multiline_text(
        (150, 165),
        wrapped,
        font=_font(55, bold=True),
        fill=TEXT,
        spacing=12,
    )
    return canvas, draw


def _code_card(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    draw.rounded_rectangle((x, y, x + width, y + height), radius=28, fill=CARD)
    draw.ellipse((x + 36, y + 30, x + 54, y + 48), fill="#FF6B6B")
    draw.ellipse((x + 68, y + 30, x + 86, y + 48), fill="#FFD166")
    draw.ellipse((x + 100, y + 30, x + 118, y + 48), fill=GREEN)
    draw.multiline_text(
        (x + 55, y + 90),
        "\n".join(lines),
        font=_mono_font(37),
        fill="#D7E2F0",
        spacing=17,
    )


def _decision_card(
    draw: ImageDraw.ImageDraw,
    number: str,
    label: str,
    body: str,
    x: int,
    y: int,
) -> None:
    draw.rounded_rectangle((x, y, x + 780, y + 255), radius=28, fill=CARD)
    draw.text((x + 38, y + 34), number, font=_font(34, bold=True), fill=PURPLE)
    draw.text((x + 115, y + 30), label, font=_font(42, bold=True), fill=TEXT)
    draw.multiline_text(
        (x + 38, y + 105),
        _wrap(body, 42),
        font=_font(29),
        fill=DIM,
        spacing=9,
    )


def _bullets(
    draw: ImageDraw.ImageDraw,
    items: list[str],
    *,
    x: int,
    y: int,
    columns: int,
) -> None:
    column_width = (WIDTH - x * 2) // columns
    rows = (len(items) + columns - 1) // columns
    for index, item in enumerate(items):
        column = index // rows
        row = index % rows
        item_x = x + column * column_width
        item_y = y + row * 115
        draw.ellipse((item_x, item_y + 12, item_x + 22, item_y + 34), fill=TEAL)
        draw.multiline_text(
            (item_x + 42, item_y),
            _wrap(item, max(24, 36 // columns + 20)),
            font=_font(29, bold=True),
            fill=TEXT,
            spacing=7,
        )


def _render_still_segment(source: Path, destination: Path, duration: float) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(source),
            "-t",
            str(duration),
            "-vf",
            (
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x080A10,"
                "fps=30,format=yuv420p"
            ),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            str(destination),
        ]
    )


def _render_video_segment(source: Path, destination: Path, duration: float) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-t",
            str(duration),
            "-vf",
            (
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x080A10,"
                "fps=30,format=yuv420p"
            ),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            str(destination),
        ]
    )


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _mono_font(size: int) -> ImageFont.ImageFont:
    for candidate in [
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(text: str, width: int) -> str:
    import textwrap

    return "\n".join(textwrap.wrap(text, width=width))


def _concat_escape(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def _run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): "
            f"{completed.stderr[-4000:]}"
        )


if __name__ == "__main__":
    main()
