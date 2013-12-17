from collections import Counter
from functools import total_ordering
import json
import random
import itertools

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models, IntegrityError


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
TRUMP = 'TRUMP'
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
OFFSUIT_TRUMP = 'o'
ONSUIT_TRUMP = 'O'
SMALL_JOKER = 'x'
BIG_JOKER = 'X'
NORMAL_RANKS = (TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE)
RANKS = NORMAL_RANKS + (OFFSUIT_TRUMP, ONSUIT_TRUMP, SMALL_JOKER, BIG_JOKER)
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

    def is_trump(self, trump_suit, trump_rank):
        return self.suit == trump_suit or self.rank in (trump_rank, JOKER)

    def get_suit(self, trump_suit, trump_rank):
        if self.is_trump(trump_suit, trump_rank):
            return TRUMP
        else:
            return self.suit

    def get_rank(self, trump_suit, trump_rank):
        if self.rank == JOKER:
            if self.suit == BLACK:
                return SMALL_JOKER
            else:
                return BIG_JOKER
        elif self.rank == trump_rank:
            if self.suit == trump_suit:
                return ONSUIT_TRUMP
            else:
                return OFFSUIT_TRUMP
        else:
            return self.rank


def create_deck():
    return ([Card(suit, rank) for suit in NORMAL_SUITS for rank in NORMAL_RANKS] +
            [Card(suit, JOKER) for suit in JOKER_SUITS])


def is_consecutive(ranks, trump_rank):
    if len(ranks) < 2:
        return False

    ranks = map(RANKS.index, ranks)
    trump_rank = RANKS.index(trump_rank)
    min_rank = min(ranks)
    max_rank = max(ranks)
    return (sorted(ranks + [trump_rank]) == range(min_rank, max_rank + 1) if min_rank < trump_rank < max_rank else
            sorted(ranks) == range(min_rank, max_rank + 1))


class Hand(object):
    def __init__(self, cards=None):
        if cards is None:
            self.cards = []
        else:
            self.cards = cards[:]

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

    def single_suit(self, trump_suit, trump_rank):
        suits = set(card.get_suit(trump_suit, trump_rank) for card in self.cards)
        if len(suits) == 1:
            return next(iter(suits))
        else:
            return None

    def has_suit(self, suit, trump_suit, trump_rank):
        return any(card.get_suit(trump_suit, trump_rank) == suit for card in self.cards)

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


class Play(object):
    def __init__(self, cards, trump_rank):
        self.suit = next(iter(cards)).suit
        self.combinations = []
        ranks = Counter(card.get_rank() for card in cards)

        subsets = {}
        for k, v in ranks.iteritems():
            if v >= 2:
                subsets.setdefault(v, []).append(k)

        for subset in subsets.itervalues():
            i = len(subset)
            while i > 1:
                permutations = itertools.permutations(subset, i)
                for r in permutations:
                    if is_consecutive(r, trump_rank):
                        self.combinations.append({'n': len(r), 'consecutive': True, 'rank': RANKS[max(map(RANKS.index, r))]})
                        for rank in r:
                            del ranks[rank]
                            subset.remove(rank)
                        i = len(subset)
                        break
                else:
                    i -= 1

        for k, v in ranks.iteritems():
            self.combinations.append({'n': v, 'consecutive': False, 'rank': k})

    def encode(self):
        return json.dumps({'suit': self.suit, 'combinations': self.combinations})

    @classmethod
    def decode(cls, s):
        play_dict = json.loads(s)
        play = cls()
        play.suit = play_dict['suit']
        play.combinations = play_dict['combinations']
        return play


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
    #lead_play = models.CharField(max_length=100)
    #lead_play_n = models.IntegerField()

    # Trump details
    trump_rank = models.CharField(max_length=1, choices=RANK_CHOICES)
    trump_suit = models.CharField(max_length=1, choices=SUIT_CHOICES, default=RED)
    trump_count = models.IntegerField(default=0)
    trump_broken = models.BooleanField(default=False)

    SETTINGS = {
        # (number of players, number of decks, hand size))
        4: (2, 25, 8),  # 2 * 54 = 108; 4 * 25 + 8 = 108
        5: (2, 20, 8),  # 2 * 54 = 108; 5 * 20 + 8 = 108
        6: (3, 25, 6),  # 3 * 54 = 162; 6 * 26 + 6 = 162
        7: (3, 25, 8),  # 3 * 54 = 162; 7 * 22 + 8 = 162
        8: (4, 25, 8),  # 4 * 54 = 216; 8 * 26 + 8 = 216
    }

    def __unicode__(self):
        return 'Game #{}'.format(self.id)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('main.views.game', args=[str(self.id)])

    def number_of_players(self):
        return self.gameplayer_set.count()

    def number_of_decks(self, number_of_players=None):
        if number_of_players is None:
            return Game.SETTINGS[self.number_of_players()][0]
        else:
            return Game.SETTINGS[number_of_players][0]

    def hand_size(self):
        return Game.SETTINGS[self.number_of_players()][1]

    def reserve_size(self):
        return Game.SETTINGS[self.number_of_players()][2]

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
            game.trump_rank = player.rank
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

    def set_trump_suit(self, player, cards):
        if self.stage != Game.DEAL:
            return False

        if any(card.rank != self.trump_rank for card in cards):
            return False

        player_hand = Hand.fromstr(player.hand)
        if not cards in player_hand:
            return False

        if len(cards) > self.trump_count:
            self.trump_count = len(cards)
            self.trump_suit = next(iter(cards)).suit
            self.save()

            play = Hand(cards)
            player.play = str(play)
            player.save()

    def reserve(self, player, cards):
        if self.stage != Game.RESERVE or player.turn != 0:
            return False

        player_hand = Hand.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if len(cards) != self.reserve_size():
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
    def create_player(cls, username, password):
        player = cls()
        try:
            player.user = User.objects.create_user(username, password=password)
            player.save()
            return player
        except IntegrityError:
            return None


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
        if 'register' in self.data:
            Player.create_player(username=cleaned_data.get('username'), password=cleaned_data.get('password'))
        user = authenticate(username=cleaned_data.get('username'), password=cleaned_data.get('password'))
        if user is None:
            self._errors['password'] = self.error_class(["Incorrect password."])
        else:
            cleaned_data['user'] = user
        return cleaned_data
