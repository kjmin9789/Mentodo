from datetime import date
import unittest
from task_dates import earliest_date, tasks_for_dates


class TaskDateTests(unittest.TestCase):
    def test_calendar_month_boundaries(self):
        for today, expected in [
            (date(2026, 10, 23), date(2026, 8, 24)),
            (date(2026, 1, 31), date(2025, 12, 1)),
            (date(2024, 4, 30), date(2024, 3, 1)),
            (date(2026, 3, 31), date(2026, 2, 1)),
        ]:
            with self.subTest(today=today):
                self.assertEqual(earliest_date(today), expected)

    def test_default_today_and_bounded_response_without_deleting_history(self):
        rows = [{'date': value} for value in ['2026-08-23', '2026-08-24', '2026-10-22', '2026-10-23', '2026-10-24']]
        today = date(2026, 10, 23)
        self.assertEqual(tasks_for_dates(rows, today=today), [rows[3]])
        self.assertEqual(tasks_for_dates(rows, 'start=2020-01-01&end=2030-12-31', today), rows[1:4])
        self.assertEqual(tasks_for_dates(rows, 'start=2026-10-19&end=2026-10-25', today), rows[2:4])
        self.assertEqual(tasks_for_dates(rows, 'start=2026-01-01&end=2026-01-31', today), [])
        self.assertEqual(len(rows), 5)

    def test_reject_incomplete_invalid_or_reversed_range(self):
        for query in ['start=2026-10-23', 'end=2026-10-23', 'start=&end=',
                      'start=2026-02-30&end=2026-03-01',
                      'start=2026-10-24&end=2026-10-23',
                      'start=2026-10-22&start=2026-10-23&end=2026-10-23']:
            with self.subTest(query=query), self.assertRaises(ValueError):
                tasks_for_dates([], query)
