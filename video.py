import subprocess
from pathlib import Path

def merge_with_ffmpeg(video_path, audio_path, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(output_path)
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Merged into {output_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg failed:", e)

def merge_videos(folder_path, output_path):
    folder = Path(folder_path).resolve()  # Make absolute path
    video_files = sorted(folder.glob("segment_*.mp4"))

    if not video_files:
        print("❌ No .mp4 files found in folder.")
        return

    concat_file = folder / "concat_list.txt"

    # Use absolute paths in list file
    with open(concat_file, "w", encoding="utf-8") as f:
        for file in video_files:
            f.write(f"file '{file.as_posix()}'\n")

    # Build FFmpeg command
    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(Path(output_path).resolve())
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Merged into {output_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg failed to stitch videos:", e)