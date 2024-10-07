import sys
from drtv_dl.utils import settings

import time

class ProgressTracker:
    def __init__(self, initial_size, filename):
        self.total_size = initial_size
        self.downloaded = 0
        self.filename = filename
        self.start_time = time.time()

    def get_appropriate_unit(self, size):
        if size < 1024 * 1024:
            return 'KB', 1024
        elif size < 1024 * 1024 * 1024:
            return 'MB', 1024 * 1024
        else:
            return 'GB', 1024 * 1024 * 1024

    def update(self, chunk_size):
        if settings.SUPPRESS_OUTPUT:
            return
        self.downloaded += chunk_size
        if self.downloaded > self.total_size:
            self.total_size = self.downloaded
        unit, divisor = self.get_appropriate_unit(self.total_size)
        downloaded_unit = self.downloaded / divisor
        total_unit = self.total_size / divisor
        
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            speed = self.downloaded / (elapsed_time * 1024 * 1024)
            percentage_done = (downloaded_unit / total_unit) * 100 if total_unit > 0 else 0
            
            print(f'\r {" " * 2}~ {downloaded_unit:.2f}/{total_unit:.2f} {unit} at {speed:.2f} MB/s - {percentage_done:.2f}%', end='', file=sys.stderr, flush=True)

    def finish(self):
        if not settings.SUPPRESS_OUTPUT:
            print(file=sys.stderr)