import logging
import os
from logging.handlers import RotatingFileHandler
from fastapi import Request
from app.core.config import settings

class LoggerConfig:
    """
    Logger configuration class to setup logging for the application.
    """
    def __init__(
        self, env=20, logger_name="TravelAgent", log_directory="logs", log_file="app.log"
    ):
        try:
            self.logger_name = logger_name
            self.log_directory = os.path.abspath(log_directory)
            self.log_file_path = os.path.join(self.log_directory, log_file)
            self.env = env
            self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
 
            self.logger = logging.getLogger(self.logger_name)
            self.root_logger = logging.getLogger()
            self.setup_logger()
        except Exception as e:
            print(f"Failed to initialize logger: {str(e)}")
 
    def setup_logger(self):
        try:
            os.makedirs(self.log_directory, exist_ok=True)
            
            # File Handler
            file_handler = RotatingFileHandler(
                self.log_file_path, backupCount=5, maxBytes=1024 * 1024 * 10, encoding="utf-8"
            )
            file_handler.setLevel(self.env)
            
            # Console Handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.env)
 
            formatter = logging.Formatter(self.log_format)
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
 
            # Avoid adding duplicate handlers if re-initialized
            if not self.logger.hasHandlers():
                self.logger.addHandler(file_handler)
                self.logger.addHandler(console_handler)
            
            self.logger.setLevel(self.env)
            
        except Exception as e:
            print(f"Failed to setup logger handlers: {str(e)}")
 
    def log(self, level: int, message: str, extra: dict = None):
        """Simple wrapper to log messages"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.log(level, message)

# Initialize Logger
logs = LoggerConfig(
    env=settings.LOGGER, 
    logger_name="APP-BE", 
    log_directory="logs", 
    log_file="app.log"
)