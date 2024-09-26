import requests
import re
import webvtt
import os
from drtv_dl.logger import logger

def download_file(url, filename):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def download_webpage(url, headers=None, data=None, params=None, json=None, save_to=None):
    response = requests.get(
        url=url,
        headers=headers,
        data=data,
        params=params,
        json=json,
    )
    response.raise_for_status()
    return response.text

def post_request(url, headers=None, data=None, params=None, json=None):
    response = requests.post(
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

def vtt_to_srt(vtt_file, srt_file):
    with open(vtt_file, 'r', encoding='utf-8') as vtt, open(srt_file, 'w', encoding='utf-8') as srt:
        content = re.sub(r'WEBVTT\n\n', '', vtt.read())
        content = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', content)
        lines = content.split('\n\n')
        for i, line in enumerate(lines, start=1):
            srt.write(f"{i}\n{line}\n\n")
    logger.info(f"Converted {vtt_file} to {srt_file}")