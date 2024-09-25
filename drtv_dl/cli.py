import argparse
from drtv_dl.main import download
from drtv_dl.exceptions import DRTVDownloaderError
from drtv_dl.logger import logger

def parse_args():
    parser = argparse.ArgumentParser(description="Download videos from DR TV")
    parser.add_argument("url", help="URL of the video to download")
    parser.add_argument("--resolution", default="360p", help="Desired video resolution (e.g., 1080p, 720p)")
    parser.add_argument("--log-level", default="INFO", help="Set the logging level")
    parser.add_argument("--with-subs", action="store_true", help="Download with subtitles")
    args = parser.parse_args()

    logger.setLevel(args.log_level.upper())

    download(args.url, resolution=args.resolution, with_subs=args.with_subs)

if __name__ == "__main__":
    parse_args()