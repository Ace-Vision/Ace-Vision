"""
tools/build_baseline.py — Build expert baseline JSON from a folder of videos.

Run this script once whenever you have new expert footage.
It processes every .mp4 in a folder, detects the three serve checkpoints in
each video, records the joint angles at each checkpoint, then averages across
all videos to produce a new baseline JSON.

Usage:
    python tools/build_baseline.py \\
        --videos_dir  data/expert_videos/tennis \\
        --sport_type  tennis_serve \\
        --output      data/reference/tennis_baselines.json

The output file will have this structure:
{
  "trophy":      { "right_elbow_flexion": {"mean": ..., "std": ...}, ... },
  "racket_drop": { ... },
  "contact":     { ... }
}
"""

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

# Add the repo root to sys.path so we can import the ml/ modules
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from ml import extractor, calculator
from ml.scorer import _find_trophy_frame, _find_racket_drop_frame, _find_contact_frame


def collect_checkpoint_angles(video_path: str) -> dict:
    """
    Process one expert video and return the joint angles at each checkpoint.

    Steps:
    1. Extract pose keypoints from every frame (extractor.py)
    2. Calculate joint angles from the keypoints (calculator.py)
    3. Detect the three checkpoints
    4. Return the angles at each detected checkpoint

    Args:
        video_path: path to the expert video .mp4 file

    Returns:
        dict like:
        {
          "trophy":      { "right_elbow_flexion": 91.2, ... }  or None,
          "racket_drop": { ... }                                or None,
          "contact":     { ... }                                or None,
        }
        A checkpoint is None if it could not be detected in this video.
    """
    print(f"  Processing: {video_path}")

    # Step 1 + 2: run the same pipeline stages as the live app
    keypoints_list = extractor.extract_keypoints(video_path)
    angles_list    = calculator.calculate_angles(keypoints_list)

    # Step 3: detect the three checkpoints
    trophy_frame      = _find_trophy_frame(keypoints_list)
    racket_drop_frame = _find_racket_drop_frame(keypoints_list, after_frame=trophy_frame or 0)
    contact_frame     = _find_contact_frame(angles_list, after_frame=racket_drop_frame or 0)

    print(f"    trophy={trophy_frame}, racket_drop={racket_drop_frame}, contact={contact_frame}")

    # Step 4: extract the angles at each checkpoint
    def angles_at(frame_idx):
        if frame_idx is None:
            return None
        angles = angles_list[frame_idx] if frame_idx < len(angles_list) else {}
        # Remove None values (joints that couldn't be measured)
        return {k: v for k, v in angles.items() if v is not None}

    return {
        "trophy":      angles_at(trophy_frame),
        "racket_drop": angles_at(racket_drop_frame),
        "contact":     angles_at(contact_frame),
    }


def build_baselines(videos_dir: str, output_path: str) -> None:
    """
    Process all .mp4 files in videos_dir, average angles at each checkpoint,
    and write the nested baseline JSON to output_path.

    Args:
        videos_dir:   folder containing expert .mp4 videos
        output_path:  where to write the output JSON
    """
    # Find all video files in the directory (.mp4 and .avi both work)
    video_files = []
    for ext in ("*.mp4", "*.avi", "*.MP4", "*.AVI"):
        video_files.extend(Path(videos_dir).glob(ext))

    if not video_files:
        print(f"No video files (.mp4 or .avi) found in {videos_dir}")
        return

    print(f"Found {len(video_files)} video(s) in {videos_dir}\n")

    # Accumulate angles per checkpoint per joint across all videos.
    # Structure: all_angles[checkpoint_name][joint_name] = [angle1, angle2, ...]
    all_angles: dict[str, dict[str, list[float]]] = {
        "trophy":      {},
        "racket_drop": {},
        "contact":     {},
    }

    for video_path in video_files:
        result = collect_checkpoint_angles(str(video_path))

        # Add each joint's angle to the accumulator list
        for checkpoint_name, angles in result.items():
            if angles is None:
                print(f"    Warning: could not detect '{checkpoint_name}' in {video_path.name}")
                continue
            for joint, angle in angles.items():
                if joint not in all_angles[checkpoint_name]:
                    all_angles[checkpoint_name][joint] = []
                all_angles[checkpoint_name][joint].append(angle)

    print("\nComputing means and standard deviations...")

    # Build the final nested baseline dict
    baselines = {}

    for checkpoint_name, joint_data in all_angles.items():
        baselines[checkpoint_name] = {}

        for joint, angle_list in joint_data.items():
            mean = statistics.mean(angle_list)

            # Need at least 2 values to compute a real std dev.
            # Fall back to 5.0 degrees if we only have one video.
            if len(angle_list) >= 2:
                std = statistics.stdev(angle_list)
                # Clamp std to a minimum of 2.0 so severity scores are meaningful
                std = max(std, 2.0)
            else:
                std = 5.0
                print(f"    Warning: only 1 sample for {checkpoint_name}/{joint} — using std=5.0")

            baselines[checkpoint_name][joint] = {
                "mean": round(mean, 2),
                "std":  round(std, 2),
            }

        n_videos = len(video_files)
        print(f"  {checkpoint_name}: averaged {len(joint_data)} joints across {n_videos} video(s)")

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(baselines, f, indent=2)

    print(f"\nBaselines written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build expert baseline JSON from a folder of serve videos"
    )
    parser.add_argument(
        "--videos_dir",
        required=True,
        help="Folder containing expert .mp4 videos",
    )
    parser.add_argument(
        "--sport_type",
        required=True,
        choices=["tennis_serve", "badminton"],
        help="Which sport these videos are for",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the baseline JSON (e.g. data/reference/tennis_baselines.json)",
    )
    args = parser.parse_args()

    print(f"Building {args.sport_type} baselines from: {args.videos_dir}\n")
    build_baselines(args.videos_dir, args.output)


if __name__ == "__main__":
    main()
