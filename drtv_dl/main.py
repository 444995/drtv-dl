from drtv_dl.downloader import DRTVDownloader
from drtv_dl.extractor import InfoExtractor, SeasonInfoExtractor, SeriesInfoExtractor
from drtv_dl.exceptions import DRTVDownloaderError
from drtv_dl.logger import logger

def download(url, resolution=None, with_subs=False):
    ie = InfoExtractor()
    sie = SeasonInfoExtractor()

    if '/drtv/serie/' in url:
        extractor = SeriesInfoExtractor()
    elif '/drtv/saeson/' in url:
        extractor = sie
    else:
        extractor = ie

    info = extractor.extract(url)
    downloader = DRTVDownloader()

    if isinstance(info, dict) and 'episode_urls' in info:
        for episode_url in info['episode_urls']:
            episode_info = ie.extract(episode_url)
            downloader.download(episode_info, resolution=resolution, with_subs=with_subs)
    elif isinstance(info, list):
        for season in info:
            saeson_info = sie.extract(season)
            for episode_url in saeson_info['episode_urls']:
                episode_info = ie.extract(episode_url)
                downloader.download(episode_info, resolution=resolution, with_subs=with_subs)
    else:
        downloader.download(info, resolution=resolution, with_subs=with_subs)
