# MKV Subtitle Extractor

A Python script to extract Japanese subtitles from MKV video files and merge them with corresponding English subtitles (.ass or .srt) into combined SRT files.

I created this project while watching *Terrace House: Boys × Girls Next Door* from local MKV files. For language immersion, I wanted subtitles displayed side by side to quickly filter out unknown words and patterns that I don't recognize.

## Features

- Extracts embedded Japanese subtitles from MKV files using ffmpeg.
- Finds and converts English subtitles (.ass to .srt if needed).
- Merges Japanese and English subtitles into a single SRT file with UTF-8 encoding.
- Outputs combined SRT files in the same directory as the MKV files.
- Skips processing if SRT already exists.

## Requirements

- Python 3.6+
- ffmpeg and ffprobe (install from https://ffmpeg.org/download.html)
- pysrt library: `pip install pysrt`

## Installation

1. Clone or download this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure ffmpeg is installed and in your PATH.

## Usage

Run the script with the input folder containing MKV and subtitle files:

```bash
python extract.py --input-folder /path/to/your/mkv/folder
```

Optional: Specify an output folder to mirror the input structure:

```bash
python extract.py --input-folder /path/to/input --output-folder /path/to/output
```

The script will process all MKV files recursively, creating `{video_name}.srt` files next to each MKV.

## Example

If you have:
- `show.S01E01.mkv` (with embedded Japanese subs)
- `show.S01E01.ass` (English subs)

Running the script will create:
- `show.S01E01.srt` (combined Japanese + English)

Sample content from `show.S01E01.srt`:

```
1
00:00:01,000 --> 00:00:04,000
こんにちは
Hello

2
00:00:05,000 --> 00:00:08,000
今日はいい天気ですね
It's a nice day today
```

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature-name`
5. Open a pull request.

## License

MIT License