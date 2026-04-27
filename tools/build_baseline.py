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
from ml.scorer import (
    _find_trophy_frame, _find_racket_drop_frame, _find_contact_frame,
    _find_clear_contact_frame, _find_backswing_frame, _find_follow_through_frame,
)


def collect_checkpoint_angles(video_path: str, sport_type: str = "tennis_serve") -> dict:
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

    # Step 3: detect checkpoints (sport-specific)
    def angles_at(frame_idx):
        if frame_idx is None:
            return None
        angles = angles_list[frame_idx] if frame_idx < len(angles_list) else {}
        return {k: round(v, 2) for k, v in angles.items() if v is not None}

    total_frames = len(keypoints_list)
    print(f"    total frames : {total_frames}")

    if sport_type == "badminton":
        contact_frame        = _find_clear_contact_frame(keypoints_list)
        backswing_frame      = _find_backswing_frame(
            angles_list, before_frame=contact_frame or 0, keypoints_list=keypoints_list
        )
        follow_through_frame = _find_follow_through_frame(
            keypoints_list, after_frame=contact_frame or 0
        )
        print(f"    backswing      : frame {backswing_frame}")
        print(f"    contact        : frame {contact_frame}")
        print(f"    follow_through : frame {follow_through_frame}")
        result = {
            "backswing":      angles_at(backswing_frame),
            "contact":        angles_at(contact_frame),
            "follow_through": angles_at(follow_through_frame),
        }
    else:
        trophy_frame      = _find_trophy_frame(keypoints_list)
        racket_drop_frame = _find_racket_drop_frame(keypoints_list, after_frame=trophy_frame or 0)
        contact_frame     = _find_contact_frame(
            angles_list, after_frame=racket_drop_frame or 0, keypoints_list=keypoints_list
        )
        print(f"    trophy       : frame {trophy_frame}")
        print(f"    racket_drop  : frame {racket_drop_frame}")
        print(f"    contact      : frame {contact_frame}")
        result = {
            "trophy":      angles_at(trophy_frame),
            "racket_drop": angles_at(racket_drop_frame),
            "contact":     angles_at(contact_frame),
        }

    # Print the extracted angles so the user can verify them
    for cp, angles in result.items():
        if angles:
            print(f"\n    [{cp}]")
            for joint, val in angles.items():
                print(f"      {joint:<30} {val:.1f}°")
        else:
            print(f"\n    [{cp}]  ← not detected")

    return result


def build_baselines(videos_dir: str, output_path: str, sport_type: str = "tennis_serve", single_file: str | None = None) -> None:
    """
    Process all .mp4 files in videos_dir, average angles at each checkpoint,
    and write the nested baseline JSON to output_path.

    Args:
        videos_dir:   folder containing expert .mp4 videos
        output_path:  where to write the output JSON
    """
    # Find all video files in the directory (.mp4 and .avi both work)
    if single_file:
        video_files = [Path(single_file)]
    else:
        video_files = []
        for ext in ("*.mp4", "*.avi", "*.MP4", "*.AVI"):
            video_files.extend(Path(videos_dir).glob(ext))

    if not video_files:
        print(f"No video files (.mp4 or .avi) found in {videos_dir}")
        return

    print(f"Found {len(video_files)} video(s) in {videos_dir}\n")

    # Accumulate angles per checkpoint per joint across all videos.
    # Structure: all_angles[checkpoint_name][joint_name] = [angle1, angle2, ...]
    checkpoint_keys = (
        ["backswing", "contact", "follow_through"]
        if sport_type == "badminton"
        else ["trophy", "racket_drop", "contact"]
    )
    all_angles: dict[str, dict[str, list[float]]] = {k: {} for k in checkpoint_keys}

    for video_path in video_files:
        result = collect_checkpoint_angles(str(video_path), sport_type=sport_type)

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
        description="Build expert baseline JSON from expert video(s)"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--video",
        help="Single expert video file (e.g. data/expert/clear.mp4)",
    )
    source.add_argument(
        "--videos_dir",
        help="Folder containing multiple expert .mp4 videos",
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
        help="Output path for the baseline JSON (e.g. data/reference/badminton_baselines.json)",
    )
    args = parser.parse_args()

    if args.video:
        print(f"Building {args.sport_type} baselines from single video: {args.video}\n")
        build_baselines(
            str(Path(args.video).parent), args.output,
            sport_type=args.sport_type, single_file=args.video,
        )
    else:
        print(f"Building {args.sport_type} baselines from: {args.videos_dir}\n")
        build_baselines(args.videos_dir, args.output, sport_type=args.sport_type)


if __name__ == "__main__":
    main()
