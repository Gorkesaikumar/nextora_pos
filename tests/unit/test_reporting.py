import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import unittest
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.utils import timezone

from contexts.reporting.views import get_date_range, _fmt_inr


class TestReportingHelpers(unittest.TestCase):

    def test_fmt_inr(self):
        self.assertEqual(_fmt_inr(Decimal("123456.78")), "1,23,456.78")
        self.assertEqual(_fmt_inr(Decimal("1250000.00")), "12,50,000.00")
        self.assertEqual(_fmt_inr(0), "0.00")

    def test_get_date_range_presets(self):
        today = timezone.localdate()
        
        # Test 'today' preset
        start, end, s_date, e_date = get_date_range('today')
        self.assertEqual(s_date, today)
        self.assertEqual(e_date, today)
        self.assertEqual(start.time(), datetime.min.time())
        self.assertEqual(end.time(), datetime.max.time())
        
        # Test 'yesterday' preset
        start, end, s_date, e_date = get_date_range('yesterday')
        self.assertEqual(s_date, today - timedelta(days=1))
        self.assertEqual(e_date, today - timedelta(days=1))
        
        # Test 'last_7_days' preset
        start, end, s_date, e_date = get_date_range('last_7_days')
        self.assertEqual(s_date, today - timedelta(days=6))
        self.assertEqual(e_date, today)
