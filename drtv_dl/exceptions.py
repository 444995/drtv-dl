class DRTVDownloaderError(Exception):
    pass

class DownloadError(DRTVDownloaderError):
    pass

class ExtractionError(DRTVDownloaderError):
    pass