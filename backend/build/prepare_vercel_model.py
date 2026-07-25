"""Prepare E5 model files as small, balanced Vercel container layers."""

from __future__ import annotations

import shutil
from pathlib import Path

from transformers import AutoModel, AutoTokenizer

MODEL_ID = "intfloat/e5-base-v2"
MODEL_DIRECTORY = Path("/tmp/e5-base-v2")
LAYERS_DIRECTORY = Path("/tmp/model-layers")
LAYER_COUNT = 8
MAX_SINGLE_FILE_BYTES = 120 * 1024 * 1024


def main() -> None:
    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)
    tokenizer.save_pretrained(MODEL_DIRECTORY)
    model.save_pretrained(
        MODEL_DIRECTORY,
        safe_serialization=True,
        max_shard_size="64MB",
    )

    layer_directories = [
        LAYERS_DIRECTORY / f"{index:02d}"
        for index in range(1, LAYER_COUNT + 1)
    ]
    for directory in layer_directories:
        directory.mkdir(parents=True, exist_ok=True)

    layer_sizes = [0] * LAYER_COUNT
    model_files = sorted(
        (path for path in MODEL_DIRECTORY.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )
    if not model_files:
        raise RuntimeError("The downloaded model directory is empty")

    for source_path in model_files:
        file_size = source_path.stat().st_size
        if file_size > MAX_SINGLE_FILE_BYTES:
            raise RuntimeError(
                f"Model file is too large for a Vercel layer: "
                f"{source_path.name} ({file_size} bytes)"
            )
        target_index = min(range(LAYER_COUNT), key=layer_sizes.__getitem__)
        shutil.move(
            str(source_path),
            layer_directories[target_index] / source_path.name,
        )
        layer_sizes[target_index] += file_size

    print(
        "Prepared model layer sizes (bytes): "
        + ", ".join(str(size) for size in layer_sizes)
    )


if __name__ == "__main__":
    main()
