from collections import Counter, deque
from functools import total_ordering
import itertools
import json
import logging
import random

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
JOKER = 'J'
TRUMP = 'TRUMP'
SUITS = NORMAL_SUITS + (JOKER,)
SUIT_CHOICES = (
    (CLUBS, 'Clubs'),
    (DIAMONDS, 'Diamonds'),
    (HEARTS, 'Hearts'),
    (SPADES, 'Spades'),
    # jokers
    (JOKER, 'Joker'),
)

TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE, OFFSUIT_TRUMP, ONSUIT_TRUMP, BLACK, RED = range(2, 2 + 17)
NORMAL_RANKS = (TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE)
RANKS = NORMAL_RANKS + (OFFSUIT_TRUMP, ONSUIT_TRUMP, BLACK, RED)
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
    (BLACK, 'Black'),
    (RED, 'Red'),
)


logger = logging.getLogger(__name__)


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
        return self.suit in (trump_suit, JOKER) or self.rank == trump_rank

    def get_suit(self, trump_suit, trump_rank):
        if self.is_trump(trump_suit, trump_rank):
            return TRUMP
        else:
            return self.suit

    def get_rank(self, trump_suit, trump_rank):
        if self.rank == trump_rank:
            if self.suit == trump_suit:
                return ONSUIT_TRUMP
            else:
                return OFFSUIT_TRUMP
        else:
            return self.rank


def create_deck():
    return ([Card(suit, rank) for suit in NORMAL_SUITS for rank in NORMAL_RANKS] +
            [Card(JOKER, rank) for rank in (BLACK, RED)])


def is_consecutive(cards, trump_suit, trump_rank):
    if len(cards) < 2:
        return False

    ranks = [card.get_rank(trump_suit, trump_rank) for card in cards]
    min_rank = min(ranks)
    max_rank = max(ranks)
    return (sorted(ranks + [trump_rank]) == range(min_rank, max_rank + 1) if min_rank < trump_rank < max_rank else
            sorted(ranks) == range(min_rank, max_rank + 1))


class Cards(object):
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


@total_ordering
class CardCombinations(object):
    def __init__(self, cards=None, trump_suit=None, trump_rank=None, consecutive=True):
        self.cards = []
        self.suit = None
        self.rank = None
        self.combinations = []
        self.can_win = True
        if cards:
            self.init(cards, trump_suit, trump_rank, consecutive)

    def __eq__(self, other):
        return (self.suit, self.rank) == (other.suit, other.rank)

    def __lt__(self, other):
        if self.suit != TRUMP and other.suit == TRUMP:
            return True
        if self.suit == TRUMP and other.suit != TRUMP:
            return False
        return self.rank < other.rank

    def init(self, cards, trump_suit, trump_rank, consecutive=True):
        self.cards = str(Cards(cards))
        self.suit = cards[0].get_suit(trump_suit, trump_rank)
        self.rank = max(card.get_rank(trump_suit, trump_rank) for card in cards)
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

    def validate(self, before, after):
        # Check which combinations are matched with hand
        for first_player_combination in self.combinations:
            remove = []
            if first_player_combination['consecutive'] >= 2:
                match = [combination for combination in before.combinations
                         if combination['consecutive'] >= 2 and
                         first_player_combination['n'] == combination['n']][:1]
                if match:
                    first_player_combination['match'] = True
                    remove.extend(match)

                else:
                    self.can_win = False
                    match = [combination for combination in before.combinations
                             if first_player_combination['n'] == combination['n']][:first_player_combination['consecutive']]
                    if match:
                        first_player_combination['match'] = len(match)
                        remove.extend(match)

            else:
                match = [combination for combination in before.combinations
                         if first_player_combination['n'] == combination['n']][:1]
                if match:
                    first_player_combination['match'] = True
                    remove.extend(match)
                else:
                    self.can_win = False

            for r in remove:
                before.combinations.remove(r)

        # Check which combinations are matched with cards played
        for first_player_combination in self.combinations:
            if 'match' not in first_player_combination:
                continue

            remove = []
            if first_player_combination['consecutive'] >= 2:
                if first_player_combination['match'] is True:
                    match = [combination for combination in after.combinations
                             if combination['consecutive'] >= 2 and
                             first_player_combination['n'] == combination['n']][:1]
                    if match:
                        remove.extend(match)
                    else:
                        return "Consecutive pairs have to be played"

                else:
                    match = [combination for combination in after.combinations
                             if first_player_combination['n'] == combination['n']][:first_player_combination['consecutive']]
                    if len(match) >= first_player_combination['match']:
                        remove.extend(match)
                    else:
                        return "Pairs have to be played"

            else:
                match = [combination for combination in after.combinations
                         if first_player_combination['n'] == combination['n']][:1]
                if match:
                    first_player_combination['match'] = True
                    remove.extend(match)
                else:
                    return "Pairs have to be played"

            for r in remove:
                after.combinations.remove(r)

    def encode(self):
        return json.dumps({'suit': self.suit, 'rank': self.rank, 'combinations': self.combinations, 'cards': self.cards})

    @classmethod
    def decode(cls, s):
        play_dict = json.loads(s)
        play = cls()
        play.suit = play_dict['suit']
        play.rank = play_dict['rank']
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
    lead = models.IntegerField(default=0)
    winner = models.CharField(max_length=1, choices=TEAM_CHOICES, default=DECLARERS)

    # Cards
    deck = models.CharField(max_length=1000)
    kitty = models.CharField(max_length=100)

    # Trump details
    trump_rank = models.IntegerField(choices=RANK_CHOICES)
    def get_trump_rank_display(self): return dict(RANK_CHOICES)[self.trump_rank]
    trump_suit = models.CharField(max_length=1, choices=SUIT_CHOICES)
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
    def setup(cls, players, shuffle=False):
        if shuffle:
            random.shuffle(players)

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

        for turn, player in enumerate(players):
            if turn % 2 == 0:
                team = DECLARERS
            else:
                team = OPPONENTS
            GamePlayer.objects.create(game=game, player=player, team=team, turn=turn)

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

        player_hand = Cards.fromstr(player.hand)
        if len(player_hand) >= self.hand_size():
            return False

        deck = Cards.fromstr(self.deck)
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

        player_hand = Cards.fromstr(player.hand)
        if not cards in player_hand:
            return False

        if len(cards) > self.trump_count:
            self.trump_count = len(cards)
            self.trump_suit = cards[0].suit
            self.save()

            play = CardCombinations(cards, self.trump_suit, self.trump_rank)
            player.play = play.encode()
            player.save()
        else:
            return "Not enough cards to change trump suit"

    def pickup_reserve(self, player):
        if self.stage != Game.DEAL or player.turn != 0 or len(player.get_hand()) != self.hand_size():
            return False

        reserve = Cards.fromstr(self.deck)
        if not self.trump_suit:
            self.trump_suit = reserve.cards[0].suit
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

        player_hand = Cards.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if len(cards) != self.reserve_size():
            return "Incorrect number of cards were played"

        player_hand.play_cards(cards)
        player.hand = str(player_hand)
        player.save()

        kitty = Cards(cards)
        self.kitty = str(kitty)
        self.stage = Game.PLAY
        self.turn = 0
        self.trick_turn = 0
        self.save()

    def play(self, player, cards):
        if self.stage != Game.PLAY or not player.your_turn():
            return False

        player_hand = Cards.fromstr(player.hand)
        if cards not in player_hand:
            return False

        if self.trick_turn == 0:
            for other in self.gameplayer_set.all():
                other.play = ''
                other.save()

            # First player has to play a single suit
            cards_played = Cards(cards)
            cards_played_suit = cards_played.single_suit(self.trump_suit, self.trump_rank)
            if cards_played_suit is None:
                return "Cards have to be a single suit"
            if cards_played_suit == TRUMP and not self.trump_broken:
                if set(card.get_suit(self.trump_suit, self.trump_rank) for card in cards) != set(TRUMP):
                    return "Trump hasn't been broken yet"
                else:
                    self.trump_broken = True

            # If combination is played, remove cards that aren't highest
            play = CardCombinations(cards_played.cards, self.trump_suit, self.trump_rank)
            if len(play.combinations) > 1:
                for other in self.gameplayer_set.all():
                    if player == other:
                        continue

                    other_hand = [card for card in Cards.fromstr(other.hand).cards
                                  if card.get_suit(self.trump_suit, self.trump_rank) == cards_played_suit]
                    other_play = CardCombinations(other_hand, self.trump_suit, self.trump_rank, False)

                    not_highest = []
                    for combination in play.combinations:
                        if combination['consecutive'] >= 2:
                            continue

                        for other_combination in other_play.combinations:
                            if (combination['n'] <= other_combination['n'] and
                                    combination['rank'] < other_combination['rank']):
                                not_highest.append(combination)

                    if not_highest:
                        cards = Cards()
                        for combination in play.combinations:
                            if combination['consecutive'] < 2:
                                continue

                            for rank in range(combination['rank'], combination['rank'] - combination['consecutive'], -1):
                                cards.add_cards(Card(play.suit, rank) for _ in range(combination['n']))

                        lowest = min(not_highest, key=lambda c: c['rank'])
                        cards.add_cards(Card(play.suit, lowest['rank']) for _ in range(lowest['n']))
                        cards = cards.cards
                        break

        else:
            # Other players have to play the same number of cards that the first person played
            first_player_combinations = CardCombinations.decode(self.gameplayer_set.all()[self.turn].play)
            first_player_cards = Cards.fromstr(first_player_combinations.cards).cards
            if len(first_player_cards) != len(cards):
                return "Play same amount of cards"

            # Other players have to play the suit that the first person played
            cards_played_suit = Cards(cards).single_suit(self.trump_suit, self.trump_rank)
            hand_after_play = Cards(player_hand.cards)
            hand_after_play.play_cards(cards)

            if ((not cards_played_suit or cards_played_suit != first_player_combinations.suit) and
                    hand_after_play.has_suit(first_player_combinations.suit, self.trump_suit, self.trump_rank)):
                return "Play leading suit"

            if cards_played_suit in (first_player_combinations.suit, TRUMP):
                if cards_played_suit == TRUMP:
                    self.trump_broken = True

                first_player_combinations = CardCombinations(first_player_cards,
                                                             self.trump_suit, self.trump_rank)
                combinations_before_play = CardCombinations(
                    [card for card in player_hand.cards
                     if card.get_suit(self.trump_suit, self.trump_rank) == cards_played_suit],
                    self.trump_suit, self.trump_rank)
                combinations_played = CardCombinations(cards, self.trump_suit, self.trump_rank)
                ret = first_player_combinations.validate(combinations_before_play, combinations_played)
                if ret:
                    return ret

                lead_play = CardCombinations.decode(self.gameplayer_set.all()[self.lead].play)
                logger.debug("first: %s, lead: %s, play: %s",
                             first_player_combinations.encode(), lead_play.encode(),
                             CardCombinations(cards, self.trump_suit, self.trump_rank).encode())
                logger.debug("can win: %s, win: %s", first_player_combinations.can_win, combinations_played > lead_play)
                if first_player_combinations.can_win and combinations_played > lead_play:
                    self.lead = (self.turn + self.trick_turn) % self.number_of_players()

        player_hand.play_cards(cards)
        player.hand = str(player_hand)
        play = CardCombinations(cards, self.trump_suit, self.trump_rank).encode()
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
                lead = self.gameplayer_set.all()[self.lead]
                if lead.team == OPPONENTS:
                    cards = Cards.fromstr(self.kitty).cards
                    lead.points += 2 * (5 * len([card for card in cards if card.rank == FIVE]) +
                                        10 * len([card for card in cards if card.rank == TEN or card.rank == KING]))
                    lead.save()

                opponent_points = sum(player.points for player in self.gameplayer_set.filter(team=OPPONENTS))
                if opponent_points >= 80:
                    players = self.gameplayer_set.filter(team=OPPONENTS)
                    if opponent_points >= 160:
                        delta = 3
                    elif opponent_points >= 120:
                        delta = 2
                    else:
                        delta = 1
                    for player in players:
                        player.player.add_rank(delta)
                    for player in self.gameplayer_set.filter(team=DECLARERS):
                        player.player.plus = False
                        player.player.save()
                    self.winner = OPPONENTS
                else:
                    players = self.gameplayer_set.filter(team=DECLARERS)
                    if opponent_points >= 40:
                        delta = 1
                    elif opponent_points >= 0:
                        delta = 2
                    else:
                        delta = 3
                    for player in players:
                        player.player.add_rank(delta)
                    for player in self.gameplayer_set.filter(team=OPPONENTS):
                        player.player.plus = False
                        player.player.save()

        self.save()

    def rematch(self):
        if self.stage != Game.SCORE:
            return False

        players = deque(self.gameplayer_set.all())
        players.rotate(-1)
        while players[0].team != self.winner:
            players.rotate(-1)
        return Game.setup(players)


class Player(models.Model):
    user = models.ForeignKey(User)
    rank = models.IntegerField(choices=RANK_CHOICES, default=TWO)
    plus = models.BooleanField(default=False)

    def __unicode__(self):
        return self.user.__unicode__()

    def get_rank(self):
        return '{}{}'.format(self.rank, '+' if self.plus else '-')

    @classmethod
    def create_player(cls, username, password):
        player = cls()
        try:
            player.user = User.objects.create_user(username, password=password)
            player.save()
            return player
        except IntegrityError:
            return None

    def add_rank(self, delta):
        if not self.plus:
            self.plus = True
            delta -= 1
        self.rank += delta
        self.save()


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
        return Cards.fromstr(self.hand)

    def your_turn(self):
        return (self.game.turn + self.game.trick_turn) % self.game.number_of_players() == self.turn

    def get_play(self):
        if self.play:
            return CardCombinations.decode(self.play)
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
