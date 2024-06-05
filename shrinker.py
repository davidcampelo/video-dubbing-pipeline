from utils import get_args, build_output_video_path, cleanup_files, extract_non_silence_intervals, create_video_chunks, merge_video_chunks

def main():
    # Get the arguments
    args = get_args()
    input_video_path = "video/render1.2_no_blink.mp4"
    output_video_path_merged = "video/render1.2_no_blink.merged.2024-06-05_23-03-41.mp4"
    output_video_path_final = build_output_video_path(input_video_path, "merged.shrinked")
    silence_threshold = args.silence_threshold
    min_silence_duration = args.min_silence_duration
    new_silence_duration = args.new_silence_duration

    # Cleanup files
    cleanup_files()
    # Extract non-silence intervals
    non_silence_intervals = extract_non_silence_intervals(output_video_path_merged, min_silence_duration, silence_threshold)
    # Create video chunks
    create_video_chunks(output_video_path_merged, non_silence_intervals, new_silence_duration)
    # Merge video chunks
    merge_video_chunks(output_video_path_merged, non_silence_intervals, output_video_path_final)

if __name__ == "__main__":
    main()