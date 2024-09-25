# CREDIT TO https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/drtv.py

import requests
import uuid
import json
from drtv_dl.logger import logger
from drtv_dl.helpers import download_webpage, extract_ids_from_url
from urllib.parse import urljoin

class InfoExtractor:
    BASE_URL = "https://www.dr.dk/drtv"
    ITEM_DATA_PARAMS = {
        'device': 'web_browser',
        'ff': 'idp,ldp,rpt',
        'lang': 'da',
        'expand': 'all',
        'sub': 'Anonymous',
    }
    ITEM_API_URL = 'https://production-cdn.dr-massive.com/api/items/{}'
    STREAM_API_URL = 'https://production.dr-massive.com/api/account/items/{}/videos'
    ANONYMOUS_SSO_URL = 'https://production.dr-massive.com/api/authorization/anonymous-sso'
    ANONYMOUS_SSO_PARAMS = {
        'device': 'web_browser',
        'ff': 'idp,ldp,rpt',
        'lang': 'da',
        'supportFallbackToken': 'true',
    }

    def __init__(self):
        anon_token_response = requests.post(
            url=self.ANONYMOUS_SSO_URL,
            params=self.ANONYMOUS_SSO_PARAMS,
            headers={'Content-Type': 'application/json'},
            json={
                'deviceId': str(uuid.uuid4()),
                'scopes': ['Catalog'],
                'optout': True,
            },
        )
        anon_token_response.raise_for_status()
        anon_token_json = anon_token_response.json()
        self._TOKEN = next((entry['value'] for entry in anon_token_json if entry['type'] == 'UserAccount'), None)
        if not self._TOKEN:
            raise Exception("Couldn't retrieve anonymous token")

    def extract(self, url):
        _, item_id = extract_ids_from_url(url)
        if not item_id:
            raise Exception("Could not extract item ID from URL")

        item_response = requests.get(
            self.ITEM_API_URL.format(item_id),
            params=self.ITEM_DATA_PARAMS,
            headers={'Authorization': f'Bearer {self._TOKEN}'}
        )
        item_response.raise_for_status()
        item = item_response.json()

        with open("item.json", "w") as f:
            f.write(json.dumps(item, indent=4))

        video_id = item.get('customId', '').split(':')[-1] or item_id

        stream_response = requests.get(
            self.STREAM_API_URL.format(item_id),
            params={
                'delivery': 'stream',
                'device': 'web_browser',
                'ff': 'idp,ldp,rpt',
                'lang': 'da',
                'resolution': 'HD-1080',
                'sub': 'Anonymous',
            },
            headers={'Authorization': f'Bearer {self._TOKEN}'}
        )
        stream_response.raise_for_status()
        stream_data = stream_response.json()

        formats = []
        for stream in stream_data:
            stream_url = stream.get('url', None)
            if not stream_url:
                continue

            format_id = stream.get('format', 'na')
            access_service = stream.get('accessService')
            preference = None
            if access_service in ('SpokenSubtitles', 'SignLanguage', 'VisuallyInterpreted'):
                preference = -1
                format_id += f'-{access_service}'
            elif access_service == 'StandardVideo' or access_service is None:
                preference = 1

            formats.append({
                'format_id': format_id,
                'url': stream_url,
                'preference': preference,
            })

        return {
            "id": video_id,
            "title": item.get('season', {}).get('title', None) or item.get('title'),
            "season_number": item.get('season', {}).get('seasonNumber', None),
            "episode_number": item.get('episodeNumber', None),
            "formats": formats,
        }
    


class SeasonInfoExtractor:
    BASE_URL = "https://www.dr.dk/drtv"
    SEASON_API_URL = 'https://production-cdn.dr-massive.com/api/page'
    SEASON_API_PARAMS = {
        'device': 'web_browser',
        'item_detail_expand': 'all',
        'lang': 'da',
        'max_list_prefetch': '3',
    }

    def __init__(self):
        self.info_extractor = InfoExtractor()

    def extract(self, url):
        display_id, season_id = extract_ids_from_url(url)
        if not season_id:
            raise Exception("Could not extract season ID from URL")

        season_data = json.loads(download_webpage(
            url=self.SEASON_API_URL,
            params={
                **self.SEASON_API_PARAMS,
                'path': f'/saeson/{display_id}_{season_id}'
            },
        ))

        episodes = season_data.get('entries', [])[0].get('item', {}).get('episodes', {}).get('items', [])
        episode_infos = []
        for episode in episodes:
            episode_path = episode.get('path')
            episode_url = urljoin(self.BASE_URL, episode_path)
            info = self.info_extractor.extract(episode_url)
            episode_infos.append(info)

        season_number = season_data.get('entries', [])[0].get('item', {}).get('seasonNumber')

        return [{
            'season_number': season_number,
            'episodes': episode_infos
        }] # Read why it's a list in next class
 
class SeriesInfoExtractor:
    BASE_URL = "https://www.dr.dk/drtv"
    SERIES_API_URL = 'https://production-cdn.dr-massive.com/api/page'
    SERIES_API_PARAMS = {
        'device': 'web_browser',
        'item_detail_expand': 'all',
        'lang': 'da',
        'max_list_prefetch': '3',
    }

    def __init__(self):
        self.season_extractor = SeasonInfoExtractor()

    def extract(self, url):
        display_id, series_id = extract_ids_from_url(url)
        if not series_id:
            raise Exception("Could not extract series ID from URL")

        series_data = json.loads(download_webpage(
            url=self.SERIES_API_URL,
            params={
                **self.SERIES_API_PARAMS,
                'path': f'/serie/{display_id}_{series_id}'
            },
        ))

        seasons = series_data.get('entries', [])[0].get('item', {}).get('show', {}).get('seasons', {}).get('items', [])
        season_infos = []
        for season in seasons:
            season_path = season.get('path')
            season_url = urljoin(self.BASE_URL, season_path)
            season_info = self.season_extractor.extract(season_url)
            season_infos.append(season_info[0]) # We do [0] so we don't have to check for either a list or dict in main.py; only a list
                                                # TODO: Maybe there is a better way to do it?

        return season_infos
