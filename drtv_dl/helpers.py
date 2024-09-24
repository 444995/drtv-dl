import requests
import re

def download_webpage(url, headers=None, data=None, params=None, json=None):
    response = requests.get(
        url=url,
        headers=headers,
        data=data,
        params=params,
        json=json,
    )
    response.raise_for_status()
    return response

def post_request(url, headers=None, data=None, params=None, json=None):
    response = requests.get(
        url=url,
        headers=headers,
        data=data,
        params=params,
        json=json,
    )
    response.raise_for_status()
    return response

def extract_ids_from_url(url):
    path_parts = url.strip('/').split('/')
    last_part = path_parts[-1]
    if '_' in last_part:
        display_id, item_id = last_part.rsplit('_', 1)
    else:
        display_id = last_part
        item_id = None
    return display_id, item_id

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)