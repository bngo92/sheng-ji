from django.http import HttpResponse

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
                      {'games': Game.objects.filter(gameplayer__player__user=request.user)})

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            auth.login(request, form.cleaned_data['user'])
            return render(request, "home.html",
                          {'games': Game.objects.filter(gameplayer__player__user=request.user)})
    else:
        form = LoginForm()

    return render(request, "login.html", {'form': form})


@login_required(login_url=home)
def game(request, game_id):
    return render(request, "game.html", {'id': game_id})


def logout(request):
    auth.logout(request)
    return redirect(home)


@login_required(login_url=home)
def status(request, game_id):
    game = Game.objects.get(id=game_id)
    players = game.gameplayer_set.all()
    player = game.gameplayer_set.get(player__user=request.user)

    new_cards = []
    if game.stage == Game.DEAL:
        new_card = game.deal(player)
        if new_card:
            new_cards.append(new_card.repr())

    return HttpResponse(json.dumps({
        'stage': game.stage,
        'ready': player.ready,
        'turn': player.your_turn(),
        'reserve': game.stage == Game.DEAL and player.your_turn() and len(player.get_hand()) == game.hand_size(),
        'status': {
            'trump_rank': game.get_trump_rank_display(),
            'trump_suit': game.get_trump_suit_display(),
            'turn': next((player.__unicode__() for player in players if player.your_turn()), '')
        },
        'hand': {
            'player': player.__unicode__(),
            'str': ','.join(str(card) for card in sorted(player.get_hand().cards)),
            'cards': [card.repr() for card in sorted(player.get_hand().cards)],
            'new_cards': new_cards,
        },
        'players': [{'name': player.__unicode__(),
                     'cards': [card.repr() for card in player.get_play().cards]} for player in players]
    }), content_type='application/json')


@login_required(login_url=home)
def ready(request, game_id):
    game = Game.objects.get(id=game_id)
    player = game.gameplayer_set.get(player__user=request.user)

    if game.stage == Game.SETUP:
        game.ready(player)

    return HttpResponse()


@login_required(login_url=home)
def new_game(request):
    if request.method == "POST":
        players = [Player.objects.get(user__username=username) for username in request.POST.getlist('users')]
        game = Game.setup(players)
        if game:
            return redirect(game)
        else:
            error = 'Only 4-8 players are allowed'
    else:
        error = None
    return render(request, "new_game.html", {'users': User.objects.all(), 'error': error})


@login_required(login_url=home)
def play(request, game_id):
    game = Game.objects.get(id=game_id)
    player = game.gameplayer_set.get(player__user=request.user)
    if request.method == "POST":
        cards = Hand.fromstr(request.POST['data']).cards
        if game.stage == Game.DEAL:
            game.set_trump_suit(player, cards)
        if game.stage == Game.RESERVE:
            game.reserve(player, cards)
        if game.stage == Game.PLAY:
            game.play(player, cards)
    return HttpResponse()


@login_required(login_url=home)
def reserve(request, game_id):
    if request.method == "POST":
        game = Game.objects.get(id=game_id)
        players = game.gameplayer_set.all()
        player = game.gameplayer_set.get(player__user=request.user)
        if game.stage == Game.DEAL and player.your_turn() and len(player.get_hand()):
            reserve = Hand.fromstr(game.deck)
            game.deck = ''
            game.stage = Game.RESERVE
            game.save()

            player_hand = player.get_hand()
            player_hand.add_cards(reserve.cards)
            player.hand = str(player_hand)
            player.save()

            for player in players:
                player.play = ''
                player.save()
    return HttpResponse()
