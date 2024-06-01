import subprocess
import re
import os
from datetime import datetime


def build_output_file(input_video):
    """
    Build output file name
    """
    # Get the base name and extension of the file
    base_name, extension = os.path.splitext(input_video)

    # Get current date and time
    # Format as a string
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create a new filename with datetime appended
    output_video = f"{base_name}.{datetime_str}{extension}"
    parts = input_video.split('.')
    return f"{parts[0]}_shrinked.{parts[1]}"

def create_filter(start, end, count):
    """
    Create FFmpeg filter for trimming video and audio
    """
    if end == "":
        return (f"[0:v]trim=start={start},setpts=PTS-STARTPTS[v{count}];"
            f"[1:a]atrim=start={start},asetpts=PTS-STARTPTS[a{count}];")
    else:
        return (f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{count}];"
                f"[1:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{count}];")

input_video = 'video/lecture-1.1.mp4'
input_audio = 'audio/audio/lecture-1.1-captions_Torcull.wav'
output_video = build_output_file(input_video)
silence_threshold = '-30dB'
min_silence_duration = 3
new_silence_duration = 1

# Step 1: Extract silence timestamps
ffmpeg_command = [
    'ffmpeg', '-i', input_audio, '-af',
    f'silencedetect=n={silence_threshold}:d={min_silence_duration}', '-f', 'null', '-'
]

result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
silence_output = result.stderr

# Step 2: Parse silence timestamps
silence_pattern = re.compile(r' silence_(start|end): (\d+\.\d+)')
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
    'ffmpeg', '-i', input_video,  '-filter_complex', filter_complex,
    '-map', '[v]', '-map', '[a]', output_video
]

process = subprocess.Popen(ffmpeg_concat_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
for line in process.stdout:
    print(line)

