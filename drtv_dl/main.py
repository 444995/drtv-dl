from drtv_dl.downloader import DRTVDownloader
from drtv_dl.extractor import InfoExtractor, SeasonInfoExtractor, SeriesInfoExtractor
from drtv_dl.exceptions import DRTVDownloaderError
from drtv_dl.logger import logger
from drtv_dl.helpers import print_to_screen

def download(url, resolution=None, with_subs=False):
    print_to_screen(f"Processing URL: {url}")
    ie = InfoExtractor()
    sie = SeasonInfoExtractor(ie)

    if '/drtv/serie/' in url:
        print_to_screen("Identified as a series URL")
        extractor = SeriesInfoExtractor(sie)
    elif '/drtv/saeson/' in url:
        print_to_screen("Identified as a season URL")
        extractor = sie
    else:
        print_to_screen("Identified as an episode URL")
        extractor = ie

    info = extractor.extract(url)
    downloader = DRTVDownloader()

    if isinstance(info, dict) and 'episode_urls' in info:
        print_to_screen(f"Starting download of season {info.get('season_number', '')}")
        for idx, episode_url in enumerate(info['episode_urls'], start=1):
            print_to_screen(f"Downloading episode {idx} of {len(info['episode_urls'])}")
            episode_info = ie.extract(episode_url)
            downloader.download(episode_info, resolution=resolution, with_subs=with_subs)
    elif isinstance(info, list):
        total_seasons = len(info)
        for season_idx, season in enumerate(info, start=1):
            print_to_screen(f"Downloading season {season_idx} of {total_seasons}")
            for idx, episode_url in enumerate(season['episode_urls'], start=1):
                print_to_screen(f"Downloading episode {idx} of {len(season['episode_urls'])} in season {season_idx}")
                episode_info = ie.extract(episode_url)
                downloader.download(episode_info, resolution=resolution, with_subs=with_subs)
    else:
        print_to_screen("Starting download of a single episode")
        downloader.download(info, resolution=resolution, with_subs=with_subs)
