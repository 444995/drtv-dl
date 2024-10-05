import re
import inspect
import logging
import requests, sys
from drtv_dl.logger import logger
from drtv_dl.exceptions import DownloadError

def is_valid_drtv_url(url):
    pattern = r'^https://www\.dr\.dk/drtv/(se|saeson|serie|program)/[a-zA-Z0-9\-_]+_\d+$'
    return bool(re.match(pattern, url))

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
    print_to_screen(f"Destination: {filename}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    initial_size = int(response.headers.get('content-length', 0))
    progress_tracker = ProgressTracker(initial_size, filename)
    
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            size = file.write(chunk)
            progress_tracker.update(size)
    
    progress_tracker.finish()
    
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
    sanitized = re.sub(r'[<>:"/\\|?*]', ' - ', filename)
    logger.debug(f"Sanitized filename: {sanitized}")
    return sanitized.replace("  ", " ")

def vtt_to_srt(vtt_file, srt_file):
    with open(vtt_file, 'r', encoding='utf-8') as vtt, open(srt_file, 'w', encoding='utf-8') as srt:
        content = re.sub(r'WEBVTT\n\n', '', vtt.read())
        content = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', content)
        lines = content.split('\n\n')
        for i, line in enumerate(lines, start=1):
            srt.write(f"{i}\n{line}\n\n")
    print_to_screen(f"Converted {vtt_file} to {srt_file}")

class ProgressTracker:
    def __init__(self, initial_size, filename):
        self.total_size = initial_size
        self.downloaded = 0
        self.filename = filename

    def get_appropriate_unit(self, size):
        if size < 1024 * 1024:
            return 'KB', 1024
        elif size < 1024 * 1024 * 1024:
            return 'MB', 1024 * 1024
        else:
            return 'GB', 1024 * 1024 * 1024

    def update(self, chunk_size):
        self.downloaded += chunk_size
        if self.downloaded > self.total_size:
            self.total_size = self.downloaded
        unit, divisor = self.get_appropriate_unit(self.total_size)
        downloaded_unit = self.downloaded / divisor
        total_unit = self.total_size / divisor
        percentage_done = (downloaded_unit / total_unit) * 100
        print(f'\r {" " * 2}~ {downloaded_unit:.2f}/{total_unit:.2f} {unit} - {percentage_done:.2f}%', end='', file=sys.stderr, flush=True)

    def finish(self):
        print(file=sys.stderr)

def get_optimal_format(formats):
    if not formats:
        logger.error("No available formats to choose from")
        raise DownloadError("No formats for media were available")
    preferred_formats = [f for f in formats if f.get('preference') == 1]
    if not preferred_formats:
        logger.error("No suitable formats found")
        raise DownloadError("No suitable formats found.")
    logger.debug(f"Optimal format selected: {preferred_formats[0]['format_id']}")
    return preferred_formats[0]

def print_formats(formats):
    # helper func
    def format_row(columns, widths):
        return " │ ".join([col.ljust(width) for col, width in zip(columns, widths)])

    data_rows = []
    for audio in formats.get('audio', []):
        data_rows.append(
            [
                f"audio_{audio['group-id']}-{audio['name']}-{audio['language']}", 
                "mp4", "", 
                "audio only", 
                "unknown", "unknown", 
                "audio only", 
                f"[{audio['language']}] {audio['name']}", 
                "m3u8"
            ]
        )
    for subtitle in formats.get('subtitles', []):
        data_rows.append(
            [
                f"subs_{subtitle['name']}-{subtitle['language']}", 
                "vtt", "", 
                "subtitles", 
                "unknown", "unknown", 
                "sub only", 
                f"[{subtitle['language']}] {subtitle['name']}", 
                "m3u8"
            ]
        )
    for video in formats.get('video', []):
        data_rows.append(
            [
                f"video_{video['bandwidth']}", 
                "mp4", video['frame-rate'], 
                video['resolution'], 
                f"{int(video['bandwidth']) // 1000}k", 
                f"{int(video['average-bandwidth']) // 1000}k", 
                video['codecs'].split(",")[0], 
                "video only", 
                "m3u8"
            ]
        )

    data_rows.insert(0, 
        [
            "ID", "EXT", "FPS", 
            "RESOLUTION", "TBR", 
            "VBR", "VCODEC", 
            "ACODEC", "PROTOCOL"
        ]
    )

    column_widths = [max(len(str(item)) for item in col) for col in zip(*data_rows)]
    print()
    for i, row in enumerate(data_rows):
        if i == 1:  # After the header, print a separator line
            print("─" * (sum(column_widths) + 3 * (len(column_widths) - 1)))
        print(format_row(row, column_widths))
    print("─" * (sum(column_widths) + 3 * (len(column_widths) - 1)))
    print()
