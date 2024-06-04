import subprocess
import re
import os
from datetime import datetime
import argparse
from subtoaudiomod import SubToAudio

def get_args():
    # Create the parser
    parser = argparse.ArgumentParser(description="Shrink video by reducing silence duration")

    # Add the arguments
    parser.add_argument("input_video", nargs='?', help="The filepath of the video to shrink", default="video/lecture-1.1.mp4")
    parser.add_argument("input_subtitle",nargs='?',  help="The filepath of the subtitle file to use", default="srt/lecture-1.1-captions.mod.srt")
    parser.add_argument("silence_threshold", nargs='?', help="The silence threshold in dB", default="-30dB")
    parser.add_argument("min_silence_duration", nargs='?', type=int, help="The minimum silence duration in seconds", default=3)
    parser.add_argument("new_silence_duration", nargs='?', type=int, help="The new silence duration in seconds", default=1)

    # Parse the arguments
    return parser.parse_args()


def check_if_file_created(file_path):
    if os.path.exists(file_path):
        print_in_green(f"# Created {file_path}")
    else:
        print_in_red(f"# Failed to create {file_path}")
        exit(1)


def shell_command(command):
    """
    Run a shell command and return the output
    """
    print_in_green("# Running command: "+ ' '.join(command))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
    for line in process.stdout:
        print(line)


def build_output_video_path(input_video, type):
    """
    Build output file name
    """
    # Get the base name and extension of the file
    base_name, extension = os.path.splitext(input_video)

    # Get current date and time
    # Format as a string
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create a new filename with "shrinked" and datetime appended
    output_video = f"{base_name}.{type}.{datetime_str}{extension}"
    return output_video 


def build_output_audio_path(input_video):
    """
    Build output file name
    """
    # Get the base name and extension of the file
    base_name, extension = os.path.splitext(input_video)

    # Get current date and time
    # Format as a string
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create a new filename with "shrinked" and datetime appended
    output_audio_filename = f"{base_name}.audio.{datetime_str}.wav"
    return output_audio_filename


def create_filter(start, end, count):
    """
    Create FFmpeg filter for trimming video and audio
    """
    if end == "":
        return (f"[0:v]trim=start={start},setpts=PTS-STARTPTS[v{count}];"
            f"[0:a]atrim=start={start},asetpts=PTS-STARTPTS[a{count}];")
    else:
        return (f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{count}];"
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{count}];")


def print_in_green(text):
    print("\033[92m {}\033[00m" .format(text))


def print_in_red(text):
    print("\033[91m {}\033[00m" .format(text))


def extract_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold):
    # Extract silence timestamps
    ffmpeg_command = [
        'ffmpeg', '-i', output_video_path_merged, '-af',
        f'silencedetect=n={silence_threshold}:d={min_silence_duration}', '-f', 'null', '-'
    ]
    shell_command(ffmpeg_command)
    result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
    silence_output = result.stderr
    # Parse silence timestamps
    silence_pattern = re.compile(r' silence_(start|end): (\d+(\.\d+)?)')
    silence_events = silence_pattern.findall(silence_output)
    # Group start and end times adding new_silence_duration to end time
    silence_intervals = []
    for i in range(0, len(silence_events), 2):
        start_time = float(silence_events[i][1])
        end_time = float(silence_events[i+1][1])
        silence_intervals.append((start_time, end_time))

    return silence_intervals

def extract_non_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold):
    silence_intervals = extract_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold)
    non_silence_intervals = []
    start_time = 0
    for silence_start, silence_end in silence_intervals:
        non_silence_intervals.append((start_time, silence_start))
        start_time = silence_end

    return non_silence_intervals


def create_video_chunks(video_path, non_silence_intervals, new_silence_added_duration):
    for i, (start_time, end_time) in enumerate(non_silence_intervals):
        chunk_path = f'out{i:03}.mp4'
        ffmpeg_command = [
        'ffmpeg', '-i', video_path, '-ss', str(start_time), '-to', str(end_time + new_silence_added_duration), '-c', 'copy', f'out{i:03}.mp4'
        ]
        #shell_command(ffmpeg_command)
        result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
        check_if_file_created(chunk_path)


def merge_video_chunks(video_path, non_silence_intervals, video_path_final):
    ffmpeg_command = [
    'ffmpeg', '-i', 'concat:"' + '|'.join([f'out{i:03}.mp4' for i in range(len(non_silence_intervals))]) + '"', '-c', 'copy', video_path_final
    ]
    shell_command(ffmpeg_command)
    result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
    check_if_file_created(video_path_final)


def main():
    # Get the arguments
    args = get_args()
    input_video_path = "video/render1.2.mp4"
    output_video_path_merged = "video/render1.2.merged.2024-06-03_23-23-11.mp4"
    output_video_path_final = build_output_video_path(input_video_path, "merged.shrinked")
    silence_threshold = args.silence_threshold
    min_silence_duration = args.min_silence_duration
    new_silence_duration = args.new_silence_duration

    # Extract non-silence intervals
    non_silence_intervals = extract_non_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold)
    # Create video chunks
    create_video_chunks(output_video_path_merged, non_silence_intervals, new_silence_duration)
    # Merge video chunks
    merge_video_chunks(output_video_path_merged, non_silence_intervals, output_video_path_final)

if __name__ == "__main__":
    main()