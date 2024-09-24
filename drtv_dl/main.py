from drtv_dl.downloader import Downloader
from drtv_dl.extractor import InfoExtractor, SeasonInfoExtractor, SeriesInfoExtractor
from drtv_dl.exceptions import DRTVDownloaderError
from drtv_dl.logger import logger

def download(url, resolution=None):
    try:
        if '/drtv/serie/' in url:
            extractor = SeriesInfoExtractor()
        elif '/drtv/saeson/' in url:
            extractor = SeasonInfoExtractor()
        else:
            extractor = InfoExtractor()

        info = extractor.extract(url)

        downloader = Downloader()

        if isinstance(info, list):
            for season in info:
                for episode in season['episodes']:
                    downloader.download(episode, resolution=resolution)
        else:
            downloader.download(info, resolution=resolution)

    except Exception as e:
        logger.error(f"Failed to download video: {str(e)}")
        raise DRTVDownloaderError(f"Failed to download video: {str(e)}") from None
