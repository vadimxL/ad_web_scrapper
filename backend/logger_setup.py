import logging

# Include filename and line number in the log format (no milliseconds in asctime)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def setup_logger(name, log_file, level=logging.INFO):
    """Create or return a logger with file & line number in each entry."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # avoid duplicate logs if root logger configured elsewhere

    # Prevent adding multiple handlers if setup_logger called more than once
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith(log_file) for h in logger.handlers):
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# first file logger
internal_info_logger = setup_logger('internal_info', 'internal_info.log')

# second file logger
ads_updates_logger = setup_logger('ads_updates', 'ads_updates.log')