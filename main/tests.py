"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from main.models import *


class CardTest(TestCase):
    def test_consecutive(self):
        two = Card('', TWO)
        three = Card('', THREE)
        four = Card('', FOUR)

        self.assertFalse(two.is_consecutive(two, THREE))
        self.assertTrue(two.is_consecutive(three, FOUR))
        self.assertFalse(two.is_consecutive(three, THREE))
        self.assertTrue(two.is_consecutive(four, THREE))
