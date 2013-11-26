import random

from django.shortcuts import render as django_render, redirect
from django.contrib import auth
from django.contrib.auth.decorators import login_required

from models import *


def render(request, template_name, additional=None):
    if additional is None:
        additional = {}
    if request.user.is_authenticated():
        additional.update({'username': request.user.get_username()})
    return django_render(request, template_name, additional)


def home(request):
    if request.user.is_authenticated():
        return render(request, "home.html",
                      {'games': request.user.player_set.filter(game__active=True)})
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            auth.login(request, form.cleaned_data['user'])
            return render(request, "home.html",
                          {'games': request.user.player_set.filter(game__active=True)})
    else:
        form = LoginForm()
    return render(request, "home_login.html", {'form': form})


def register(request):
    return


def logout(request):
    auth.logout(request)
    return redirect(home)


@login_required(login_url=home)
def new_game(request):
    if request.method == "POST":
        users = [User.objects.get(username=username) for username in request.POST.getlist('users')]
        if len(users) == 4:
            game = Game.objects.create(victory_score=request.POST.get('rank'))
            for i, player in enumerate(users):
                Player.objects.create(user=player, game=game, turn=i, team=(TEAM_CHOICES[i % 2])[0])
            game.reserve_size = 8

            deck_list = [Card(suit+rank) for suit, _ in SUITS for rank, _ in RANKS] + [Card('BJ')] + [Card('RJ')]
            random.shuffle(deck_list)
            game.deck = ','.join(str(card) for card in deck_list)
            game.save()

            return redirect(home)
        error = 'Not enough users'
    else:
        error = None
    return render(request, "new_game.html", {'users': User.objects.all(), 'ranks': [rank for rank, _ in RANKS], 'error': error})


@login_required(login_url=home)
def draw(request):
    if request.method == "POST":
        if 'trump' in request.POST:
            game_id = request.POST['trump']
            game = Game.objects.get(id=game_id)
            player = request.user.player_set.get(game=game)
            if game.active and game.deck and 'on' in request.POST:
                cards = [k for k, v in request.POST if v == 'on' and Card(k).rank == game.trump_rank()]
        elif 'game_id' in request.POST:
            game_id = request.POST['game_id']
            game = Game.objects.get(id=game_id)
            player = request.user.player_set.get(game=game)
            if game.active and game.deck and player.your_turn():
                deck_list = game.deck.split(',')
                if len(deck_list) > Game.RESERVE_SIZE:
                    player = game.player_set.get(game=game, turn=game.turn % game.player_set.count())
                    if player.hand:
                        player.hand += ',{}'.format(deck_list.pop())
                    else:
                        player.hand = deck_list.pop()
                    player.save()
                    game.deck = ','.join(deck_list)
                    game.turn += 1
                if len(deck_list) == Game.RESERVE_SIZE:
                    game.reserve = game.deck
                    game.deck = ''
                game.save()
    return redirect(home)
