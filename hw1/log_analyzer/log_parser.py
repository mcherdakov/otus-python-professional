from __future__ import annotations

import re
import gzip
import os

from datetime import datetime
from typing import Generator, Optional, Callable
from dataclasses import dataclass, field

from config import Config


file_date_regexp = re.compile(r'\d+')
log_format_regexp = re.compile(
    r'^nginx-access-ui\.log-\d+(\.txt|\.log|\.gz)?$',
)
report_format_regexp = re.compile(r'^report-*')
request_regexp = re.compile(r'".*?"')
request_duration_regexp = re.compile(r'[.\d]*$')


@dataclass
class File:
    name: str
    date: datetime

    @classmethod
    def from_file_name(cls, file_name: str) -> File:
        date = re.findall(file_date_regexp, file_name)[0]

        return cls(
            name=file_name,
            date=datetime.strptime(date, '%Y%m%d')
        )


@dataclass
class Request:
    method: str = ''
    name: str = ''
    http_version: str = ''


@dataclass
class RequestLog:
    request: Request = field(default_factory=lambda: Request())
    duration: float = .0
    success: bool = True


def _get_files_in_path(path: str) -> Generator[File, None, None]:
    for name in os.listdir(path):
        if os.path.isfile(os.path.join(path, name)):
            yield File.from_file_name(name)


def get_next_log_file(config: Config) -> Optional[File]:
    last_log_file: Optional[File] = None
    for log_file in _get_files_in_path(config.LOG_DIR):
        if not re.match(log_format_regexp, log_file.name):
            continue

        if last_log_file is None or last_log_file.date < log_file.date:
            last_log_file = log_file

    if last_log_file is None:
        return None

    # If report for this date already exists, skip this log file
    for report_file in _get_files_in_path(config.REPORT_DIR):
        if last_log_file.date == report_file.date:
            return None

    return last_log_file


def parse_log_line(log_line: str) -> RequestLog:
    request_search = re.search(request_regexp, log_line)
    request_duration_search = re.search(request_duration_regexp, log_line)
    if request_search is None or request_duration_search is None:
        raise ValueError

    request = request_search.group().replace('"', '').split()
    if len(request) != 3:
        raise ValueError

    return RequestLog(
        request=Request(
            method=request[0],
            name=request[1],
            http_version=request[2],
        ),
        duration=float(request_duration_search.group()),
    )


def log_readlines(file_name: str) -> Generator[RequestLog, None, None]:
    open_func: Callable = open
    if file_name.endswith('.gz'):
        open_func = gzip.open

    with open_func(file_name, 'rt', encoding='utf-8') as log_file:
        for line in log_file:
            try:
                yield parse_log_line(line)
            except ValueError:
                yield RequestLog(success=False)
