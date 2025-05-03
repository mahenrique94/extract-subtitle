from whisper.utils import get_writer

import argparse
import os
import whisper


print("Setting up requirements")
parser = argparse.ArgumentParser()
print("Defining command line arguments")
parser.add_argument("--file", dest="file", type=str, help="MP3 file to extract the subtitles")
parser.add_argument("--home", dest="home", type=str, default=os.getenv('HOME'), help="User home directory")
parser.add_argument("--source", dest="source", type=str, default="Downloads", help="Folder to look for video and write subtitles")
parser.add_argument("--translate", dest="translate", type=str, help="Language to subtitles be translated to")
print("Parsing command line arguments")
args = parser.parse_args()


if args.file is None:
  raise Exception("You need to provide a file to extract the subtitles")

print("Loading whisper model...")
model = whisper.load_model("large")


print("Getting source folder")
source_folder = f"{args.home}/{args.source}"
print("Getting mp3 folder")
file_path = f"{source_folder}/{args.file}"


should_be_translated = args.translate is not None
task = "translate" if should_be_translated else "transcribe"
if should_be_translated: 
  print(f"The clips will be translated to {args.translate}")

print("Extracting subtitles from audio file...")
transcription = model.transcribe(file_path, language=args.translate, task=task, verbose=True, word_timestamps=True)

print("Getting SRT writter")
srt_writer = get_writer(output_format="srt", output_dir=source_folder)

print("Writing srt file...")
srt_writer(transcription, file_path, {
  "highlight_words": False,
  "max_line_count": 1,
  "max_line_width": 16
})
