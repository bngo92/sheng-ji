from collections import Counter
from functools import total_ordering
import random
import itertools

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models


DECLARERS = 'A'
OPPONENTS = 'B'
TEAM_CHOICES = (
    (DECLARERS, 'Declarers'),
    (OPPONENTS, 'Opponents'),
)

CLUBS = 'C'
DIAMONDS = 'D'
HEARTS = 'H'
SPADES = 'S'
NORMAL_SUITS = (CLUBS, DIAMONDS, HEARTS, SPADES)
BLACK = 'B'
RED = 'R'
JOKER_SUITS = (BLACK, RED)
SUIT_CHOICES = (
    (CLUBS, 'Clubs'),
    (DIAMONDS, 'Diamonds'),
    (HEARTS, 'Hearts'),
    (SPADES, 'Spades'),
    # jokers
    (BLACK, 'Black'),
    (RED, 'Red'),
)

TWO = '2'
THREE = '3'
FOUR = '4'
FIVE = '5'
SIX = '6'
SEVEN = '7'
EIGHT = '8'
NINE = '9'
TEN = 'T'
JACK = 'J'
QUEEN = 'Q'
KING = 'K'
ACE = 'A'
JOKER = 'S'
NORMAL_RANKS = (TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE)
RANK_CHOICES = (
    (TWO, '2'),
    (THREE, '3'),
    (FOUR, '4'),
    (FIVE, '5'),
    (SIX, '6'),
    (SEVEN, '7'),
    (EIGHT, '8'),
    (NINE, '9'),
    (TEN, '10'),
    (JACK, 'Jack'),
    (QUEEN, 'Queen'),
    (KING, 'King'),
    (ACE, 'Ace'),
    #jokers
    (JOKER, 'Jokers'),
)


@total_ordering
class Card(object):
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    @classmethod
    def fromstr(cls, s):
        return cls(suit=s[0], rank=s[1])

    def __eq__(self, other):
        return (self.suit, self.rank) == (other.suit, other.rank)

    def __lt__(self, other):
        if self.suit in NORMAL_SUITS:
            if other.suit in JOKER_SUITS:
                return True
            else:
                key = NORMAL_SUITS
        else:
            if other.suit in JOKER_SUITS:
                key = JOKER_SUITS
            else:
                return False
        return key.index(self.suit) < key.index(other.suit)

    def __str__(self):
        return self.suit + self.rank

    def __hash__(self):
        return self.suit, self.rank

    def image(self):
        return '{}_of_{}.png'.format(dict(RANK_CHOICES)[self.rank], dict(SUIT_CHOICES)[self.suit]).lower()

    def repr(self):
        return {'card': self.__str__(), 'image': self.image()}


def create_deck():
    return ([Card(suit, rank) for suit in NORMAL_SUITS for rank in NORMAL_RANKS] +
            [Card(suit, JOKER) for suit in JOKER_SUITS])


class Hand(object):
    def __init__(self, cards=None):
        if cards is None:
            self.cards = []
        else:
            self.cards = cards

    @classmethod
    def fromstr(cls, s):
        return cls(cards=[Card.fromstr(ss) for ss in s.split(',')] if s else [])

    def __len__(self):
        return len(self.cards)

    def __contains__(self, items):
        cards = self.cards[:]

        for item in items:
            try:
                cards.remove(item)
            except ValueError:
                return False

        return True

    def __str__(self):
        return ','.join(str(card) for card in self.cards)

    def add_card(self, card):
        self.cards.append(card)

    def add_cards(self, cards):
        for card in cards:
            self.cards.append(card)

    def play_card(self, card):
        self.cards.remove(card)

    def play_cards(self, cards):
        for card in cards:
            self.cards.remove(card)

    def pop(self):
        return self.cards.pop()

    def sort(self, key=None):
        if key is None:
            self.cards.sort(key=key)
        else:
            self.cards.sort()

    def has_suit(self, suit, trump_rank):
        return any(card.suit == suit and card.rank != trump_rank for card in self.cards)

    def has_trump(self, trump_suit, trump_rank):
        return any(card.suit == trump_suit or card.rank in (trump_rank, JOKER) for card in self.cards)

    def has_ntuple(self, suit, n, trump_rank):
        return any(count >= n
                   for count in Counter(card
                                        for card in self.cards
                                        if card.suit == suit and card.rank != trump_rank).itervalues())

    def has_trump_ntuple(self, trump_suit, n, trump_rank):
        return any(count >= n
                   for count in Counter(card
                                        for card in self.cards
                                        if card.suit == trump_suit or card.rank in (trump_rank, JOKER)).itervalues())

    def has_consecutive_ntuple(self, suit, n, trump_rank):
        ranks = sorted(set(NORMAL_RANKS.index(card.rank)
                           for card, count in Counter(card
                                                      for card in self.cards
                                                      if card.suit == suit and card.rank != trump_rank).iteritems()
                           if count >= n))
        return any(abs(t1 - t0) == 1 or t0 + t1 == trump_rank * 2
                   for t0, t1 in itertools.combinations(ranks, 2))

    def has_trump_consecutive_ntuple(self, trump_suit, n, trump_rank):
        ranks = sorted(set(NORMAL_RANKS.index(card.rank)
                           for card, count in Counter(card
                                                      for card in self.cards
                                                      if card.suit == trump_suit and card.rank in (trump_rank, JOKER)).iteritems()
                           if count >= n))
        return any(abs(t1 - t0) == 1 or t0 + t1 == trump_rank * 2
                   for t0, t1 in itertools.combinations(ranks, 2))

    def has_higher(self, cards):
        return any(card.suit == next(cards).suit and card > min(cards) for card in self.cards)


class Game(models.Model):
    SETUP = '1'
    DEAL = '2'
    RESERVE = '3'
    PLAY = '4'
    SCORE = '5'
    STAGE_CHOICES = (
        (SETUP, 'Setup'),
        (DEAL, 'Deal'),
        (RESERVE, 'Reserve'),
        (PLAY, 'Play'),
        (SCORE, 'Score'),
    )

    SINGLE = 'A'
    CONSECUTIVE = 'B'
    COMBINATION = 'C'
    PLAY_CHOICES = (
        (SINGLE, 'Single'),
        (CONSECUTIVE, 'Consecutive'),
        (COMBINATION, 'Combination'),
    )

    # Game details
    stage = models.CharField(max_length=1, choices=STAGE_CHOICES, default=SETUP)
    turn = models.IntegerField(default=0)
    trick_turn = models.IntegerField(default=0)

    # Cards
    deck = models.CharField(max_length=1000)
    kitty = models.CharField(max_length=100)
    #lead_play = models.CharField(max_length=1)
    #lead_play_n = models.IntegerField()

    # Trump details
    dominant_rank = models.CharField(max_length=1, choices=RANK_CHOICES)
    dominant_suit = models.CharField(max_length=1, choices=SUIT_CHOICES, default=RED)
    dominant_count = models.IntegerField(default=0)

    SETTINGS = {
        # (number of players, number of decks, hand size))
        4: (2, 25),  # 2 * 54 = 108; 4 * 25 + 8 = 108
        5: (2, 20),  # 2 * 54 = 108; 5 * 20 + 8 = 108
        6: (3, 25),  # 3 * 54 = 162; 6 * 26 + 6 = 162
        7: (3, 25),  # 3 * 54 = 162; 7 * 22 + 8 = 162
        8: (4, 25),  # 4 * 54 = 216; 8 * 26 + 8 = 216
    }

    def __unicode__(self):
        return 'Game #{}'.format(self.id)

    def get_absolute_url(self):
        return '/game/{}'.format(self.id)

    def number_of_players(self):
        return self.gameplayer_set.count()

    def number_of_decks(self, number_of_players=None):
        if number_of_players is None:
            return Game.SETTINGS[self.number_of_players()][0]
        else:
            return Game.SETTINGS[number_of_players][0]

    def hand_size(self):
        return Game.SETTINGS[self.number_of_players()][1]

    @classmethod
    def setup(cls, players):
        game = cls()
        game.save()

        try:
            deck = [card for _ in range(game.number_of_decks(len(players))) for card in create_deck()]
        except KeyError:
            return False

        random.shuffle(deck)
        game.deck = ','.join(map(str, deck))
        game.kitty = ''

        def create_first_player(player, turn):
            game.dominant_rank = player.rank
            GamePlayer.objects.create(game=game, player=player, team=DECLARERS, turn=turn)

        def create_rest_player(player, turn):
            GamePlayer.objects.create(game=game, player=player, turn=turn)

        create_player = create_first_player
        for turn, player in enumerate(players):
            create_player(player, turn)
            create_player = create_rest_player

        game.save()
        return game

    def ready(self, player):
        if self.stage != Game.SETUP:
            return False

        player.ready = True
        player.save()

        if all(player.ready for player in self.gameplayer_set.all()):
            self.stage = Game.DEAL
            self.save()

    def deal(self, player):
        if self.stage != Game.DEAL or not player.your_turn():
            return False

        player_hand = Hand.fromstr(player.hand)
        if len(player_hand) >= self.hand_size():
            return False

        deck = Hand.fromstr(self.deck)
        draw = deck.pop()
        self.deck = str(deck)

        player_hand.add_card(draw)
        player.hand = str(player_hand)

        self.turn = (self.turn + 1) % self.number_of_players()
        self.save()
        player.save()

        return draw

    def set_dominant_suit(self, player, cards):
        if self.stage != Game.DEAL:
            return False

        if any(card.rank != self.dominant_rank for card in cards):
            return False

        player_hand = Hand.fromstr(player.hand)
        if not cards in player_hand:
            return False

        if len(cards) > self.dominant_count:
            self.dominant_count = len(cards)
            self.dominant_suit = next(iter(cards)).suit
            self.save()

    def reserve(self, player, cards):
        if self.stage != Game.RESERVE or player.turn != 0:
            return False

        player_hand = Hand.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if len(player_hand.cards) != self.hand_size():
            return False

        player_hand.play_cards(cards)
        player.hand = str(player_hand)
        player.save()

        kitty = Hand(cards)
        self.kitty = str(kitty)
        self.stage = Game.PLAY
        self.turn = 0
        self.trick_turn = 0
        self.save()
        return True

    def play(self, player, cards):
        if self.stage != Game.DEAL or not player.your_turn():
            return False

        player_hand = Hand.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if self.trick_turn == 0:
            if len(set(cards)) == 1:
                player_hand.play_cards(cards)
                self.lead_play = str(len(cards))
            elif len(set(cards)) == 2:
                tractor = list(set(cards))
                if (len([card for card in cards if card == tractor[0]]) ==
                        len([card for card in cards if card == tractor[1]])):
                    player_hand.play_cards(cards)

        else:
            #first_hand = Hand.fromstr(self.hands.split(';', 1))
            pass

        player.hand = player_hand
        player.save()
        self.trick_turn += 1

        if self.trick_turn == self.number_of_players():
            #hands = [Hand.fromstr(s) for s in self.hands.split(';')]
            #self.turn = winner
            self.trick_turn = 0

        self.save()


class Player(models.Model):
    user = models.ForeignKey(User)
    rank = models.CharField(max_length=1, choices=RANK_CHOICES, default=TWO)

    def __unicode__(self):
        return self.user.__unicode__()

    @classmethod
    def create_player(cls, username):
        player = cls()
        player.user = User.objects.create_user(username, password=username)
        player.save()


class GamePlayer(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(Player)

    team = models.CharField(max_length=1, choices=TEAM_CHOICES, default=OPPONENTS)
    ready = models.BooleanField(default=False)
    turn = models.IntegerField()
    points = models.IntegerField(default=0)
    hand = models.CharField(max_length=200, default='')
    play = models.CharField(max_length=200, default='')

    def __unicode__(self):
        return self.player.__unicode__()

    def get_hand(self):
        return Hand.fromstr(self.hand)

    def your_turn(self):
        return (self.game.turn + self.game.trick_turn) % self.game.number_of_players() == self.turn

    def get_play(self):
        return Hand.fromstr(self.play)


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.widgets.PasswordInput)

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        user = authenticate(username=cleaned_data.get('username'), password=cleaned_data.get('password'))
        if user is None:
            self._errors['password'] = self.error_class(["Incorrect password."])
        else:
            cleaned_data['user'] = user
        return cleaned_data
