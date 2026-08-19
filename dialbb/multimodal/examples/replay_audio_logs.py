#!/usr/bin/env python3
"""Build and optionally play a stereo replay from audio_logs manifest.jsonl.

Usage:
  python dialbb/multimodal/examples/replay_audio_logs.py \
      audio_logs/<session_id>/manifest.jsonl --play

Default channel assignment:
- left : user
- right: system

The script aligns clips by start timestamp and mixes overlaps on each track.

For old manifests that only have timestamp_ns, default mode (auto) treats
user timestamp_ns as end-of-utterance and compensates by subtracting duration.
"""

from __future__ import annotations

import argparse
import json
import platform
import wave
from array import array
from pathlib import Path
from typing import cast
from typing import Iterable

TARGET_WIDTH_BYTES = 2  # 16-bit PCM
TARGET_RATE = 16000
DEFAULT_USER_TIMESTAMP_MODE = "auto"


def _read_manifest(manifest_path: Path) -> list[dict]:
    records: list[dict] = []
    with manifest_path.open("r", encoding="utf-8") as fp:
        for index, line in enumerate(fp, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {index}: {exc}") from exc
            records.append(record)

    if not records:
        raise ValueError(f"No entries in manifest: {manifest_path}")

    records.sort(
        key=lambda r: (
            int(r.get("start_timestamp_ns", r.get("timestamp_ns", 0))),
            int(r.get("sequence", 0)),
        )
    )
    return records


def _duration_ns_from_samples(sample_count: int, sample_rate: int) -> int:
    return int(round(sample_count * 1_000_000_000 / sample_rate))


def _resolve_start_timestamp_ns(
    record: dict,
    source: str,
    duration_ns: int,
    timestamp_mode: str,
) -> int:
    timestamp_ns = int(record.get("timestamp_ns", 0))
    start_timestamp_ns = record.get("start_timestamp_ns")
    end_timestamp_ns = record.get("end_timestamp_ns")

    if timestamp_mode == "start":
        if start_timestamp_ns is not None:
            return int(start_timestamp_ns)
        return timestamp_ns

    if timestamp_mode == "end":
        if end_timestamp_ns is not None:
            return int(end_timestamp_ns) - duration_ns
        return timestamp_ns - duration_ns

    # auto mode
    if start_timestamp_ns is not None:
        return int(start_timestamp_ns)
    if end_timestamp_ns is not None:
        return int(end_timestamp_ns) - duration_ns
    if source == "user":
        return timestamp_ns - duration_ns
    return timestamp_ns


def _clip_to_int16(value: int) -> int:
    if value > 32767:
        return 32767
    if value < -32768:
        return -32768
    return value


def _convert_pcm_to_mono_int16(pcm: bytes, sample_width: int, channels: int) -> list[int]:
    if channels < 1:
        raise ValueError(f"Invalid channel count: {channels}")

    frame_size = sample_width * channels
    if frame_size <= 0:
        raise ValueError("Invalid frame size")

    usable = (len(pcm) // frame_size) * frame_size
    pcm = pcm[:usable]

    if sample_width == 1:
        decoded = [((b - 128) << 8) for b in pcm]
    elif sample_width == 2:
        decoded_arr = array("h")
        decoded_arr.frombytes(pcm)
        decoded = [int(v) for v in decoded_arr]
    elif sample_width == 4:
        decoded = []
        for i in range(0, len(pcm), 4):
            v = int.from_bytes(pcm[i:i + 4], byteorder="little", signed=True)
            decoded.append(v >> 16)
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    if channels == 1:
        return decoded

    mono: list[int] = []
    for i in range(0, len(decoded), channels):
        frame = decoded[i:i + channels]
        if not frame:
            continue
        mono.append(int(sum(frame) / len(frame)))
    return mono


def _resample_linear(samples: list[int], source_rate: int, target_rate: int) -> list[int]:
    if source_rate == target_rate:
        return samples
    if not samples:
        return []
    if len(samples) == 1:
        out_len = max(1, int(round(target_rate / source_rate)))
        return [samples[0]] * out_len

    out_len = max(1, int(round(len(samples) * target_rate / source_rate)))
    resampled: list[int] = []
    for i in range(out_len):
        src_pos = i * source_rate / target_rate
        left = int(src_pos)
        if left >= len(samples) - 1:
            resampled.append(samples[-1])
            continue
        frac = src_pos - left
        v = samples[left] * (1.0 - frac) + samples[left + 1] * frac
        resampled.append(int(round(v)))
    return resampled


def _decode_wav_to_target_pcm(wav_path: Path, target_rate: int) -> array:
    with wave.open(str(wav_path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        source_rate = wf.getframerate()
        frames = wf.getnframes()
        pcm = wf.readframes(frames)

    mono_samples = _convert_pcm_to_mono_int16(pcm, sample_width, channels)
    if source_rate != target_rate:
        mono_samples = _resample_linear(mono_samples, source_rate, target_rate)

    samples = array("h", (_clip_to_int16(v) for v in mono_samples))
    return samples


def _ensure_length(buf: list[int], required: int) -> None:
    if required <= len(buf):
        return
    buf.extend([0] * (required - len(buf)))


def _mix_into(buf: list[int], start_index: int, samples: Iterable[int]) -> None:
    samples_list = list(samples)
    _ensure_length(buf, start_index + len(samples_list))
    for offset, value in enumerate(samples_list):
        buf[start_index + offset] += int(value)


def _interleave_stereo(left: list[int], right: list[int]) -> array:
    length = max(len(left), len(right))
    _ensure_length(left, length)
    _ensure_length(right, length)

    interleaved = array("h")
    for i in range(length):
        interleaved.append(_clip_to_int16(left[i]))
        interleaved.append(_clip_to_int16(right[i]))
    return interleaved


def _write_stereo_wav(path: Path, samples: array, sample_rate: int) -> None:
    wf = cast(wave.Wave_write, wave.open(str(path), "wb"))
    try:
        wf.setnchannels(2)
        wf.setsampwidth(TARGET_WIDTH_BYTES)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    finally:
        wf.close()


def _play_wav(path: Path) -> None:
    if platform.system().lower().startswith("win"):
        import winsound  # pylint: disable=import-outside-toplevel

        print(f"Playing: {path}")
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return

    print("Automatic playback is currently implemented only for Windows.")
    print(f"Generated file: {path}")


def build_stereo_replay(
    manifest_path: Path,
    output_path: Path,
    left_source: str,
    right_source: str,
    sample_rate: int,
    user_timestamp_mode: str,
) -> dict:
    records = _read_manifest(manifest_path)
    prepared_entries: list[tuple[str, array, int]] = []

    mixed_entries = 0
    skipped_entries = 0

    for record in records:
        source = str(record.get("source", "")).strip().lower()
        audio_format = str(record.get("audio_format", "")).strip().lower()
        file_name = str(record.get("file_name", "")).strip()

        if not file_name:
            skipped_entries += 1
            continue

        if audio_format != "wav":
            print(f"Skipping non-wav entry: {file_name} ({audio_format})")
            skipped_entries += 1
            continue

        wav_path = manifest_path.parent / file_name
        if not wav_path.exists():
            print(f"Skipping missing file: {wav_path}")
            skipped_entries += 1
            continue

        if source not in {left_source, right_source}:
            print(f"Skipping unknown source entry: {file_name} (source={source})")
            skipped_entries += 1
            continue

        samples = _decode_wav_to_target_pcm(wav_path, sample_rate)
        duration_ns = _duration_ns_from_samples(len(samples), sample_rate)
        start_timestamp_ns = _resolve_start_timestamp_ns(record, source, duration_ns, user_timestamp_mode)
        prepared_entries.append((source, samples, start_timestamp_ns))
        mixed_entries += 1

    if not prepared_entries:
        raise ValueError("No playable wav entries found in manifest")

    t0 = min(start_ts for _, _, start_ts in prepared_entries)

    left_track: list[int] = []
    right_track: list[int] = []

    for source, samples, start_timestamp_ns in prepared_entries:
        start_index = max(0, int(round((start_timestamp_ns - t0) * sample_rate / 1_000_000_000)))

        if source == left_source:
            _mix_into(left_track, start_index, samples)
        else:
            _mix_into(right_track, start_index, samples)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stereo = _interleave_stereo(left_track, right_track)
    _write_stereo_wav(output_path, stereo, sample_rate)

    return {
        "mixed_entries": mixed_entries,
        "skipped_entries": skipped_entries,
        "total_entries": len(records),
        "duration_sec": (len(stereo) // 2) / sample_rate,
        "output_path": output_path,
        "user_timestamp_mode": user_timestamp_mode,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a stereo replay wav from manifest.jsonl. "
            "Default: left=user, right=system."
        )
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to manifest.jsonl under audio_logs/<session_id>/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output wav path (default: <manifest_dir>/replay_stereo.wav)",
    )
    parser.add_argument("--left-source", default="user", help="Source name for left channel")
    parser.add_argument("--right-source", default="system", help="Source name for right channel")
    parser.add_argument("--sample-rate", type=int, default=TARGET_RATE, help="Output sample rate")
    parser.add_argument(
        "--user-timestamp-mode",
        choices=["auto", "start", "end"],
        default=DEFAULT_USER_TIMESTAMP_MODE,
        help=(
            "How to interpret timestamp when start/end fields are unavailable. "
            "auto: user=end/system=start, start: all start, end: all end"
        ),
    )
    parser.add_argument("--play", action="store_true", help="Play output file after generating it")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    manifest_path: Path = args.manifest
    if not manifest_path.exists():
        parser.error(f"Manifest not found: {manifest_path}")

    output_path: Path = args.output or (manifest_path.parent / "replay_stereo.wav")
    left_source = str(args.left_source).strip().lower()
    right_source = str(args.right_source).strip().lower()

    if left_source == right_source:
        parser.error("--left-source and --right-source must be different")

    result = build_stereo_replay(
        manifest_path=manifest_path,
        output_path=output_path,
        left_source=left_source,
        right_source=right_source,
        sample_rate=int(args.sample_rate),
        user_timestamp_mode=str(args.user_timestamp_mode),
    )

    print("Stereo replay generated")
    print(f"  output        : {result['output_path']}")
    print(f"  total entries : {result['total_entries']}")
    print(f"  mixed entries : {result['mixed_entries']}")
    print(f"  skipped       : {result['skipped_entries']}")
    print(f"  duration (s)  : {result['duration_sec']:.3f}")
    print(f"  ts mode       : {result['user_timestamp_mode']}")

    if args.play:
        _play_wav(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
