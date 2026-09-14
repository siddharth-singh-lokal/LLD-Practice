import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


class LogLevel:
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


_LEVEL_NAMES = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.WARNING: "WARNING",
    LogLevel.ERROR: "ERROR",
}


@dataclass(frozen=True)
class LogRecord:
    level: int
    message: str

    @property
    def level_name(self) -> str:
        return _LEVEL_NAMES[self.level]


class LogFormatter(ABC):
    @abstractmethod
    def format_log(self, record: LogRecord) -> str:
        pass


class StringLogFormatter(LogFormatter):
    def format_log(self, record: LogRecord) -> str:
        return f"[{record.level_name}] {record.message}"


class JsonLogFormatter(LogFormatter):
    def format_log(self, record: LogRecord) -> str:
        return json.dumps(
            {"level": record.level_name, "message": record.message}
        )


class LogSink(ABC):
    @abstractmethod
    def write(self, record: LogRecord, formatted_message: str) -> None:
        pass


class ConsoleSink(LogSink):
    def write(self, record: LogRecord, formatted_message: str) -> None:
        print(formatted_message)


class FileSink(LogSink):
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, record: LogRecord, formatted_message: str) -> None:
        self.lines.append(formatted_message)


class LevelFilterSink(LogSink):
    """Wrap any sink so it only receives logs at or above min_level."""

    def __init__(self, min_level: int, inner: LogSink) -> None:
        self._min_level = min_level
        self._inner = inner

    def write(self, record: LogRecord, formatted_message: str) -> None:
        if record.level >= self._min_level:
            self._inner.write(record, formatted_message)


class Logger:
    def __init__(self, min_level: int, formatter: LogFormatter) -> None:
        self._formatter = formatter
        self._min_level = min_level
        self._sinks: list[LogSink] = []

    def add_sink(self, sink: LogSink) -> None:
        if sink not in self._sinks:
            self._sinks.append(sink)

    def log(self, level: int, message: str) -> None:
        if level < self._min_level:
            return

        record = LogRecord(level, message)
        formatted_message = self._formatter.format_log(record)

        for sink in self._sinks:
            sink.write(record, formatted_message)

    def debug(self, message: str) -> None:
        self.log(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        self.log(LogLevel.INFO, message)

    def warning(self, message: str) -> None:
        self.log(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        self.log(LogLevel.ERROR, message)


if __name__ == "__main__":
    # --- core flow: string formatter, console + file, level filter on logger ---
    file_sink = FileSink()
    logger = Logger(LogLevel.INFO, StringLogFormatter())
    logger.add_sink(ConsoleSink())
    logger.add_sink(file_sink)

    logger.debug("should not appear")
    logger.info("user logged in")
    logger.warning("disk 80% full")
    logger.error("payment failed")

    assert len(file_sink.lines) == 3
    assert all("should not" not in line for line in file_sink.lines)
    assert file_sink.lines[0] == "[INFO] user logged in"

    # --- extension: file sink only keeps ERROR+, console gets everything ---
    error_only_file = FileSink()
    filtered_logger = Logger(LogLevel.INFO, StringLogFormatter())
    filtered_logger.add_sink(ConsoleSink())
    filtered_logger.add_sink(LevelFilterSink(LogLevel.ERROR, error_only_file))

    filtered_logger.info("info goes to console only")
    filtered_logger.warning("warning goes to console only")
    filtered_logger.error("error goes to both")

    assert len(error_only_file.lines) == 1
    assert error_only_file.lines[0] == "[ERROR] error goes to both"

    # --- json formatter swap (Strategy) without changing Logger ---
    json_file = FileSink()
    json_logger = Logger(LogLevel.WARNING, JsonLogFormatter())
    json_logger.add_sink(json_file)

    json_logger.info("filtered by logger min level")
    json_logger.warning("kept")
    json_logger.error("also kept")

    assert len(json_file.lines) == 2
    assert json.loads(json_file.lines[0]) == {
        "level": "WARNING",
        "message": "kept",
    }

    # --- boundary: empty message is still a valid log line ---
    empty_msg_sink = FileSink()
    edge_logger = Logger(LogLevel.INFO, StringLogFormatter())
    edge_logger.add_sink(empty_msg_sink)
    edge_logger.info("")

    assert empty_msg_sink.lines == ["[INFO] "]

    print("all checks passed")
