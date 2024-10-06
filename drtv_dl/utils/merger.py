import ffmpeg
import os

from drtv_dl.utils.helpers import print_to_screen

class Merger:
    def __init__(self, video_file, audio_file, subtitle_file, output_file):
        self.video_file = video_file
        self.audio_file = audio_file
        self.subtitle_file = subtitle_file
        self.output_file = output_file
    
    def _get_input_streams(self):
        video_input = ffmpeg.input(os.path.join(os.getcwd(), self.video_file))
        audio_input = ffmpeg.input(os.path.join(os.getcwd(), self.audio_file))

        output_params = {'c:v': 'copy', 'c:a': 'copy'}

        if self.subtitle_file:
            subtitle_input = ffmpeg.input(os.path.join(os.getcwd(), self.subtitle_file))
            output_params['c:s'] = 'mov_text'
            streams = [video_input, audio_input, subtitle_input]
        else:
            streams = [video_input, audio_input]

        return streams, output_params

    def merge(self, note):
        print_to_screen(note)
        streams, output_params = self._get_input_streams()
        try:
            ffmpeg.output(
                *streams,
                os.path.join(os.getcwd(), self.output_file),
                **output_params
            ).run(quiet=True, overwrite_output=True)
            return True
        except ffmpeg.Error:
            return False