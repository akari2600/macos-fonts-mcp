import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO", format_type: str = "json") -> logging.Logger:
    """Setup structured logging for the MCP server."""
    
    logger = logging.getLogger("macos-fonts-mcp")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stderr)
    
    if format_type == "json":
        import json
        import datetime
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # Add any extra fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                                   'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                                   'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                                   'processName', 'process', 'message']:
                        log_entry[key] = value
                
                return json.dumps(log_entry)
        
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Global logger instance
logger = setup_logging()