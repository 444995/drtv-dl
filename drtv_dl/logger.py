import logging
import os

def setup_logger():
    logger = logging.getLogger('drtv_dl')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(module)s] - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()