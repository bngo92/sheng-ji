from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import models

TEAM_CHOICES = (
    ('A', 'A'),
    ('B', 'B'),
)
SUITS = (
    ('C', 'C'),
    ('D', 'D'),
    ('H', 'H'),
    ('S', 'S'),
)
RANKS = (
    ('A', 'A'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
    ('10', '10'),
    ('J', 'J'),
    ('Q', 'Q'),
    ('K', 'K'),
)


class Card(object):

    def __init__(self, s):
        self.suit = s[0]
        self.rank = s[1:]

    def __str__(self):
        return self.suit + self.rank


class Game(models.Model):
    RESERVE_SIZE = 8

    active = models.BooleanField(default=True)
    round = models.IntegerField(default=0)
    victory_score = models.CharField(max_length=2, choices=RANKS)
    scoring_team = models.CharField(max_length=1, choices=TEAM_CHOICES)
    score_a = models.CharField(max_length=2, choices=RANKS, default='2')
    score_b = models.CharField(max_length=2, choices=RANKS, default='2')
    turn = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    deck = models.CharField(max_length=1000)
    reserve = models.CharField(max_length=100)
    trump_suit = models.CharField(max_length=1, choices=SUITS)
    trump_count = models.IntegerField(default=0)

    def trump_rank(self):
        pass


class Player(models.Model):
    user = models.ForeignKey(User)
    game = models.ForeignKey(Game)
    hand = models.CharField(max_length=200)
    team = models.CharField(max_length=1, choices=TEAM_CHOICES)
    turn = models.IntegerField()

    def __unicode__(self):
        return self.user.__unicode__()

    def get_hand(self):
        return self.hand.split(',')

    def your_turn(self):
        return self.game.turn % self.game.player_set.count() == self.turn


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
