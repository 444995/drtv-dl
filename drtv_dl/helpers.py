import re
import inspect
import logging
import requests
from tqdm import tqdm

from drtv_dl.logger import logger

def print_to_screen(message, level='info'):
    frame = inspect.currentframe().f_back
    module = inspect.getmodule(frame)
    module_name = module.__name__.split('.')[-1] if module else 'unknown_module'
    locals_ = frame.f_locals
    class_name = None
    if 'self' in locals_:
        class_name = locals_['self'].__class__.__name__
    elif 'cls' in locals_:
        class_name = locals_['cls'].__name__
    if class_name:
        identifier = f'{module_name}:{class_name.lower()}'
    else:
        identifier = module_name
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, message, extra={'module_class': identifier})


def download_file(url, filename):
    print_to_screen(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    file_size = int(response.headers.get('content-length', 0))
    progress_bar = tqdm(total=file_size, unit='iB', unit_scale=True, desc=filename)
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            size = file.write(chunk)
            progress_bar.update(size)
    
    progress_bar.close()
    logger.debug(f"File {filename} downloaded successfully")

def download_webpage(url, headers=None, data=None, params=None, json=None, save_to=None):
    logger.debug(f"Requesting URL: {url}")
    response = requests.get(
        url=url,
        headers=headers,
        data=data,
        params=params,
        json=json,
    )
    response.raise_for_status()
    logger.debug(f"Received response from {url}")
    return response.text

def post_request(url, headers=None, data=None, params=None, json=None):
    logger.debug(f"POST request to URL: {url}")
    response = requests.post(
        url=url,
        headers=headers,
        data=data,
        params=params,
        json=json,
    )
    response.raise_for_status()
    logger.debug(f"POST response received from {url}")
    return response

def extract_ids_from_url(url):
    path_parts = url.strip('/').split('/')
    last_part = path_parts[-1]
    if '_' in last_part:
        display_id, item_id = last_part.rsplit('_', 1)
    else:
        display_id = last_part
        item_id = None
    logger.debug(f"Extracted display_id: {display_id}, item_id: {item_id}")
    return display_id, item_id

def sanitize_filename(filename):
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    logger.debug(f"Sanitized filename: {sanitized}")
    return sanitized

def vtt_to_srt(vtt_file, srt_file):
    with open(vtt_file, 'r', encoding='utf-8') as vtt, open(srt_file, 'w', encoding='utf-8') as srt:
        content = re.sub(r'WEBVTT\n\n', '', vtt.read())
        content = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', content)
        lines = content.split('\n\n')
        for i, line in enumerate(lines, start=1):
            srt.write(f"{i}\n{line}\n\n")
    print_to_screen(f"Converted {vtt_file} to {srt_file}")