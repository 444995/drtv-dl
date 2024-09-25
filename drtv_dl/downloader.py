import os
import re
import requests
import ffmpeg
from urllib.parse import urljoin, unquote
from drtv_dl.exceptions import DownloadError
from drtv_dl.logger import logger
from drtv_dl.helpers import sanitize_filename, download_webpage, vtt_to_srt
from collections import defaultdict


class M3U8Parser:
    def __init__(self, base_uri, m3u8_content):
        self.base_uri = base_uri
        self.m3u8_content = m3u8_content.splitlines()
        self.streams = defaultdict(list)
    
    def parse(self):
        stream_info = {}
        for line in self.m3u8_content:
            line = line.strip()
            if line.startswith("#EXT-X-MEDIA:TYPE=AUDIO"):
                audio_info = self._parse_attributes(line)
                self.streams['audio'].append({
                    **audio_info,
                    'uri': self._get_complete_uri(audio_info.get('uri'))
                })
            elif line.startswith("#EXT-X-MEDIA:TYPE=SUBTITLES"):
                subtitle_info = self._parse_attributes(line)
                self.streams['subtitles'].append({
                    **subtitle_info,
                    'uri': self._get_complete_uri(subtitle_info.get('uri'), is_subtitle=True)
                })
            elif line.startswith("#EXT-X-STREAM-INF:"):
                stream_info = self._parse_stream(line)
            elif stream_info:
                self.streams['video'].append({
                    **stream_info,
                    'uri': self._get_complete_uri(line)
                })
                stream_info = {} # reset for the next one
        return dict(self.streams)
    
    def _parse_attributes(self, line):
        attrs = {}
        matches = re.findall(r'([A-Z\-]+)=("[^"]*"|\d+x\d+|\d+|\w+)', line)
        for key, value in matches:
            attrs[key.lower()] = value.strip('"')
        return attrs
    
    def _parse_stream(self, line):
        return self._parse_attributes(line)
    
    def _get_complete_uri(self, uri, is_subtitle=False):
        if is_subtitle:
            uri = uri.replace("/playlist.m3u8", ".vtt")
        return urljoin(self.base_uri, uri)


class DRTVDownloader:
    def __init__(self):
        pass

    def combine_video_audio(self, video_file, audio_file, subtitle_file, output_file):
        video_input = ffmpeg.input(os.path.join(os.getcwd(), video_file))
        audio_input = ffmpeg.input(os.path.join(os.getcwd(), audio_file))

        output_params = {'c:v': 'copy', 'c:a': 'copy'}
        
        if subtitle_file:
            subtitle_input = ffmpeg.input(os.path.join(os.getcwd(), subtitle_file))
            output_params['c:s'] = 'mov_text'
            streams = [video_input, audio_input, subtitle_input]
        else:
            streams = [video_input, audio_input]

        ffmpeg.output(
            *streams,
            os.path.join(os.getcwd(), output_file), 
            **output_params
        ).run(quiet=True, overwrite_output=True)

    def _get_optimal_format(self, formats):
        if formats == []:
            raise DownloadError("No formats for media was available")
        preferred_formats = [f for f in formats if f.get('preference') == 1]
        if not preferred_formats:
            logger.error(f"No suitable formats found")
            raise DownloadError("No suitable formats found.")
        return preferred_formats[0]

    def _get_optimal_stream(self, parsed_m3u8_streams, desired_resolution):
        optimal_stream = {
            'video': None,
            'audio': None,
            'subtitle': None
        }

        if parsed_m3u8_streams['subtitles']:
            optimal_stream['subtitle'] = parsed_m3u8_streams['subtitles'][-1]

        for stream in parsed_m3u8_streams['video']:
            if stream['resolution'].split('x')[1] == desired_resolution.replace('p', ''):
                optimal_stream['video'] = stream
                break

        if optimal_stream['video'] is None:
            raise DownloadError(f"No video stream found for resolution {desired_resolution}")

        audio_group = optimal_stream['video']['audio']
        for audio_stream in parsed_m3u8_streams['audio']:
            if audio_stream['group-id'] == audio_group:
                optimal_stream['audio'] = audio_stream
                break

        if optimal_stream['audio'] is None:
            raise ValueError(f"No audio stream found for group {audio_group}")

        return optimal_stream

    def _download_file(self, url, filename):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

    def _extract_map_uri(self, m3u8_content, base_url):
        for line in m3u8_content.splitlines():
            if line.startswith('#EXT-X-MAP:'):
                uri_part = line.split('URI=')[1].split(',')[0].strip('"')
                uri = uri_part.split('"')[0]
                return urljoin(base_url, unquote(uri))
        return None


    def download(self, info, resolution=None, with_subs=False):
        format_info = self._get_optimal_format(info.get('formats', []))
        stream_url = format_info.get('url')
        m3u8_streams = download_webpage(url=stream_url)
        parsed_m3u8_streams = M3U8Parser(stream_url, m3u8_streams).parse()
        optimal_stream = self._get_optimal_stream(parsed_m3u8_streams, resolution)

        base_filename = self._generate_filename(info)
        
        subtitle_filename = None


        # video download
        video_m3u8 = download_webpage(url=optimal_stream['video']['uri'])
        video_map_uri = self._extract_map_uri(video_m3u8, optimal_stream['video']['uri'])
        if video_map_uri:
            video_filename = f"{base_filename}.video"
            self._download_file(video_map_uri, video_filename)
            logger.info(f"Video downloaded: {video_filename}")
        else:
            raise DownloadError("Could not find video MAP URI")

        # audio download
        audio_m3u8 = download_webpage(url=optimal_stream['audio']['uri'])
        audio_map_uri = self._extract_map_uri(audio_m3u8, optimal_stream['audio']['uri'])
        if audio_map_uri:
            audio_filename = f"{base_filename}.audio"
            self._download_file(audio_map_uri, audio_filename)
            logger.info(f"Audio downloaded: {audio_filename}")
        else:
            raise DownloadError("Could not find audio MAP URI")

        # subtitle download (if --with-subs enabled)
        if with_subs and optimal_stream['subtitle']:
            subtitle_url = optimal_stream['subtitle']['uri']
            vtt_filename = f"{base_filename}.vtt"
            self._download_file(subtitle_url, vtt_filename)
            logger.info(f"Subtitle downloaded: {vtt_filename}")
            
            srt_filename = f"{base_filename}.srt"
            vtt_to_srt(vtt_filename, srt_filename)
            logger.info(f"Converted subtitle to SRT: {srt_filename}")
            
            os.remove(vtt_filename)
            
            subtitle_filename = srt_filename

        # combine video and audio (and subtitles if available)
        output_filename = f"{base_filename}.mp4"
        self.combine_video_audio(video_filename, audio_filename, subtitle_filename, output_filename)
        logger.info(f"Combined video and audio into: {output_filename}")

        # cleanup
        os.remove(video_filename)
        os.remove(audio_filename)
        if subtitle_filename:
            os.remove(subtitle_filename)

        logger.info("Download and combination completed successfully.")

    @staticmethod
    def _generate_filename(info):
        title = info.get('title')
        id_ = info.get('id')
        season_number = info.get('season_number')
        episode_number = info.get('episode_number')

        if season_number and episode_number:
            filename = f"{title} S{int(season_number):02d}E{int(episode_number):02d} [{id_}]"
        else:
            filename = f"{title} [{id_}]"

        return sanitize_filename(filename)