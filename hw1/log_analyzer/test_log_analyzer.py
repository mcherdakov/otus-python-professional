import unittest
from typing import Generator

from log_analyzer import process_request_logs, RequestStat
from log_parser import Request, RequestLog


class TestLogAnalyzer(unittest.TestCase):
    @staticmethod
    def _log_line_generator(
        logs: list[tuple[str, float, bool]],
    ) -> Generator[RequestLog, None, None]:
        for name, duration, success in logs:
            yield RequestLog(
                request=Request(name=name),
                duration=duration,
                success=success,
            )

    def _cmp_stats(self, stat1: RequestStat, stat2: RequestStat) -> None:
        precision = 3
        self.assertEqual(stat1.url, stat2.url)
        self.assertEqual(stat1.count, stat2.count)
        self.assertAlmostEqual(stat1.count_perc, stat2.count_perc, precision)
        self.assertAlmostEqual(stat1.time_sum, stat2.time_sum, precision)
        self.assertAlmostEqual(stat1.time_med, stat2.time_med, precision)
        self.assertAlmostEqual(stat1.time_perc, stat2.time_perc, precision)
        self.assertAlmostEqual(stat1.time_avg, stat2.time_avg, precision)

    def test_empty_file(self) -> None:
        request_stats, fault_rate = process_request_logs(
            request_logs=self._log_line_generator([]),
        )

        self.assertListEqual(request_stats, [])
        self.assertAlmostEqual(fault_rate, 0.)

    def test_success_stat(self) -> None:
        log_generator = self._log_line_generator(
            [
                ('request1', 1., True), ('request1', 2., True),
                ('request1', 3., True), ('request2', 2., True),
                ('request2', 3., True),
            ]
        )

        request_stats, fault_rate = process_request_logs(
            request_logs=log_generator,
        )
        self.assertEqual(len(request_stats), 2)
        self.assertAlmostEqual(fault_rate, 0.)

        expected_stat1 = RequestStat(
            url='request1', count=3, count_perc=60., time_sum=6.,
            time_perc=6./11.*100, time_avg=2., time_med=2.,
        )
        expected_stat2 = RequestStat(
            url='request2', count=2, count_perc=40., time_sum=5.,
            time_perc=5./11.*100, time_avg=2.5, time_med=2.5,
        )

        if request_stats[0].url == 'request1':
            stat1, stat2 = request_stats[0], request_stats[1]
        else:
            stat2, stat1 = request_stats[0], request_stats[1]

        self._cmp_stats(expected_stat1, stat1)
        self._cmp_stats(expected_stat2, stat2)

    def test_fault_rate(self) -> None:
        log_generator = self._log_line_generator(
            [
                ('request1', 1., True), ('request1', 2., True),
                ('request2', 3., False), ('request3', 5., False),
            ]
        )

        request_stats, fault_rate = process_request_logs(
            request_logs=log_generator,
        )
        self.assertEqual(len(request_stats), 1)
        self.assertAlmostEqual(fault_rate, 0.5)


if __name__ == '__main__':
    unittest.main()
