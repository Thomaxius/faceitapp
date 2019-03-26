import logging

def init():
    # Configure logging (https://docs.python.org/3/library/logging.html#logrecord-attributes)
    FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

def get(name):
    return logging.getLogger(name)

init()