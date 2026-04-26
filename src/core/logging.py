"""Enhanced logging configuration with file rotation and detailed formatting."""
import logging
import os
import sys
import glob
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta
from src.core.config import config


def cleanup_old_logs(log_dir: Path, retention_days: int):
    """Delete log files older than retention_days.

    Args:
        log_dir: Path to the logs directory
        retention_days: Number of days to keep logs (default: 7)
    """
    if not log_dir.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0
    deleted_size = 0

    logger = logging.getLogger(__name__)

    # Find all log files
    log_patterns = ["proxy_*.log", "proxy_errors_*.log", "tool_usage_*.log"]

    for pattern in log_patterns:
        for log_file in log_dir.glob(pattern):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if mtime < cutoff_date:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                    logger.debug(f"Deleted old log: {log_file.name} ({file_size} bytes)")
            except Exception as e:
                logger.warning(f"Failed to delete {log_file}: {e}")

    if deleted_count > 0:
        size_mb = deleted_size / (1024 * 1024)
        logger.info(f"Cleaned up {deleted_count} old log files ({size_mb:.2f} MB), keeping {retention_days} days")
    else:
        logger.debug(f"No old logs to clean up (retention: {retention_days} days)")


class ProxyLogger:
    """Enhanced logger with file rotation and structured formatting."""

    def __init__(self, name: str, log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels
        self.logger.handlers.clear()  # Clear existing handlers

        # Create logs directory
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Clean up old logs (using retention days from config)
        try:
            cleanup_old_logs(self.log_dir, config.log_retention_days)
        except Exception as e:
            # Don't fail logging if cleanup fails
            print(f"Warning: Log cleanup failed: {e}")

        # Parse log level
        log_level = config.log_level.split()[0].upper()
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level not in valid_levels:
            log_level = 'INFO'

        # Define detailed format for files
        detailed_format = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Define simple format for console
        console_format = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # 1. File handler - all logs with rotation
        today = datetime.now().strftime("%Y-%m-%d")
        all_log_file = self.log_dir / f"proxy_{today}.log"
        file_handler = RotatingFileHandler(
            filename=all_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_format)
        self.logger.addHandler(file_handler)

        # 2. File handler - errors only
        error_log_file = self.log_dir / f"proxy_errors_{today}.log"
        error_handler = RotatingFileHandler(
            filename=error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_format)
        self.logger.addHandler(error_handler)

        # 3. Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # 4. Tool usage tracking file
        self.tool_log_file = self.log_dir / f"tool_usage_{today}.log"

    def log_tool_conversion(self, request_id: str, tool_data: dict):
        """Log tool parameter conversion details."""
        try:
            with open(self.tool_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"\n{'='*80}\n")
                f.write(f"[{timestamp}] Request ID: {request_id}\n")
                f.write(f"Tool Name: {tool_data.get('name', 'N/A')}\n")
                f.write(f"Description: {tool_data.get('description', 'N/A')}\n")
                f.write(f"Input Schema:\n{tool_data.get('parameters', 'N/A')}\n")
                f.write(f"{'='*80}\n")
        except Exception as e:
            self.logger.error(f"Failed to write tool log: {e}")

    def log_tool_choice(self, request_id: str, tool_choice: dict, available_tools: list):
        """Log tool choice conversion details."""
        try:
            with open(self.tool_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                f.write(f"\n{'='*80}\n")
                f.write(f"[{timestamp}] Request ID: {request_id}\n")
                f.write(f"Tool Choice Type: {tool_choice.get('type', 'N/A')}\n")
                f.write(f"Tool Choice Name: {tool_choice.get('name', 'N/A')}\n")
                f.write(f"Available Tools: {[t.get('name', 'N/A') for t in available_tools]}\n")
                f.write(f"{'='*80}\n")
        except Exception as e:
            self.logger.error(f"Failed to write tool choice log: {e}")

    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger


# Initialize module logger
_proxy_logger = ProxyLogger(__name__)
logger = _proxy_logger.get_logger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the proxy configuration."""
    return ProxyLogger(name).get_logger()


def log_request_summary(request_id: str, model: str, route: str, has_tools: bool):
    """Log a concise request summary."""
    logger.info(f"[{request_id}] Request: model={model}, route={route}, tools={has_tools}")


def log_tool_validation_error(request_id: str, tool_name: str, error: str):
    """Log tool validation errors."""
    logger.error(f"[{request_id}] Tool validation failed for '{tool_name}': {error}")


def log_provider_call(request_id: str, provider: str, model: str, start_time: float):
    """Log provider API call with timing."""
    duration = (datetime.now().timestamp() - start_time) * 1000
    logger.info(f"[{request_id}] Provider call: {provider}:{model} ({duration:.0f}ms)")


# Configure uvicorn loggers
for uvicorn_logger in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
    logging.getLogger(uvicorn_logger).setLevel(logging.WARNING)

logger.info(f"Logging initialized. Log directory: {_proxy_logger.log_dir}")
logger.info(f"Log files: proxy_{{date}}.log, proxy_errors_{{date}}.log, tool_usage_{{date}}.log")
