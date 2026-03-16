import logging
import logging.config as logging_config

LOGGING_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOGGING_JSON_FORMAT = "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(request_id)s %(message)s"
LOGGING_DATEFMT = "%d-%m-%Y %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": LOGGING_FORMAT, "datefmt": LOGGING_DATEFMT},
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": LOGGING_JSON_FORMAT,
            "datefmt": LOGGING_DATEFMT,
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

logging_config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """Получить логгер с заданным именем."""
    return logging.getLogger(name)
