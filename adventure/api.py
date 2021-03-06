# This is the gameplay api stuff
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from pusher import Pusher
from django.http import JsonResponse
from decouple import config
from django.contrib.auth.models import User
from .models import *
from rest_framework.decorators import api_view
import json

# instantiate pusher
pusher = Pusher(app_id=config('PUSHER_APP_ID'), key=config('PUSHER_KEY'), secret=config('PUSHER_SECRET'), cluster=config('PUSHER_CLUSTER'))

# for that intial return and inserting into world
@csrf_exempt
@api_view(["GET"])
def initialize(request):
    user = request.user
    player = user.player
    player_id = player.id
    uuid = player.uuid
    room = player.room()
    currentPlayerUUIDs = room.playerUUIDs(player.id)
    players = room.playerNames(player_id)
    for p_uuid in currentPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has appeared from the ether.'})
    return JsonResponse({'uuid': uuid, 'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players}, safe=True)

# this is all the movement stuff
# @csrf_exempt
@api_view(["POST"])
def move(request):
    dirs={"n": "north", "s": "south", "e": "east", "w": "west"}
    reverse_dirs = {"n": "south", "s": "north", "e": "west", "w": "east"}
    player = request.user.player
    player_id = player.id
    player_uuid = player.uuid
    data = json.loads(request.body)
    direction = data['direction']
    room = player.room()
    nextRoomID = None
    if direction == "n":
        nextRoomID = room.n_to
    elif direction == "s":
        nextRoomID = room.s_to
    elif direction == "e":
        nextRoomID = room.e_to
    elif direction == "w":
        nextRoomID = room.w_to
    if nextRoomID is not None and nextRoomID > 0:
        nextRoom = Room.objects.get(id=nextRoomID)
        player.currentRoom=nextRoomID
        player.save()
        players = nextRoom.playerNames(player_id)
        currentPlayerUUIDs = room.playerUUIDs(player_id)
        nextPlayerUUIDs = nextRoom.playerUUIDs(player_id)
        for p_uuid in currentPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has walked {dirs[direction]}.'})
        for p_uuid in nextPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has entered from the {reverse_dirs[direction]}.'})
        return JsonResponse({'name':player.user.username, 'title':nextRoom.title, 'description':nextRoom.description, 'players':players, 'error_msg':""}, safe=True)
    else:
        players = room.playerNames(player_uuid)
        return JsonResponse({'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players, 'error_msg':"You cannot move that way."}, safe=True)

# the say command
@csrf_exempt
@api_view(["POST"])
def say(request):
    player = request.user.player
    room = player.room()
    currentPlayerUUIDs = room.playerUUIDs(player.id)
    data = json.loads(request.body)
    message = data['message']
    for p_uuid in currentPlayerUUIDs:
        pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has said "{message}".'})
    return JsonResponse({'message':f'You have said "{message}"'}, safe=True)

# the shout command
@csrf_exempt
@api_view(["POST"])
def shout(request):
    player = request.user.player
    currentPlayer = Player.objects.all()
    data = json.loads(request.body)
    message = data['message']
    for otherplayer in currentPlayer:
        if player.uuid != otherplayer.uuid:
            pusher.trigger(f'p-channel-{otherplayer.uuid}', u'broadcast', {'message':f'{player.user.username} has shouted "{message}".'})
    return JsonResponse({'message':f'You have shouted "{message}"'}, safe=True)

# the shout command
@csrf_exempt
@api_view(["POST"])
def whisper(request):
    player = request.user.player
    data = json.loads(request.body)
    message = data['message']
    if 'player' not in data:
        return JsonResponse({"error":"No player name provided"}, safe=True, status=500)
    targetplayer = data['player']

    currentPlayer = User.objects.filter(username = targetplayer)
    print(currentPlayer)
    if len(currentPlayer) == 0: 
         return JsonResponse({"error":"No player found by that name"}, safe=True, status=500)
    pusher.trigger(f'p-channel-{currentPlayer[0].player.uuid}', u'broadcast', {'message':f'{player.user.username} has whispered "{message}".'})
   
    return JsonResponse({'message':f'You have whispered "{message}" to {currentPlayer[0].player.user.username}'}, safe=True)