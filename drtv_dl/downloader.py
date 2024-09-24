import os
import re
import requests
import ffmpeg
from tqdm import tqdm
from urllib.parse import urljoin
from drtv_dl.exceptions import DownloadError
from drtv_dl.logger import logger
from drtv_dl.helpers import sanitize_filename, download_webpage


class M3U8Parser:
    def parse(self, content, base_url):
        lines = content.strip().splitlines()
        stream_infos = []
        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF'):
                info_line = line
                url_line = lines[i + 1] if (i + 1) < len(lines) else ''
                resolution = self._extract_resolution(info_line)
                audio_group = self._extract_audio_group(info_line)
                if resolution:
                    stream_infos.append({
                        'resolution': resolution,
                        'url': urljoin(base_url, url_line),
                        'audio_group': audio_group
                    })
        return stream_infos

    def _extract_resolution(self, info_line):
        match = re.search(r'RESOLUTION=(\d+x\d+)', info_line)
        if match:
            resolution = match.group(1)
            return self._resolution_to_string(resolution)
        return None

    @staticmethod
    def _extract_audio_group(info_line):
        match = re.search(r'AUDIO="([^"]+)"', info_line)
        return match.group(1) if match else None

    @staticmethod
    def _resolution_to_string(resolution):
        _, height = map(int, resolution.split('x'))
        return f'{height}p'

    @staticmethod
    def _resolution_to_pixels(resolution):
        return int(resolution.replace('p', ''))

    @staticmethod
    def get_audio_url(playlist_content, base_url, audio_group):
        lines = playlist_content.strip().splitlines()
        for line in lines:
            if line.startswith('#EXT-X-MEDIA') and 'TYPE=AUDIO' in line:
                if f'GROUP-ID="{audio_group}"' in line:
                    match = re.search(r'URI="([^"]+)"', line)
                    if match:
                        audio_uri = match.group(1)
                        return urljoin(base_url, audio_uri)
        return None

    def parse_segments(self, playlist_content, base_url):
        lines = playlist_content.strip().splitlines()
        segments = []
        current_byterange = None
        for line in lines:
            if line.startswith('#EXT-X-MAP'):
                segments.append(self._parse_init_segment(line, base_url))
            elif line.startswith('#EXT-X-BYTERANGE'):
                current_byterange = self._parse_byterange(line[len('#EXT-X-BYTERANGE:'):])
            elif not line.startswith('#') and line.strip():
                segments.append({
                    'uri': urljoin(base_url, line),
                    'byterange': current_byterange
                })
                current_byterange = None
        return segments

    def _parse_init_segment(self, line, base_url):
        init_uri = re.search(r'URI="([^"]+)"', line).group(1)
        init_uri = urljoin(base_url, init_uri)
        init_byterange_match = re.search(r'BYTERANGE="([^"]+)"', line)
        init_byterange = self._parse_byterange(init_byterange_match.group(1)) if init_byterange_match else None
        return {
            'uri': init_uri,
            'byterange': init_byterange
        }

    @staticmethod
    def _parse_byterange(byterange_str):
        parts = byterange_str.strip().split('@')
        length = int(parts[0])
        offset = int(parts[1]) if len(parts) > 1 else None
        return (length, offset)

class StreamDownloader:
    def __init__(self):
        self.m3u8_parser = M3U8Parser()

    def download_stream(self, stream_url, output_filename):
        segments = self.m3u8_parser.parse_segments(
            self._get_playlist_content(stream_url), 
            self._extract_base_url(stream_url)
        )

        if not segments:
            raise DownloadError("No segments found in the playlist.")

        with open(output_filename, 'wb') as f:
            for segment in tqdm(segments, desc=f'Downloading segments for {output_filename}'):
                self._download_segment(segment, f)

        logger.info(f"Downloaded stream to {output_filename}")

    @staticmethod
    def _download_segment(segment, file_handle):
        length, offset = segment['byterange'] if segment['byterange'] else (None, None)
        headers = {}
        if length:
            if offset is not None:
                headers['Range'] = f'bytes={offset}-{offset + length - 1}'
            else:
                headers['Range'] = f'bytes=0-{length - 1}'
        response = requests.get(segment['uri'], headers=headers, stream=True)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_handle.write(chunk)
    
    @staticmethod
    def _extract_base_url(stream_url):
        return stream_url.rsplit('/', 1)[0] + '/'

    @staticmethod
    def _get_playlist_content(stream_url):
        return download_webpage(
            url=stream_url
        ).text

class FFmpegHandler:
    @staticmethod
    def combine_video_audio(video_file, audio_file, output_file):
        video_input = ffmpeg.input(os.path.join(os.getcwd(), video_file))
        audio_input = ffmpeg.input(os.path.join(os.getcwd(), audio_file))

        ffmpeg.output(
            video_input, 
            audio_input, 
            os.path.join(os.getcwd(), output_file), 
            **{'c:v': 'copy', 'c:a': 'copy'}
        ).run(quiet=True, overwrite_output=True)

class FormatSelector:
    @staticmethod
    def select_format(formats):
        preferred_formats = [f for f in formats if f.get('preference') == 1]
        if not preferred_formats:
            logger.error(f"No suitable formats found")
            raise DownloadError("No suitable formats found.")
        return preferred_formats[0] # TODO: Have to research spokensubtitles a bit more

    @staticmethod
    def select_stream(stream_infos, resolution):
        resolutions = [stream['resolution'] for stream in stream_infos]
        if not resolution:
            desired_resolution = max(resolutions, key=lambda r: M3U8Parser._resolution_to_pixels(r))
        else:
            desired_resolution = resolution

        for stream_info in stream_infos:
            if stream_info['resolution'] == desired_resolution:
                return stream_info
        return None

class Downloader:
    def __init__(self):
        self.format_selector = FormatSelector()
        self.m3u8_parser = M3U8Parser()
        self.stream_downloader = StreamDownloader()

    def download(self, info, resolution=None):
        format_info = self.format_selector.select_format(info.get('formats', []))
        m3u8_url = format_info['url']

        stream_info, audio_url = self._get_stream_and_audio_urls(m3u8_url, resolution)

        output_filename = self._generate_filename(info)
        video_temp_file, audio_temp_file = self._download_streams(stream_info['url'], audio_url, output_filename)

        self._combine_and_cleanup(video_temp_file, audio_temp_file, output_filename)

        logger.info(f"Download completed: {output_filename}.mp4")

    def _get_stream_and_audio_urls(self, m3u8_url, resolution):
        playlist_content = self._fetch_playlist(m3u8_url)
        stream_infos = self.m3u8_parser.parse(playlist_content, m3u8_url)
        
        stream_info = self.format_selector.select_stream(stream_infos, resolution)
        if not stream_info:
            raise DownloadError(f"Desired resolution '{resolution}' not found.")

        audio_url = M3U8Parser.get_audio_url(playlist_content, m3u8_url, stream_info['audio_group'])
        if not audio_url:
            raise DownloadError("Audio stream not found.")

        return stream_info, audio_url

    def _fetch_playlist(self, url):
        return download_webpage(
            url=url
        ).text

    def _download_streams(self, video_url, audio_url, output_filename):
        video_temp_file = f"{output_filename}.mp4.video"
        audio_temp_file = f"{output_filename}.mp4.audio"

        self.stream_downloader.download_stream(video_url, video_temp_file)
        self.stream_downloader.download_stream(audio_url, audio_temp_file)

        return video_temp_file, audio_temp_file

    def _combine_and_cleanup(self, video_file, audio_file, output_filename):
        FFmpegHandler.combine_video_audio(video_file, audio_file, f"{output_filename}.mp4")
        os.remove(video_file)
        os.remove(audio_file)

    def _generate_filename(self, info):
        title = info.get('title')
        id_ = info.get('id')
        season_number = info.get('season_number')
        episode_number = info.get('episode_number')

        if season_number and episode_number:
            filename = f"{title} S{int(season_number):02d}E{int(episode_number):02d} [{id_}]"
        else:
            filename = f"{title} [{id_}]" # TODO: Release year is preferred but isn't stored realiably - have to figure out a way

        return sanitize_filename(filename)