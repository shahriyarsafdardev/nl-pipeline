import logging


def getLogger():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('sphere')
    logger.setLevel(logging.INFO)
    return logger
