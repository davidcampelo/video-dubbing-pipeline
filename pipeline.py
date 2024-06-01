import subprocess
import re
import os
from datetime import datetime
import argparse
from subtoaudiomod import SubToAudio


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
    output_audio_filename = f"{base_name}.audio.{datetime_str}"
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
    print(f"\033[92m{text}\033[00m")

# Create the parser
parser = argparse.ArgumentParser(description="Shrink video by reducing silence duration")

# Add the arguments
parser.add_argument("input_video", nargs='?', help="The filepath of the video to shrink", default="video/lecture-1.1.mp4")
parser.add_argument("input_subtitle",nargs='?',  help="The filepath of the subtitle file to use", default="srt/lecture-1.1-captions.mod.srt")
parser.add_argument("silence_threshold", nargs='?', help="The silence threshold in dB", default="-30dB")
parser.add_argument("min_silence_duration", nargs='?', type=int, help="The minimum silence duration in seconds", default=3)
parser.add_argument("new_silence_duration", nargs='?', type=int, help="The new silence duration in seconds", default=1)

# Parse the arguments
args = parser.parse_args()

# Use the arguments
input_video_path = args.input_video
input_subtitle_path = args.input_subtitle
output_audio_path = "audio/lecture-1.1-captions_Torcull.wav" #build_output_audio_path(input_video_path)
output_video_path_merged = build_output_video_path(input_video_path, "merged")
output_video_path_final = build_output_video_path(input_video_path, "final_shrinked")
silence_threshold = args.silence_threshold
min_silence_duration = args.min_silence_duration
new_silence_duration = args.new_silence_duration


# Step 0: Create new audio based on subtitle
    #best speakers :
    #'Viktor Eka'
    #'Luis Moray'
    #'Torcull Diarmuid'
_speaker = 'Torcull Diarmuid'
models = SubToAudio().coqui_model()
sub = SubToAudio(model_name=models[0], progress_bar=True)


subtitle = sub.subtitle(input_subtitle_path)
print(" Subtitle has ["+str(len(subtitle))+"] lines...")
sub.convert_to_audio(sub_data=subtitle, speaker=_speaker, output_path=output_audio_path)


# Step 00: Merge audio and video
ffmpeg_concat_command = [  
    'ffmpeg', '-i', input_video_path,  '-i', output_audio_path, 
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-shortest', output_video_path_merged
]
process = subprocess.Popen(ffmpeg_concat_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
for line in process.stdout:
    print(line)
print_in_green("# Created merged video: "+ output_video_path_merged)


# Step 1: Extract silence timestamps
ffmpeg_command = [
    'ffmpeg', '-i', output_video_path_merged, '-af',
    f'silencedetect=n={silence_threshold}:d={min_silence_duration}', '-f', 'null', '-'
]

result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
silence_output = result.stderr

# Step 2: Parse silence timestamps
silence_pattern = re.compile(r' silence_(start|end): (\d+(\.\d+)?)')
silence_events = silence_pattern.findall(silence_output)

# Group start and end times
silence_intervals = []
for i in range(0, len(silence_events), 2):
    start_time = float(silence_events[i][1])
    end_time = float(silence_events[i+1][1])
    silence_intervals.append((start_time, end_time))

# Step 3: Create FFmpeg trim and concat commands
filters = []
current_position = 0
count = 0
for i, (start_time, end_time) in enumerate(silence_intervals):
    if start_time - current_position > 0:
        filters.append(create_filter(current_position, start_time + new_silence_duration, count))
        count = count + 1 
    else:
        print(f">>>>>>>>>>> Not supposed to happen! start={start_time} current={current_position}")
    
    current_position = end_time

filters.append(create_filter(current_position, "", count))


filter_complex = "".join(filters) + "".join(f"[v{i}][a{i}]" for i in range(count+1)) + f"concat=n={count+1}:v=1:a=1[v][a]"

# Step 4: Run FFmpeg with filter_complex
ffmpeg_concat_command = [
    'ffmpeg', '-i', output_video_path_merged, '-filter_complex', filter_complex,
    '-map', '[v]', '-map', '[a]', output_video_path_final
]

process = subprocess.Popen(ffmpeg_concat_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
for line in process.stdout:
    print(line)
print_in_green("# Created final video: "+ output_video_path_final)
