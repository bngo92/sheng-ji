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
        ranks1 = Hand.fromstr("S2,S3").cards
        ranks2 = Hand.fromstr("S2,S4").cards
        ranks3 = Hand.fromstr("S2,S3,S4").cards
        ranks4 = Hand.fromstr("SA,S2,H2,BS,RS").cards

        # Normal case
        self.assertTrue(is_consecutive(ranks1, HEARTS, FOUR))
        self.assertFalse(is_consecutive(ranks2, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks3, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks4, HEARTS, TWO))

        # Normal case with trump_rank in between
        self.assertTrue(is_consecutive(ranks2, HEARTS,THREE))


class PlayTest(TestCase):
    def test_init(self):
        # pair of offsuit trump
        cards = Hand.fromstr("S2,D2").cards
        play = Play(cards, HEARTS, TWO)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(len(play.combinations) == 2)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 1)
        self.assertFalse(combination['consecutive'])
        self.assertTrue(combination['rank'] == OFFSUIT_TRUMP)

        combination = play.combinations[1]
        self.assertTrue(combination['n'] == 1)
        self.assertFalse(combination['consecutive'])
        self.assertTrue(combination['rank'] == OFFSUIT_TRUMP)

        # tractor
        cards = Hand.fromstr("S2,S2,S3,S3").cards
        play = Play(cards, HEARTS, FOUR)
        self.assertTrue(play.suit == SPADES)
        self.assertTrue(len(play.combinations) == 1)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 2)
        self.assertTrue(combination['consecutive'])
        self.assertTrue(combination['rank'] == THREE)

        # combination
        cards = Hand.fromstr("S2,S3").cards
        play = Play(cards, HEARTS, FOUR)
        self.assertTrue(play.suit == SPADES)
        self.assertTrue(len(play.combinations) == 2)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 1)
        self.assertFalse(combination['consecutive'])
        rank1 = combination['rank']

        combination = play.combinations[1]
        self.assertTrue(combination['n'] == 1)
        self.assertFalse(combination['consecutive'])
        rank2 = combination['rank']
        self.assertTrue(sorted([rank1, rank2]) == sorted([TWO, THREE]))
