#!/usr/bin/env python2
import os
import sys
import msgpack

from tml.tml import Teemap
from tml.items import TileLayer
from tml.constants import TML_DIR, TILEINDEX

ENTITY_OFFSET=255-16*4
ENTITY_NULL=0
ENTITY_SPAWN=1
ENTITY_SPAWN_RED=2
ENTITY_SPAWN_BLUE=3
ENTITY_FLAGSTAND_RED=4
ENTITY_FLAGSTAND_BLUE=5
ENTITY_ARMOR_1=6
ENTITY_HEALTH_1=7
ENTITY_WEAPON_SHOTGUN=8
ENTITY_WEAPON_GRENADE=9
ENTITY_POWERUP_NINJA=10
ENTITY_WEAPON_RIFLE=11
ENTITY_LASER_FAST_CW=12
ENTITY_LASER_NORMAL_CW=13
ENTITY_LASER_SLOW_CW=14
ENTITY_LASER_STOP=15
ENTITY_LASER_SLOW_CCW=16
ENTITY_LASER_NORMAL_CCW=17
ENTITY_LASER_FAST_CCW=18
ENTITY_LASER_SHORT=19
ENTITY_LASER_MEDIUM=20
ENTITY_LASER_LONG=21
ENTITY_LASER_C_SLOW=22
ENTITY_LASER_C_NORMAL=23
ENTITY_LASER_C_FAST=24
ENTITY_LASER_O_SLOW=25
ENTITY_LASER_O_NORMAL=26
ENTITY_LASER_O_FAST=27
ENTITY_PLASMAE=29
ENTITY_PLASMAF=30
ENTITY_PLASMA=31
ENTITY_PLASMAU=32
ENTITY_CRAZY_SHOTGUN_EX=33
ENTITY_CRAZY_SHOTGUN=34
ENTITY_DRAGGER_WEAK=42
ENTITY_DRAGGER_NORMAL=43
ENTITY_DRAGGER_STRONG=44
ENTITY_DRAGGER_WEAK_NW=45
ENTITY_DRAGGER_NORMAL_NW=46
ENTITY_DRAGGER_STRONG_NW=47
ENTITY_DOOR=49
NUM_ENTITIES=50

TILE_AIR=0
TILE_SOLID=1
TILE_DEATH=2
TILE_NOHOOK=3
TILE_NOLASER=4
TILE_THROUGH_CUT=5
TILE_THROUGH=6
TILE_JUMP=7
TILE_FREEZE = 9
TILE_TELEINEVIL=10
TILE_UNFREEZE=11
TILE_DFREEZE=12
TILE_DUNFREEZE=13
TILE_TELEINWEAPON=14
TILE_TELEINHOOK=15
TILE_WALLJUMP = 16
TILE_EHOOK_START=17
TILE_EHOOK_END=18
TILE_HIT_START=19
TILE_HIT_END=20
TILE_SOLO_START=21
TILE_SOLO_END=22
TILE_SWITCHTIMEDOPEN = 22
TILE_SWITCHTIMEDCLOSE=23
TILE_SWITCHOPEN=24
TILE_SWITCHCLOSE=25
TILE_TELEIN=26
TILE_TELEOUT=27
TILE_BOOST=28
TILE_TELECHECK=29
TILE_TELECHECKOUT=30
TILE_TELECHECKIN=31
TILE_REFILL_JUMPS = 32
TILE_BEGIN=33
TILE_END=34
TILE_STOP = 60
TILE_STOPS=61
TILE_STOPA=62
TILE_TELECHECKINEVIL=63
TILE_CP=64
TILE_CP_F=65
TILE_THROUGH_ALL=66
TILE_THROUGH_DIR=67
TILE_TUNE1=68
TILE_OLDLASER = 71
TILE_NPC=72
TILE_EHOOK=73
TILE_NOHIT=74
TILE_NPH=75
TILE_UNLOCK_TEAM=76
TILE_PENALTY = 79
TILE_NPC_END = 88
TILE_SUPER_END=89
TILE_JETPACK_END=90
TILE_NPH_END=91
TILE_BONUS = 95
TILE_NPC_START = 104
TILE_SUPER_START=105
TILE_JETPACK_START=106
TILE_NPH_START=107
TILE_ENTITIES_OFF_1 = 190
TILE_ENTITIES_OFF_2=191

def IsValidGameTile(Index):
    return (
            Index == TILE_AIR
        or (Index >= TILE_SOLID and Index <= TILE_NOLASER)
        or  Index == TILE_THROUGH
        or  Index == TILE_FREEZE
        or (Index >= TILE_UNFREEZE and Index <= TILE_DUNFREEZE)
        or (Index >= TILE_WALLJUMP and Index <= TILE_SOLO_END)
        or (Index >= TILE_REFILL_JUMPS and Index <= TILE_STOPA)
        or (Index >= TILE_CP and Index <= TILE_THROUGH_DIR)
        or (Index >= TILE_OLDLASER and Index <= TILE_UNLOCK_TEAM)
        or (Index >= TILE_NPC_END and Index <= TILE_NPH_END)
        or (Index >= TILE_NPC_START and Index <= TILE_NPH_START)
        or (Index >= TILE_ENTITIES_OFF_1 and Index <= TILE_ENTITIES_OFF_2)
        or  IsValidEntity(Index)
    );

def IsValidFrontTile(Index):
    return (
                    Index == TILE_AIR
                or  Index == TILE_DEATH
                or (Index >= TILE_NOLASER and Index <= TILE_THROUGH)
                or  Index == TILE_FREEZE
                or (Index >= TILE_UNFREEZE and Index <= TILE_DUNFREEZE)
                or (Index >= TILE_WALLJUMP and Index <= TILE_SOLO_END)
                or (Index >= TILE_REFILL_JUMPS and Index <= TILE_STOPA)
                or (Index >= TILE_CP and Index <= TILE_THROUGH_DIR)
                or (Index >= TILE_OLDLASER and Index <= TILE_UNLOCK_TEAM)
                or (Index >= TILE_NPC_END and Index <= TILE_NPH_END)
                or (Index >= TILE_NPC_START and Index <= TILE_NPH_START)
                or  IsValidEntity(Index)
        );

def IsValidEntity(Index):
    Index -= ENTITY_OFFSET
    return (
                   (Index >= ENTITY_SPAWN and Index <= ENTITY_LASER_O_FAST)
                or (Index >= ENTITY_PLASMAE and Index <= ENTITY_CRAZY_SHOTGUN)
                or (Index >= ENTITY_DRAGGER_WEAK and Index <= ENTITY_DRAGGER_STRONG_NW)
                or  Index == ENTITY_DOOR
        );

def main(argv):
  map_path = argv[1]
  t = Teemap(map_path)

  frontlayer = None # Works thanks to hack in tml
  for group in t.groups:
    if group.name == 'Game':
      for layer in group.layers:
        if type(layer) == TileLayer and layer.name == 'Front':
          frontlayer = layer
          break

  for tile in t.gamelayer.tiles:
    if not IsValidGameTile(tile.index):
      print(map_path)
      return

  if frontlayer != None:
      for tile in frontlayer.tiles:
        if not IsValidFrontTile(tile.index):
          print(map_path)
          return

if __name__ == "__main__":
  main(sys.argv)
