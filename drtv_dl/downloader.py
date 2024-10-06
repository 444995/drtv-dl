import os

from drtv_dl.logger import logger
from drtv_dl.exceptions import DownloadError
from drtv_dl.utils.merger import Merger
from drtv_dl.utils.m3u8_parser import M3U8Parser
from drtv_dl.utils.helpers import (
    generate_filename,
    download_webpage,
    vtt_to_srt,
    download_file,
    print_to_screen,
    get_optimal_format, 
    print_formats
)

class DRTVDownloader:
    def download(self, info, list_formats, resolution, include_subs):
        stream_url = self._get_stream_url(info)
        m3u8_streams = self._download_m3u8_streams(info['id'], stream_url)
        parsed_m3u8_streams = self._parse_m3u8_streams(m3u8_streams, stream_url, info['id'])

        if list_formats:
            print_formats(parsed_m3u8_streams)
            return

        optimal_stream = self._get_optimal_stream(parsed_m3u8_streams, resolution)
        base_filename = generate_filename(info)
        
        video_filename = self._download_video(optimal_stream, base_filename)
        audio_filename = self._download_audio(optimal_stream, base_filename)
        subtitle_filename = self._download_subtitle(optimal_stream, base_filename, include_subs)

        self._merge_streams(info, video_filename, audio_filename, subtitle_filename, base_filename)
        self._cleanup(video_filename, audio_filename, subtitle_filename)

    @staticmethod
    def _download_video(optimal_stream, base_filename):
        video_m3u8 = download_webpage(url=optimal_stream['video']['uri'])
        video_map_uri = M3U8Parser.extract_map_uri(video_m3u8, optimal_stream['video']['uri'])
        if video_map_uri:
            video_filename = f"{base_filename}.video"
            download_file(video_map_uri, video_filename)
            print_to_screen(f"Video saved as {video_filename}")
            return video_filename
        else:
            logger.error("Could not find video MAP URI")
            raise DownloadError("Could not find video MAP URI")

    @staticmethod
    def _download_audio(optimal_stream, base_filename):
        audio_m3u8 = download_webpage(url=optimal_stream['audio']['uri'])
        audio_map_uri = M3U8Parser.extract_map_uri(audio_m3u8, optimal_stream['audio']['uri'])
        if audio_map_uri:
            audio_filename = f"{base_filename}.audio"
            download_file(audio_map_uri, audio_filename)
            print_to_screen(f"Audio saved as {audio_filename}")
            return audio_filename
        else:
            logger.error("Could not find audio MAP URI")
            raise DownloadError("Could not find audio MAP URI")

    @staticmethod
    def _download_subtitle(optimal_stream, base_filename, include_subs):
        if include_subs and optimal_stream['subtitle']:
            subtitle_url = optimal_stream['subtitle']['uri']
            vtt_filename = f"{base_filename}.vtt"
            download_file(subtitle_url, vtt_filename)
            print_to_screen(f"Subtitles saved as {vtt_filename}")
            
            srt_filename = f"{base_filename}.srt"
            vtt_to_srt(vtt_filename, srt_filename)
            os.remove(vtt_filename)
            return srt_filename
        return None

    @staticmethod
    def _get_stream_url(info):
        return get_optimal_format(info.get('formats', [])).get('url')
    
    @staticmethod
    def _download_m3u8_streams(info_id, stream_url):
        print_to_screen(f"{info_id}: Downloading m3u8 manifest...")
        return download_webpage(url=stream_url)
    
    @staticmethod
    def _parse_m3u8_streams(m3u8_streams, stream_url, info_id):
        return M3U8Parser(stream_url, m3u8_streams).parse()

    @staticmethod
    def _get_optimal_stream(parsed_m3u8_streams, desired_resolution):
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

    @staticmethod
    def _merge_streams(info, video_filename, audio_filename, subtitle_filename, base_filename):
        output_filename = f"{base_filename}.mp4"
        result = Merger(
            video_filename,
            audio_filename,
            subtitle_filename,
            output_filename
        ).merge(note=f"{info['id']}: Merging streams into {output_filename}")
        if not result:
            raise DownloadError(f"Failed to merge streams for {info['id']}")
    
    @staticmethod
    def _cleanup(video_filename, audio_filename, subtitle_filename):
        os.remove(video_filename)
        os.remove(audio_filename)
        if subtitle_filename:
            os.remove(subtitle_filename)