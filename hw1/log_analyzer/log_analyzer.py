#!/usr/bin/env python
import os
import logging
import json
import argparse
from string import Template
from dataclasses import dataclass, asdict, field
from typing import Generator
from statistics import median

from config import Config, parse_config
from log_parser import get_next_log_file, log_readlines, RequestLog, File


@dataclass
class RequestStat:
    url: str
    count: int = 0
    count_perc: float = 0
    times: list[float] = field(default_factory=lambda: [])
    time_sum: float = 0
    time_perc: float = 0
    time_avg: float = 0
    time_max: float = 0
    time_med: float = 0

    def calculate_stats(self, total_count: int, total_duration: float) -> None:
        precision = 3

        self.count_perc = round(self.count / total_count * 100, precision)
        self.time_max = round(max(self.times), precision)
        self.time_sum = round(sum(self.times), precision)
        self.time_avg = round(self.time_sum / self.count, precision)
        self.time_perc = round(self.time_sum / total_duration * 100, precision)
        self.time_med = round(median(self.times), precision)


def save_result(
        config: Config,
        request_stats: list[RequestStat],
        log_file: File,
) -> None:
    with open('report.html', 'r', encoding='utf-8') as template_file:
        template = Template(template_file.read())
        result_stats = sorted(
            request_stats,
            key=lambda s: s.time_sum,
            reverse=True
        )[:config.REPORT_SIZE]

        results = []
        for result_stat in result_stats:
            result_stat_dict = asdict(result_stat)
            result_stat_dict.pop('times')
            results.append(result_stat_dict)

        result_table = template.safe_substitute(table_json=json.dumps(results))

    report_file_name = f'report-{log_file.date.strftime("%Y%m%d")}.html'
    report_full_path = os.path.join(config.REPORT_DIR, report_file_name)
    with open(report_full_path, 'w', encoding='utf-8') as result_file:
        result_file.write(result_table)


def process_request_logs(
        request_logs: Generator[RequestLog, None, None],
) -> tuple[list[RequestStat], float]:
    total_count = 0
    total_lines = 0
    total_duration = .0
    failed_count = 0
    request_stats: dict[str, RequestStat] = {}

    for request_log in request_logs:
        total_lines += 1

        if not request_log.success:
            failed_count += 1
            continue

        if request_log.request.name not in request_stats:
            request_stat = RequestStat(url=request_log.request.name)
            request_stats[request_log.request.name] = request_stat
        else:
            request_stat = request_stats[request_log.request.name]

        total_count += 1
        request_stat.count += 1

        total_duration += request_log.duration
        request_stat.times.append(request_log.duration)

    for request_stat in request_stats.values():
        request_stat.calculate_stats(total_count, total_duration)

    fault_rate = failed_count / total_lines if total_lines else 0
    return list(request_stats.values()), fault_rate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', default='config.json')
    args = parser.parse_args()

    config = parse_config(args.config)

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        level='INFO',
        filename=config.SCRIPT_LOG_FILE,
    )

    logger = logging.getLogger(__name__)
    logger.info(config)

    try:
        next_log_file = get_next_log_file(config)
        if next_log_file is None:
            logger.info('no new files were found, finishing.')
            return

        log_file_path = os.path.join(config.LOG_DIR, next_log_file.name)
        request_logs = log_readlines(log_file_path)

        request_stats, fault_rate = process_request_logs(
            request_logs=request_logs,
        )
        logger.info('Fault rate is %.5f', fault_rate)
        if fault_rate > .5:
            logger.error('Fault rate is too high, finishing.')
            return

        save_result(config, request_stats, next_log_file)
    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    main()
