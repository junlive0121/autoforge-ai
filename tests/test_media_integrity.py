"""Contract tests for generated storyboard and media artifacts."""

from pathlib import Path

import pytest
from PIL import Image

from src.core.media_integrity import (
    ShotValidationError,
    safe_error_message,
    validate_image_file,
    validate_shots,
)


def test_shot_contract_sorts_valid_shots() -> None:
    shots = [
        {"shot_id": 2, "voiceover": "Second", "image_prompt": "Blue diagram"},
        {"shot_id": 1, "voiceover": "First", "image_prompt": "Red diagram"},
    ]

    assert [shot["shot_id"] for shot in validate_shots(shots)] == [1, 2]


@pytest.mark.parametrize(
    "shots",
    [
        [],
        [{"shot_id": 1, "voiceover": "", "image_prompt": "A"}],
        [
            {"shot_id": 1, "voiceover": "A", "image_prompt": "A"},
            {"shot_id": 1, "voiceover": "B", "image_prompt": "B"},
        ],
    ],
)
def test_shot_contract_rejects_invalid_storyboards(shots: list[dict]) -> None:
    with pytest.raises(ShotValidationError):
        validate_shots(shots)


def test_image_validator_decodes_the_entire_file(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (320, 180), color=(20, 40, 80)).save(image_path)

    metadata = validate_image_file(image_path)

    assert metadata["width"] == 320
    assert metadata["height"] == 180


def test_image_validator_rejects_fake_png(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    image_path.write_bytes(b"not an image" * 20)

    with pytest.raises(ValueError, match="not decodable"):
        validate_image_file(image_path)


def test_public_error_redacts_credentials_urls_and_local_paths() -> None:
    error = RuntimeError(
        "api_key=secret123 https://example.com/file?signature=private "
        "/Volumes/private-lab/secret-project/output.mp4"
    )

    message = safe_error_message(error)

    assert "secret123" not in message
    assert "signature=private" not in message
    assert "secret-project" not in message
    assert "[REDACTED]" in message
