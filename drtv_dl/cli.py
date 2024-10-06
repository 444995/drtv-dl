import argparse

from drtv_dl.logger import logger
from drtv_dl.main import download
from drtv_dl.exceptions import DRTVDownloaderError

def parse_args():
    parser = argparse.ArgumentParser(description="Download videos from DR TV")
    parser.add_argument("url", help="URL of the video to download")
    parser.add_argument("--list-formats", action="store_true", help="List available formats")
    parser.add_argument("--resolution", default="360p", help="Desired video resolution (e.g., 1080p, 720p)")
    parser.add_argument("--log-level", default="INFO", help="Set the logging level")
    parser.add_argument("--include-subs", action="store_true", help="Download with subtitles")
    parser.add_argument("--suppress-output", action="store_true", help="Suppress output to the screen")
    args = parser.parse_args()

    logger.setLevel(args.log_level.upper())
    try:
        download(
            url=args.url, 
            list_formats=args.list_formats, 
            resolution=args.resolution, 
            include_subs=args.include_subs,
            suppress_output=args.suppress_output
        )
    except DRTVDownloaderError as e:
        logger.error(f"An error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    parse_args()