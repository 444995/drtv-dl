from drtv_dl.downloader import DRTVDownloader
from drtv_dl.extractor import InfoExtractor, SeasonInfoExtractor, SeriesInfoExtractor
from drtv_dl.exceptions import DRTVDownloaderError
from drtv_dl.logger import logger

def download(url, resolution=None, with_subs=False):
    try:
        if '/drtv/serie/' in url:
            extractor = SeriesInfoExtractor()
        elif '/drtv/saeson/' in url:
            extractor = SeasonInfoExtractor()
        else:
            extractor = InfoExtractor()

        info = extractor.extract(url)

        downloader = DRTVDownloader()

        if isinstance(info, list):
            for season in info:
                for episode in season['episodes']:
                    downloader.download(episode, resolution=resolution, with_subs=with_subs)
        else:
            downloader.download(info, resolution=resolution, with_subs=with_subs)

    except Exception as e:
        logger.error(f"Failed to download video: {str(e)}")
        raise DRTVDownloaderError(f"Failed to download video: {str(e)}") from None