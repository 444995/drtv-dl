import os
import re
import ffmpeg
from urllib.parse import urljoin, unquote
from drtv_dl.exceptions import DownloadError
from drtv_dl.logger import logger
from drtv_dl.utils.m3u8_parser import M3U8Parser
from drtv_dl.utils.helpers import sanitize_filename, download_webpage, vtt_to_srt, download_file, print_to_screen, get_optimal_format, print_formats


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

    def _extract_map_uri(self, m3u8_content, base_url):
        for line in m3u8_content.splitlines():
            if line.startswith('#EXT-X-MAP:'):
                uri_part = line.split('URI=')[1].split(',')[0].strip('"')
                uri = uri_part.split('"')[0]
                return urljoin(base_url, unquote(uri))
        return None


    def download(self, info, list_formats, resolution, with_subs):
        format_info = get_optimal_format(info.get('formats', []))
        stream_url = format_info.get('url')
        logger.debug(f"Stream URL: {stream_url}")

        print_to_screen(f"{info['id']}: Downloading m3u8 manifest...")
        m3u8_streams = download_webpage(url=stream_url)
        parsed_m3u8_streams = M3U8Parser(stream_url, m3u8_streams).parse()
        if list_formats:
            print_formats(parsed_m3u8_streams)
            return

        optimal_stream = self._get_optimal_stream(parsed_m3u8_streams, resolution)
        base_filename = self._generate_filename(info)
        subtitle_filename = None

        # video download
        video_m3u8 = download_webpage(url=optimal_stream['video']['uri'])
        video_map_uri = self._extract_map_uri(video_m3u8, optimal_stream['video']['uri'])
        if video_map_uri:
            video_filename = f"{base_filename}.video"
            download_file(video_map_uri, video_filename)
            print_to_screen(f"Video saved as {video_filename}")
        else:
            logger.error("Could not find video MAP URI")
            raise DownloadError("Could not find video MAP URI")

        # audio download
        audio_m3u8 = download_webpage(url=optimal_stream['audio']['uri'])
        audio_map_uri = self._extract_map_uri(audio_m3u8, optimal_stream['audio']['uri'])
        if audio_map_uri:
            audio_filename = f"{base_filename}.audio"
            download_file(audio_map_uri, audio_filename)
            print_to_screen(f"Audio saved as {audio_filename}")
        else:
            logger.error("Could not find audio MAP URI")
            raise DownloadError("Could not find audio MAP URI")

        # subtitle download
        if with_subs and optimal_stream['subtitle']:
            subtitle_url = optimal_stream['subtitle']['uri']
            vtt_filename = f"{base_filename}.vtt"
            download_file(subtitle_url, vtt_filename)
            print_to_screen(f"Subtitles saved as {vtt_filename}")
            
            srt_filename = f"{base_filename}.srt"
            vtt_to_srt(vtt_filename, srt_filename)
            os.remove(vtt_filename)
            subtitle_filename = srt_filename

        # combining streams
        output_filename = f"{base_filename}.mp4"
        print_to_screen(f"{info['id']}: Merging streams into {output_filename}")
        self.combine_video_audio(video_filename, audio_filename, subtitle_filename, output_filename)

        # cleanup
        os.remove(video_filename)
        os.remove(audio_filename)
        if subtitle_filename:
            os.remove(subtitle_filename)

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