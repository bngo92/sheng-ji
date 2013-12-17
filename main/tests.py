"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "game.settings")

from django.test import TestCase
from main.models import *


class CardTest(TestCase):
    def test_consecutive(self):
        ranks1 = [TWO, THREE]
        ranks2 = [TWO, FOUR]
        ranks3 = [TWO, THREE, FOUR]
        ranks4 = [ACE, OFFSUIT_TRUMP, ONSUIT_TRUMP, SMALL_JOKER, BIG_JOKER]

        # Normal case
        self.assertTrue(is_consecutive(ranks1, FOUR))
        self.assertFalse(is_consecutive(ranks2, FIVE))
        self.assertTrue(is_consecutive(ranks3, FIVE))
        self.assertTrue(is_consecutive(ranks4, TWO))

        # Normal case with trump_rank in between
        self.assertTrue(is_consecutive(ranks2, THREE))
