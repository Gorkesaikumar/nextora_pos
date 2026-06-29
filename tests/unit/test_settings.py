import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import unittest
from contexts.restaurant.forms import BranchForm, PrinterForm


class TestSettingsForms(unittest.TestCase):

    def test_branch_form_validation_fails_on_empty(self):
        # Empty form should be invalid
        form = BranchForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('code', form.errors)

    def test_printer_form_validation_fails_on_empty(self):
        # Empty form should be invalid
        form = PrinterForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('code', form.errors)
