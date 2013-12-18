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
        ranks4 = Hand.fromstr("S14,S2,H2,B15,R15").cards

        # Normal case
        self.assertTrue(is_consecutive(ranks1, HEARTS, FOUR))
        self.assertFalse(is_consecutive(ranks2, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks3, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks4, HEARTS, TWO))

        # Normal case with trump_rank in between
        self.assertTrue(is_consecutive(ranks2, HEARTS, THREE))


class PlayTest(TestCase):
    def test_init(self):
        # pair of offsuit trump
        cards = Hand.fromstr("S2,D2").cards
        play = Play(cards, HEARTS, TWO)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(len(play.combinations) == 2)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 1)
        self.assertTrue(combination['consecutive'] == 1)
        self.assertTrue(combination['rank'] == OFFSUIT_TRUMP)

        combination = play.combinations[1]
        self.assertTrue(combination['n'] == 1)
        self.assertTrue(combination['consecutive'] == 1)
        self.assertTrue(combination['rank'] == OFFSUIT_TRUMP)

        # tractor
        cards = Hand.fromstr("S2,S2,S3,S3").cards
        play = Play(cards, HEARTS, FOUR)
        self.assertTrue(play.suit == SPADES)
        self.assertTrue(len(play.combinations) == 1)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 2)
        self.assertTrue(combination['consecutive'] == 2)
        self.assertTrue(combination['rank'] == THREE)

        # combination
        cards = Hand.fromstr("S2,S3").cards
        play = Play(cards, HEARTS, FOUR)
        self.assertTrue(play.suit == SPADES)
        self.assertTrue(len(play.combinations) == 2)

        combination = play.combinations[0]
        self.assertTrue(combination['n'] == 1)
        self.assertTrue(combination['consecutive'] == 1)
        rank1 = combination['rank']

        combination = play.combinations[1]
        self.assertTrue(combination['n'] == 1)
        self.assertTrue(combination['consecutive'] == 1)
        rank2 = combination['rank']
        self.assertTrue(sorted([rank1, rank2]) == sorted([TWO, THREE]))


class GameTest(TestCase):
    def test_game(self):
        players = [Player.create_player(s, s) for s in ('a', 'b', 'c', 'd')]
        game = Game.setup(players)
        players = game.gameplayer_set.all()

        for player in players:
            game.ready(player)

        players_cycle = itertools.cycle(players)
        while game.stage == Game.DEAL:
            player = next(players_cycle)
            if not game.deal(player):
                break

        for player in players:
            self.assertTrue(len(Hand.fromstr(player.hand)) == game.hand_size())
        self.assertTrue(len(Hand.fromstr(game.deck)) == game.reserve_size())

        player = players[0]
        self.assertIsNone(game.pickup_reserve(player))
        self.assertTrue(len(Hand.fromstr(player.hand)) == game.hand_size() + game.reserve_size())
        self.assertTrue(len(Hand.fromstr(game.deck)) == 0)

        self.assertIsNone(game.reserve(player, player.get_hand().cards[:8]))
        self.assertTrue(len(Hand.fromstr(player.hand)) == game.hand_size())
        self.assertTrue(len(Hand.fromstr(game.kitty)) == game.reserve_size())
