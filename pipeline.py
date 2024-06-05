from utils import get_args, build_output_audio_path, build_output_video_path
from utils import cleanup_files, create_tts_audio, merge_ttsaudio_with_original_video, extract_non_silence_intervals, create_video_chunks, merge_video_chunks

def main():
    args = get_args()
    input_video_path = args.input_video
    input_subtitle_path = args.input_subtitle
    output_audio_path = build_output_audio_path(input_video_path)
    output_video_path_merged = build_output_video_path(input_video_path, "merged")
    output_video_path_final = build_output_video_path(input_video_path, "merged.shrinked")
    silence_threshold = args.silence_threshold
    min_silence_duration = args.min_silence_duration
    new_silence_duration = args.new_silence_duration
    # Cleanup files
    cleanup_files()
    # Create TTS audio
    create_tts_audio(input_subtitle_path, output_audio_path)
    # Merge TTS audio with original video
    merge_ttsaudio_with_original_video(input_video_path, output_audio_path, output_video_path_merged)
    # Extract non-silence intervals
    non_silence_intervals = extract_non_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold)
    # Create video chunks
    create_video_chunks(output_video_path_merged, non_silence_intervals, new_silence_duration)
    # Merge video chunks
    merge_video_chunks(output_video_path_merged, non_silence_intervals, output_video_path_final)

if __name__ == "__main__":
    main()
