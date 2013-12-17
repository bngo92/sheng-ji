"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from main.models import *


class CardTest(TestCase):
    def test_consecutive(self):
        # Normal case
        self.assertTrue(is_consecutive(TWO, THREE, FOUR))
        self.assertFalse(is_consecutive(TWO, FOUR, FIVE))

        # Normal case with trump_rank in between
        self.assertTrue(is_consecutive(TWO, FOUR, THREE))

        self.assertFalse(is_consecutive(TWO, TWO, TWO))
        self.assertFalse(is_consecutive(TWO, TWO, THREE))
