#!/usr/bin/env python
import os
import sys

from tml.tml import Teemap
from tml.items import TileLayer
from tml.constants import TML_DIR, TILEINDEX

MyIndex = {
    # Game & Front layer
    'begin': 33,
    'end': 34,
    'npc_end': 88,
    'super_end': 89,
    'jetpack_end': 90,
    'nph_end': 91,
    'npc_start': 104,
    'super_start': 105,
    'jetpack_start': 106,
    'nph_start': 107,
    # Tele layer
    'tele_in': 26,
    'tele_out': 27,
    'tele_in_evil': 10,
    'tele_in_weapon': 14,
    'tele_in_hook': 15,
    'jump': 7,
}

inTiles = ['tele_in', 'tele_in_evil', 'tele_in_weapon', 'tele_in_hook']

map_path = sys.argv[1]
t = Teemap(map_path)
pickups = {
    'begin': 0,
    'end': 0,
    'npc_end': 0,
    'super_end': 0,
    'jetpack_end': 0,
    'nph_end': 0,
    'npc_start': 0,
    'super_start': 0,
    'jetpack_start': 0,
    'nph_start': 0,
}

telePickups = {
    'tele_in': [],
    'tele_out': [],
    'tele_in_evil': [],
    'tele_in_weapon': [],
    'tele_in_hook': [],
    'jump': [],
}

for tile in t.gamelayer.tiles:
  for key, value in pickups.iteritems():
    if tile.index == MyIndex[key]:
      pickups[key] += 1

frontlayer = None

for group in t.groups:
  if group.name == 'Game':
    for layer in group.layers:
      if type(layer) == TileLayer and layer.name == 'Front':
        frontlayer = layer
        break

if frontlayer: # Works thanks to hack in tml
  for tile in frontlayer.tiles:
    for key, value in pickups.iteritems():
      if tile.index == MyIndex[key]:
        pickups[key] += 1

if t.telelayer:
  for tile in t.telelayer.tele_tiles:
    for key, value in telePickups.iteritems():
      if tile.type == MyIndex[key]:
        telePickups[key].append(tile.number)

if pickups['begin'] == 0:
  print 'Error: No Begin line'

if pickups['end'] == 0:
  print 'Error: No End line'

for i in telePickups['tele_out']:
  found = False
  for j in inTiles:
    if i in telePickups[j]:
      found = True
      break

  if not found:
    print 'Error: No tele-in for tele %d' % i

for j in inTiles:
  for i in telePickups[j]:
    if not i in telePickups['tele_out']:
      print 'Error: No tele-out for tele %d' % i

for k, v in pickups.iteritems():
  if v > 0:
    print '{value:3}x {key}'.format(value=v, key=k)

#for k, v in telePickups.iteritems():
#  print '{value:3}  {key}'.format(value=v, key=k)
