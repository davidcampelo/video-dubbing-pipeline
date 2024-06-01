import subprocess
import re

input_video = 'video/lecture-1.1.en.mp4'
output_video = 'video/lecture-1.1.en.shrinked.mp4'
silence_threshold = '-30dB'
min_silence_duration = 3
new_silence_duration = 1

# Step 1: Extract silence timestamps
ffmpeg_command = [
    'ffmpeg', '-i', input_video, '-af',
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
        filters.append(f"[0:v]trim=start={current_position}:end={start_time + new_silence_duration},setpts=PTS-STARTPTS[v{count}];"
                       f"[0:a]atrim=start={current_position}:end={start_time + new_silence_duration},asetpts=PTS-STARTPTS[a{count}];")
        count = count + 1 
    else:
        print(f">>>>>>>>>>> Not supposed to happen! start={start_time} current={current_position}")
    
    current_position = end_time
    break

filters.append(f"[0:v]trim=start={current_position},setpts=PTS-STARTPTS[v{count}];"
               f"[0:a]atrim=start={current_position},asetpts=PTS-STARTPTS[a{count}];")


filter_complex = "".join(filters) + "".join(f"[v{i}][a{i}]" for i in range(count+1)) + f"concat=n={count+1}:v=1:a=1[v][a]"

# Step 4: Run FFmpeg with filter_complex
ffmpeg_concat_command = [
    'ffmpeg', '-i', input_video,  '-filter_complex', '"' + filter_complex + '"',
    '-map', '"[v]"', '-map', '"[a]"', output_video
]
ffmpeg_command_string = ' '.join(ffmpeg_concat_command)
print("FFmpeg command:", ffmpeg_command_string)


#subprocess.run(ffmpeg_concat_command)

