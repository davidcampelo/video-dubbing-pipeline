import subprocess
import re
import os
from datetime import datetime
import argparse
from subtoaudiomod import SubToAudio
from moviepy.editor import VideoFileClip

TEMP_VIDEOCHUNK_PATH = "/tmp/out"

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

def cleanup_files():
    # Remove all .ts files
    ts_files = [f'{TEMP_VIDEOCHUNK_PATH}{i:03}.ts' for i in range(1000)]
    for ts_file in ts_files:
        if os.path.exists(ts_file):
            os.remove(ts_file)
            print_in_green(f"# Removed {ts_file}")

    # Remove all .mp4 files
    mp4_files = [f'{TEMP_VIDEOCHUNK_PATH}{i:03}.mp4' for i in range(1000)]
    for mp4_file in mp4_files:
        if os.path.exists(mp4_file):
            os.remove(mp4_file)
            print_in_green(f"# Removed {mp4_file}")


def create_tts_audio(input_subtitle_path, output_audio_path):
    # Step 1: Create new audio based on subtitle
        #best speakers :
        #'Viktor Eka'
        #'Luis Moray'
        #'Torcull Diarmuid'
    _speaker = 'Torcull Diarmuid'
    models = SubToAudio().coqui_model()
    sub = SubToAudio(model_name=models[0], progress_bar=True)
    subtitle = sub.subtitle(input_subtitle_path)
    print_in_green(" Subtitle has ["+str(len(subtitle))+"] lines...")
    sub.convert_to_audio(sub_data=subtitle, speaker=_speaker, output_path=output_audio_path)
    check_if_file_created(output_audio_path)


def merge_ttsaudio_with_original_video(input_video_path, output_audio_path, output_video_path_merged):
        # Step 2: Merge original video with new audio
    ffmpeg_command = [  
        'ffmpeg', '-i', input_video_path,  '-i', output_audio_path, 
        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-shortest', output_video_path_merged
    ]
    shell_command(ffmpeg_command)
    check_if_file_created(output_video_path_merged)


def get_video_duration(video_path):
    video = VideoFileClip(video_path)
    duration = video.duration
    video.close()
    return duration


def extract_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold):
    # Extract silence timestamps
    ffmpeg_command = [
        'ffmpeg', '-i', output_video_path_merged, '-af',
        f'silencedetect=n={silence_threshold}:d={min_silence_duration}', '-f', 'null', '-'
    ]
    print_in_green("# Running command: "+ ' '.join(ffmpeg_command))
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
    non_silence_intervals.append((start_time, get_video_duration(output_video_path_merged)))

    return non_silence_intervals


def create_video_chunks(video_path, non_silence_intervals, new_silence_added_duration):
    # Get video duration to check for end time overflow
    video_duration = max(non_silence_intervals, key=lambda interval: interval[1])[1]
    for i, (start_time, end_time) in enumerate(non_silence_intervals):
        # Check for end time overflow
        if (video_duration < end_time + new_silence_added_duration):
            end_time = video_duration
        else:
            end_time = end_time + new_silence_added_duration
        # Build ffmpeg command for each chunk
        chunk_base_path = f'{TEMP_VIDEOCHUNK_PATH}{i:03}'
        ffmpeg_command = [
        'ffmpeg', '-i', video_path, '-ss', str(start_time), '-to', str(end_time), '-c', 'copy', chunk_base_path +'.mp4'
        ]
        print_in_green("# Running command: "+ ' '.join(ffmpeg_command))
        result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
        check_if_file_created(chunk_base_path+'.mp4')
        # Convert each chunk to .ts format
        ffmpeg_command = [
        'ffmpeg', '-i', f'{TEMP_VIDEOCHUNK_PATH}{i:03}.mp4', '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts', chunk_base_path+'.ts'
        ]
        print_in_green("# Running command: "+ ' '.join(ffmpeg_command))
        result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
        check_if_file_created(chunk_base_path+'.ts')


def merge_video_chunks(video_path, non_silence_intervals, video_path_final):
    # First, create a list of all the .ts files
    ts_files = [f'{TEMP_VIDEOCHUNK_PATH}{i:03}.ts' for i in range(len(non_silence_intervals))]
    # Then, create a string with all the .ts files for the filter_complex parameter
    filter_complex_string = ''.join([f'[{i}:v:0][{i}:a:0]' for i in range(len(ts_files))]) + 'concat=n=' + str(len(ts_files)) + ':v=1:a=1[outv][outa]'
    # Finally, create the FFmpeg command
    ffmpeg_command = ['ffmpeg'] + [item for ts_file in ts_files for item in ['-i', ts_file]] + \
                     ['-filter_complex', filter_complex_string, '-map', '[outv]', '-map', '[outa]', video_path_final]
    shell_command(ffmpeg_command)
    check_if_file_created(video_path_final)
