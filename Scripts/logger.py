import logging
from logging.handlers import RotatingFileHandler


class CustomLogger:
    """
    A singleton class to manage custom loggers with rotating file handlers.

    Attributes:
        _instances (dict): Dictionary to store singleton instances.
        loggers (dict): Dictionary to store created loggers.
    """

    _instances = {}

    def __new__(cls, *args, **kwargs):
        """
        Ensures only one instance of CustomLogger is created (singleton pattern).

        Returns:
            CustomLogger: The singleton instance of CustomLogger.
        """
        if not hasattr(cls, "_instance"):
            cls._instance = super(CustomLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the loggers dictionary to store logger instances.
        """
        if not hasattr(self, "loggers"):
            self.loggers = {}

    def get_logger(self, name, log_file, level):
        """
        Retrieves an existing logger or creates a new one if it does not exist.

        Args:
            name (str): The name of the logger.
            log_file (str): Path to the log file.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).

        Returns:
            logging.Logger: The configured logger instance.
        """
        if name not in self.loggers:
            handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)

            logger = logging.getLogger(name)
            logger.setLevel(level)

            if not logger.handlers:
                logger.addHandler(handler)

            self.loggers[name] = logger

        return self.loggers[name]
