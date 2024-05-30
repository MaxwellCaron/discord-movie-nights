import logging

logging.basicConfig(
        format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
        datefmt='%m-%d-%Y %H:%M:%S',
        level=logging.INFO,
    )


def get_logger(name: str = "Logger") -> logging.Logger:
    logger = logging.getLogger(name)
    return logger
