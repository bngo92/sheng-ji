"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from main.models import *


class CardTest(TestCase):
    def test_consecutive(self):
        ranks1 = Hand.fromstr("S2,S3").cards
        ranks2 = Hand.fromstr("S2,S4").cards
        ranks3 = Hand.fromstr("S2,S3,S4").cards
        ranks4 = Hand.fromstr("S14,S2,H2,J17,J18").cards

        # Normal case
        self.assertTrue(is_consecutive(ranks1, HEARTS, FOUR))
        self.assertFalse(is_consecutive(ranks2, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks3, HEARTS, FIVE))
        self.assertTrue(is_consecutive(ranks4, HEARTS, TWO))

        # Normal case with trump_rank in between
        self.assertTrue(is_consecutive(ranks2, HEARTS, THREE))


class PlayTest(TestCase):
    def assert_combination(self, combination, n, consecutive, rank):
        self.assertEqual(combination['n'], n)
        self.assertEqual(combination['consecutive'], consecutive)
        self.assertEqual(combination['rank'], rank)

    def test_init(self):
        trump_suit = CLUBS
        trump_rank = SEVEN

        s = "H5,H5,H4,H4"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == HEARTS)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 2, FIVE)

        s = "S11,S11,S10,S10,S9,S9,S8,S8"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == SPADES)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 4, JACK)

        s = "C5,C5,C4,C4,C3,C3"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 3, FIVE)

        s = "D8,D8,D6,D6"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == DIAMONDS)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 2, EIGHT)

        s = "C7,C7,D7,D7,C14,C14"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 3, ONSUIT_TRUMP)

        s = "J18,J18,J17,J17,C7,C7"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 1)
        self.assert_combination(play.combinations[0], 2, 3, RED)

        s = "H10,H10,H8,H8"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == HEARTS)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 2)
        self.assert_combination(play.combinations[0], 2, 1, TEN)
        self.assert_combination(play.combinations[1], 2, 1, EIGHT)

        s = "S9,S9,D8,D8"
        hand = Hand.fromstr(s)
        self.assertFalse(hand.single_suit(trump_suit, trump_rank))

        s = "H7,H7,H6,H6"
        hand = Hand.fromstr(s)
        self.assertFalse(hand.single_suit(trump_suit, trump_rank))

        s = "C7,C7,C6,C6"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 2)
        self.assert_combination(play.combinations[0], 2, 1, ONSUIT_TRUMP)
        self.assert_combination(play.combinations[1], 2, 1, SIX)

        s = "S7,S7,D7,D7"
        cards = Hand.fromstr(s).cards
        play = Play(cards, trump_suit, trump_rank)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(play.cards == s)
        self.assertTrue(len(play.combinations) == 2)
        self.assert_combination(play.combinations[0], 2, 1, OFFSUIT_TRUMP)
        self.assert_combination(play.combinations[1], 2, 1, OFFSUIT_TRUMP)

        s = "C2,C2,S14,S14"
        hand = Hand.fromstr(s)
        self.assertFalse(hand.single_suit(trump_suit, trump_rank))

        # pair of offsuit trump
        cards = Hand.fromstr("S2,D2").cards
        play = Play(cards, HEARTS, TWO)
        self.assertTrue(play.suit == TRUMP)
        self.assertTrue(len(play.combinations) == 2)

        combination = play.combinations[0]
        self.assert_combination(combination, 1, 1, OFFSUIT_TRUMP)

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
    def assert_combination(self, combination, n, consecutive, rank):
        self.assertEqual(combination['n'], n)
        self.assertEqual(combination['consecutive'], consecutive)
        self.assertEqual(combination['rank'], rank)

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

    def test_play(self):
        players = [Player.create_player(s, s) for s in ('a', 'b', 'c', 'd')]
        game = Game.setup(players)
        game.trump_rank = SEVEN
        players = game.gameplayer_set.all()
        player = players[0]

        hand = Hand.fromstr("C7")
        self.assertFalse(game.set_trump_suit(player, hand.cards))

        game.stage = Game.DEAL
        game.save()
        self.assertFalse(game.set_trump_suit(player, hand.cards))

        player.hand = str(hand)
        player.save()
        self.assertIsNone(game.set_trump_suit(player, hand.cards))

        self.assertEqual(game.trump_suit, CLUBS)

        hands = [Hand.fromstr(s) for s in ("D13,D12", "D13,D2")]
        player0 = players[0]
        player0.hand = str(hands[0])
        player0.save()
        player1 = players[1]
        player1.hand = str(hands[1])
        player1.save()
        self.assertFalse(game.play(player0, hands[0].cards))

        game.stage = Game.PLAY
        game.save()
        self.assertIsNone(game.play(player0, hands[0].cards))
        self.assertEqual(player0.hand, "D13")
        play = Play.decode(player0.play)
        self.assertEqual(len(play.combinations), 1)
        self.assertEqual(play.suit, DIAMONDS)
        self.assert_combination(play.combinations[0], 1, 1, QUEEN)
        self.assertEqual(play.cards, "D12")

        lead_play = Play.decode(game.gameplayer_set.all()[game.lead].play)
        self.assertEqual(lead_play.suit, DIAMONDS)
        self.assertEqual(lead_play.rank, QUEEN)

        self.assertTrue(game.play(player1, hands[1].cards))
        self.assertEqual(game.lead, 0)

        self.assertIsNone(game.play(player1, hands[1].cards[:1]))
        self.assertEqual(player1.hand, "D2")
        play = Play.decode(player1.play)
        self.assertEqual(len(play.combinations), 1)
        self.assertEqual(play.suit, DIAMONDS)
        self.assert_combination(play.combinations[0], 1, 1, KING)
        self.assertEqual(play.cards, "D13")
        self.assertEqual(game.lead, 1)

        lead_play = Play.decode(game.gameplayer_set.all()[game.lead].play)
        self.assertEqual(lead_play.suit, DIAMONDS)
        self.assertEqual(lead_play.rank, KING)
