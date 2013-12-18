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
SUITS = NORMAL_SUITS + JOKER_SUITS
SUIT_CHOICES = (
    (CLUBS, 'Clubs'),
    (DIAMONDS, 'Diamonds'),
    (HEARTS, 'Hearts'),
    (SPADES, 'Spades'),
    # jokers
    (BLACK, 'Black'),
    (RED, 'Red'),
)

TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE, JOKER = range(2, 2 + 14)
OFFSUIT_TRUMP = JOKER
ONSUIT_TRUMP = JOKER + 1
SMALL_JOKER = JOKER + 2
BIG_JOKER = JOKER + 3
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
        return cls(suit=s[0], rank=int(s[1:]))

    def __eq__(self, other):
        return (self.suit, self.rank) == (other.suit, other.rank)

    def __lt__(self, other):
        return (SUITS.index(self.suit), self.rank) < (SUITS.index(other.suit), other.rank)

    def __str__(self):
        return self.suit + str(self.rank)

    def __hash__(self):
        return hash((self.suit, self.rank))

    def image(self):
        return '{}_of_{}.png'.format(dict(RANK_CHOICES)[self.rank], dict(SUIT_CHOICES)[self.suit]).lower()

    def repr(self):
        return {'card': str(self), 'image': self.image()}

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


def is_consecutive(cards, trump_suit, trump_rank):
    if len(cards) < 2:
        return False

    ranks = [RANKS.index(card.get_rank(trump_suit, trump_rank)) for card in cards]
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
            return suits.pop()
        else:
            return None

    def has_suit(self, suit, trump_suit, trump_rank):
        return any(card.get_suit(trump_suit, trump_rank) == suit for card in self.cards)


class Play(object):
    def __init__(self, cards=None, trump_suit=None, trump_rank=None, consecutive=True):
        self.cards = []
        self.suit = None
        self.combinations = None
        if cards is not None:
            self.init(cards, trump_suit, trump_rank, consecutive)

    def init(self, cards, trump_suit, trump_rank, consecutive=True):
        self.cards = str(Hand(cards))
        self.suit = cards[0].get_suit(trump_suit, trump_rank)
        self.combinations = []
        ranks = Counter(card for card in cards)

        if consecutive:
            subsets = {}
            for k, v in ranks.iteritems():
                if v >= 2:
                    subsets.setdefault(v, []).append(k)

            for n, subset in subsets.iteritems():
                i = len(subset)
                while i > 1:
                    permutations = itertools.permutations(subset, i)
                    for p in permutations:
                        if is_consecutive(p, trump_suit, trump_rank):
                            self.combinations.append(
                                {'n': n, 'consecutive': i,
                                 'rank': max(card.get_rank(trump_suit, trump_rank) for card in p)})
                            for rank in p:
                                del ranks[rank]
                                subset.remove(rank)
                            i = len(subset)
                            break
                    else:
                        i -= 1

        for k, v in ranks.iteritems():
            self.combinations.append({'n': v, 'consecutive': 1, 'rank': k.get_rank(trump_suit, trump_rank)})

    def encode(self):
        return json.dumps({'suit': self.suit, 'combinations': self.combinations, 'cards': self.cards})

    @classmethod
    def decode(cls, s):
        play_dict = json.loads(s)
        play = cls()
        play.suit = play_dict['suit']
        play.combinations = play_dict['combinations']
        play.cards = play_dict['cards']
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

    # Game details
    stage = models.CharField(max_length=1, choices=STAGE_CHOICES, default=SETUP)
    turn = models.IntegerField(default=0)
    trick_turn = models.IntegerField(default=0)
    trick_points = models.IntegerField(default=0)

    # Cards
    deck = models.CharField(max_length=1000)
    kitty = models.CharField(max_length=100)
    lead = models.IntegerField(default=0)

    # Trump details
    trump_rank = models.IntegerField(choices=RANK_CHOICES)
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
        game.trump_rank = players[0].rank
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
            return "Trump rank not played"

        if len(set(card.suit for card in cards)) != 1:
            return "Cards have to be a single suit"

        player_hand = Hand.fromstr(player.hand)
        if not cards in player_hand:
            return False

        if len(cards) > self.trump_count:
            self.trump_count = len(cards)
            self.trump_suit = cards[0].suit
            self.save()

            play = Play(cards, self.trump_suit, self.trump_rank)
            player.play = play.encode()
            player.save()
        else:
            return "Not enough cards to change trump suit"

    def pickup_reserve(self, player):
        if self.stage != Game.DEAL or player.turn != 0 or len(player.get_hand()) != self.hand_size():
            return False

        reserve = Hand.fromstr(self.deck)
        self.deck = ''
        self.stage = Game.RESERVE
        self.save()

        player_hand = player.get_hand()
        player_hand.add_cards(reserve.cards)
        player.hand = str(player_hand)
        player.save()

        for player in self.gameplayer_set.all():
            player.play = ''
            player.save()

    def reserve(self, player, cards):
        if self.stage != Game.RESERVE or player.turn != 0:
            return False

        player_hand = Hand.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if len(cards) != self.reserve_size():
            return "Incorrect number of cards were played"

        player_hand.play_cards(cards)
        player.hand = str(player_hand)
        player.save()

        kitty = Hand(cards)
        self.kitty = str(kitty)
        self.stage = Game.PLAY
        self.turn = 0
        self.trick_turn = 0
        self.save()

    def play(self, player, cards):
        if self.stage != Game.PLAY or not player.your_turn():
            return False

        player_hand = Hand.fromstr(player.hand)
        if cards not in player_hand:
            return False

        play = Hand(cards)
        player_hand.play_cards(play.cards)
        if self.trick_turn == 0:
            for other in self.gameplayer_set.all():
                other.play = ''
                other.save()

            # First player has to play a single suit
            suit = play.single_suit(self.trump_suit, self.trump_rank)
            if suit is None or (suit == TRUMP and not self.trump_broken):
                return "Cards have to be a single suit"

            # If combination is played, remove cards that aren't highest
            play = Play(play.cards, self.trump_suit, self.trump_rank)
            if len(play.combinations) > 1:
                not_highest = []
                for other in self.gameplayer_set.all():
                    if player == other:
                        continue

                    other_hand = [card for card in self.cards if card.suit == suit]
                    other_play = Play(other_hand, self.trump_suit, self.trump_rank, False)

                    for combination in play.combinations:
                        if combination['consecutive'] >= 2:
                            continue

                        for other_combination in other_play.combinations:
                            if (combination['n'] <= other_combination['n'] and
                                    combination['rank'] < other_combination['rank']):
                                not_highest.append(combination)

                if not_highest:
                    playable_combinations = [combination for combination in play.combinations
                                             if combination['consecutive'] >= 2]
                    playable_combinations.append(min(not_highest, key=lambda c: c['rank']))
                    play.combinations = playable_combinations

        else:
            # Other players have to play the suit that the first person played
            suit = play.single_suit(self.trump_suit, self.trump_rank)
            if not suit:
                if player_hand.has_suit(suit, self.trump_suit, self.trump_rank):
                    return "Play leading suit"
            else:
                lead_play = Play.decode(self.gameplayer_set.all()[self.turn].play)
                play = Play(play.cards, self.trump_suit, self.trump_rank)
                after_play = Play([card for card in player_hand.cards
                                   if card.get_suit(self.trump_suit, self.trump_rank) == suit], self.trump_suit, self.trump_rank)

                lead_rank = max(combination['rank'] for combination in lead_play.combinations)
                rank = max(combination['rank'] for combination in play.combinations)
                valid = True

                # Check which combinations are matched
                remove_lead = []
                for lead_combination in lead_play.combinations:
                    if lead_combination['consecutive'] >= 2:
                        remove = []
                        for combination in play.combinations:
                            if combination['consecutive'] >= 2 and lead_combination['n'] == combination['n']:
                                remove_lead.append(lead_combination)
                                remove.append(combination)
                                break
                        else:
                            valid = False

                        for r in remove:
                            play.combinations.remove(r)
                    else:
                        match = [combination for combination in play.combinations
                                 if lead_combination['n'] == combination['n']]
                        if match:
                            play.combinations.remove(match[0])
                            remove_lead.append(lead_combination)
                        else:
                            valid = False

                for r in remove_lead:
                    lead_play.combinations.remove(r)

                # Check cards that the player did not play that they should have
                for lead_combination in lead_play.combinations:
                    if lead_combination['consecutive'] >= 2:
                        if any(lead_combination['consecutive'] <= combination['consecutive'] and
                               lead_combination['n'] == combination['n']
                               for combination in after_play.combinations):
                            return "Consecutive pairs have to be played"

                    if any(lead_combination['n'] == combination['n'] for combination in after_play.combinations):
                        return "Pairs have to be played"

                if valid and rank > lead_rank:
                    self.lead = (self.turn + self.trick_turn) % self.number_of_players()
            play = Play(cards, self.trump_suit, self.trump_rank).encode()

        player.hand = str(player_hand)
        player.play = play.encode()
        player.save()

        self.trick_turn += 1
        self.trick_points += (5 * len([card for card in cards if card.rank == FIVE]) +
                              10 * len([card for card in cards if card.rank == TEN or card.rank == KING]))

        # Evaluate plays on last turn
        if self.trick_turn == self.number_of_players():
            lead = self.gameplayer_set.all()[self.lead]
            lead.points += self.trick_points
            lead.save()

            self.turn = self.lead
            self.trick_turn = 0
            self.trick_points = 0

            if len(player_hand) == 0:
                self.stage = Game.SCORE

        self.save()


class Player(models.Model):
    user = models.ForeignKey(User)
    rank = models.IntegerField(choices=RANK_CHOICES, default=TWO)

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
        if self.play:
            return Play.decode(self.play)
        else:
            return None


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
