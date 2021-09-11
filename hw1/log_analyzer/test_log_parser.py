import unittest
import re
from datetime import datetime

from log_parser import File, log_format_regexp, parse_log_line


class TestLogParser(unittest.TestCase):
    def _assert_datetimes(
            self,
            file_name: str,
            log_dt: datetime
    ) -> None:
        log_file = File.from_file_name(file_name)
        self.assertEqual(log_file.date, log_dt)

    def test_log_regexp(self) -> None:
        self.assertTrue(
            re.match(log_format_regexp, 'nginx-access-ui.log-12345678'),
        )
        self.assertTrue(
            re.match(log_format_regexp, 'nginx-access-ui.log-12345678.gz'),
        )
        self.assertFalse(
            re.match(log_format_regexp, 'nginx-access-ui.log-12345678.bz2'),
        )
        self.assertFalse(
            re.match(log_format_regexp, 'some-other-app.log-12345678.gz'),
        )

    def test_file_creation(self) -> None:
        self._assert_datetimes(
            'nginx-access-ui.log-20211212',
            datetime(2021, 12, 12),
        )
        self._assert_datetimes(
            'nginx-access-ui.log-20211111.gz',
            datetime(2021, 11, 11),
        )
        self._assert_datetimes(
            'report-20211212.html',
            datetime(2021, 12, 12),
        )

    def test_log_format(self) -> None:
        request_log = parse_log_line(
            '1.200.76.128 f032b48fb33e1e692  - [29/Jun/2017:03:50:24 +0300]'
            '"GET /api/1/campaigns/?id=7789711 HTTP/1.1" 200 608 "-" "-" "-" '
            '"1498697424-4102637017-4708-9752795" "-" 0.163'
        )
        self.assertEqual(
            request_log.request.name,
            '/api/1/campaigns/?id=7789711',
        )
        self.assertAlmostEqual(request_log.duration, 0.163)
        self.assertEqual(request_log.success, True)

        with self.assertRaises(ValueError):
            parse_log_line('')


if __name__ == '__main__':
    unittest.main()
