import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    REPORT_SIZE: int = 1000
    REPORT_DIR: str = './reports'
    LOG_DIR: str = './log'
    SCRIPT_LOG_FILE: Optional[str] = None


def parse_config(file_name: str) -> Config:
    config = Config()
    with open(file_name) as config_file:
        config_dict = json.load(config_file)

    if 'report_size' in config_dict:
        config.REPORT_SIZE = config_dict['report_size']
    if 'report_dir' in config_dict:
        config.REPORT_DIR = config_dict['report_dir']
    if 'log_dir' in config_dict:
        config.LOG_DIR = config_dict['log_dir']
    if 'script_log_file' in config_dict:
        config.SCRIPT_LOG_FILE = config_dict['script_log_file']

    return config
