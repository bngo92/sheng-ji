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
        players = [Player.objects.get(user__username=username) for username in request.POST.getlist('users')]
        if not Game.setup(players):
            error = 'Only 4-8 players are allowed'
        else:
            return redirect(home)
    else:
        error = None
    return render(request, "new_game.html",  {'users': User.objects.all(), 'error': error})


@login_required(login_url=home)
def draw(request):
    if request.method == "POST":
        if 'trump' in request.POST:
            game_id = request.POST['trump']
            game = Game.objects.get(id=game_id)
            player = GamePlayer(game=game, player__user=request.user)
            if game.stage != Game.SCORE and game.deck and 'on' in request.POST:
                cards = [k for k, v in request.POST if v == 'on']
                if any(card.rank != game.dominant_rank for card in cards):
                    error = 'Non-trump rank played'
                else:
                    pass  # TODO

        elif 'game_id' in request.POST:
            game_id = request.POST['game_id']
            game = Game.objects.get(id=game_id)
            player = GamePlayer(game=game, player__user=request.user)
            if game.stage != Game.SCORE and player.your_turn():
                game.deal(player)
    return redirect(home)
