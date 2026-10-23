"""Limit task responses to the requested dates within the latest two months."""
from calendar import monthrange
from datetime import date, timedelta
from urllib.parse import parse_qs


def earliest_date(today):
    month_index = today.year * 12 + today.month - 1 - 2
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(today.day, monthrange(year, month)[1])) + timedelta(days=1)


def tasks_for_dates(tasks, query='', today=None):
    today = today or date.today()
    params = parse_qs(query, keep_blank_values=True)
    if 'start' in params or 'end' in params:
        if any(len(params.get(key, [])) != 1 for key in ('start', 'end')):
            raise ValueError('조회 시작일과 종료일을 함께 입력해 주세요.')
        try:
            start, end = (date.fromisoformat(params[key][0]) for key in ('start', 'end'))
        except ValueError:
            raise ValueError('조회 날짜는 YYYY-MM-DD 형식이어야 합니다.') from None
        if start > end:
            raise ValueError('조회 시작일은 종료일보다 늦을 수 없습니다.')
    else:
        start = end = today
    start = max(start, earliest_date(today))
    end = min(end, today)
    return [task for task in tasks if start.isoformat() <= task['date'] <= end.isoformat()]
