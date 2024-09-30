# import picologging as logging
import logging


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("combat.log")
    file_handler.name = "combat_file_log"
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.name = "stdout_stream_log"
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(levelname)s - %(asctime)s - %(lineno)d - %(module)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()
