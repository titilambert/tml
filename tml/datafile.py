# -*- coding: utf-8 -*-
"""
    Handles map loading and map saving.

    :copyright: 2010-2013 by the TML Team, see AUTHORS for more details.
    :license: GNU GPL, see LICENSE for more details.
"""

from struct import pack, unpack
from zlib import compress, decompress

from .constants import *
from . import items
from .utils import ints_to_string, string_to_ints

class Header(object):
    """Contains fileheader information.

    Please make sure the passed file is at the beginning.
    Note that the file won't be rewinded!

    :param f: The file with the information.
    """

    def __init__(self, f=None):
        self.version = 4
        self.size = 0
        if f != None:
            sig = b''.join(unpack('4c', f.read(4))).decode('ascii')
            if sig not in ('DATA', 'ATAD'):
                raise TypeError('Invalid signature')
            self.version, self.size_, self.swaplen, self.num_item_types, \
            self.num_items, self.num_raw_data, self.item_size, \
            self.data_size = unpack('8i', f.read(32))
            if self.version != 4:
                raise TypeError('Wrong version')

            # calculate the size of the whole header
            self.size = sum([
                36, # header data before the offsets
                self.num_item_types * 12,
                (self.num_items + (2 * self.num_raw_data)) * 4 # item offsets, data offsets, uncompressed data sizes
            ])

class DataFileReader(object):

    def __init__(self, map_path):
        # default list of item types
        for type_ in ITEM_TYPES:
            if type_ != 'version' and type_ != 'layer':
                setattr(self, ''.join([type_, 's']), [])

        path, filename = os.path.split(map_path)
        self.name, extension = os.path.splitext(filename)
        if extension == '':
            self.map_path = os.extsep.join([map_path, 'map'])
        elif extension != ''.join([os.extsep, 'map']):
            raise TypeError('Invalid file')
        else:
            self.map_path = map_path

        with open(self.map_path, 'rb') as f:
            self.f = f
            self.header = Header(f)
            self.item_types = []
            for i in range(self.header.num_item_types):
                val = unpack('3i', f.read(12))
                self.item_types.append({
                    'type': val[0],
                    'start': val[1],
                    'num': val[2],
                })
            fmt = '{0}i'.format(self.header.num_items)
            self.item_offsets = unpack(fmt, f.read(self.header.num_items * 4))
            fmt = '{0}i'.format(self.header.num_raw_data)
            self.data_offsets = unpack(fmt, f.read(self.header.num_raw_data * 4))

            # check version
            item_size, version_item = self.find_item(f, ITEM_VERSION, 0)
            fmt = '{0}i'.format(item_size//4)
            version = unpack(fmt, version_item)[0] # we only expect 1 element here
            if version != 1:
                raise ValueError('Wrong version')

            # load items
            # begin with map info
            item = self.find_item(f, ITEM_INFO, 0)
            if item is not None:
                item_size, item_data = item
                fmt = '{0}i'.format(item_size//4)
                item_data = unpack(fmt, item_data)
                version, author, map_version, credits, \
                license = item_data[:items.Info.type_size]
                if author > -1:
                    author = decompress(self.get_compressed_data(f, author))[:-1]
                else:
                    author = None
                if map_version > -1:
                    map_version = decompress(self.get_compressed_data(f, map_version))[:-1]
                else:
                    map_version = None
                if credits > -1:
                    credits = decompress(self.get_compressed_data(f, credits))[:-1]
                else:
                    credits = None
                if license > -1:
                    license = decompress(self.get_compressed_data(f, license))[:-1]
                else:
                    license = None
                if settings > -1:
                    settings = decompress(self.get_compressed_data(f, settings)).split(b'\x00')[:-1]
                else:
                    settings = None
                self.info = items.Info(author=author, map_version=map_version,
                                       credits=credits, license=license)
            else:
                self.info = None

            # load images
            start, num = self.get_item_type(ITEM_IMAGE)
            for i in range(num):
                item = self.get_item(f, start+i)
                item_size, item_data = item
                fmt = '{0}i'.format(item_size//4)
                item_data = unpack(fmt, item_data)
                version, width, height, external, image_name, \
                image_data = item_data[:items.Image.type_size]
                external = bool(external)
                try:
                    name = decompress(self.get_compressed_data(f, image_name))[:-1].decode('utf-8')
                except UnicodeDecodeError:
                    name = decompress(self.get_compressed_data(f, image_name))[:-1].decode('cp1252')
                data = decompress(self.get_compressed_data(f, image_data)) if not external else None
                image = items.Image(external=external, name=name,
                                   data=data, width=width, height=height)
                self.images.append(image)

            # load groups
            group_item_start, group_item_num = self.get_item_type(ITEM_GROUP)
            has_game_group = False
            for i in range(group_item_num):
                item_size, item_data = self.get_item(f, group_item_start+i)
                fmt = '{0}i'.format(item_size//4)
                item_data = unpack(fmt, item_data)
                version, offset_x, offset_y, parallax_x, parallax_y, \
                start_layer, num_layers, use_clipping, clip_x, clip_y, \
                clip_w, clip_h = item_data[:items.Group.type_size-3]
                if version >= 3:
                    data = item_data[items.Group.type_size-3:items.Group.type_size]
                    group_name = ints_to_string(data) or None
                else:
                    group_name = None
                start_layer, num_layers = item_data[5:7]

                is_game_group = False
                has_gamelayer = False
                has_telelayer = False
                has_speeduplayer = False
                has_frontlayer = False
                has_switchlayer = False
                has_tunelayer = False

                # load layers in group
                layer_item_start, layer_item_num = self.get_item_type(ITEM_LAYER)
                layers = []
                for j in range(num_layers):
                    item_size, item_data = self.get_item(f, layer_item_start+start_layer+j)
                    fmt = '{0}i'.format(item_size//4)
                    item_data = unpack(fmt, item_data)
                    layer_version, type_, flags = item_data[:items.Layer.type_size]
                    detail = True if flags else False

                    if type_ == LAYERTYPE_TILES:
                        type_size = items.TileLayer.type_size
                        color = 4*[0]
                        version, width, height, game, color[0], color[1], \
                        color[2], color[3], color_env, color_env_offset, \
                        image_id, data = item_data[3:type_size-3]
                        name = None
                        name = ints_to_string(item_data[type_size-3:type_size]) or None

                        if group_name == 'Game' or (game and not version >= 3):
                            if not is_game_group and has_game_group:
                                raise ValueError('Only one Game group allowed')
                            has_game_group = True
                            is_game_group = True

                        if game and not is_game_group:
                            raise ValueError('Gamelayers only allowed in Game group')

                        tile_list = []
                        if game == 8:
                            tile_data = decompress(self.get_compressed_data(f, item_data[type_size+2]))
                        else:
                            tile_data = decompress(self.get_compressed_data(f, data))
                        for i in range(0, len(tile_data), 4):
                            tile_list.append(tile_data[i:i+4])

                        tiles = items.TileManager(data=tile_list)
                        tele_tiles = None
                        speedup_tiles = None
                        switch_tiles = None
                        tune_tiles = None

                        if game == 2:
                            tele_list = []
                            if version >= 3:
                                # num of tele data is right after the default type length
                                if len(item_data) > items.TileLayer.type_size: # some security
                                    tele_data = item_data[items.TileLayer.type_size]
                                    if tele_data > -1 and tele_data < self.header.num_raw_data:
                                        tele_data = decompress(self.get_compressed_data(f, tele_data))
                                        if len(tele_data) // 2 != width * height:
                                            raise ValueError('Invalid tele data')
                                        for i in range(0, len(tele_data), 2):
                                            tele_list.append(tele_data[i:i+2])
                                        tele_tiles = items.TileManager(data=tele_list, _type=1)
                            else:
                                # num of tele data is right after num of data for old maps
                                if len(item_data) > items.TileLayer.type_size-3: # some security
                                    tele_data = item_data[items.TileLayer.type_size-3]
                                    if tele_data > -1 and tele_data < self.header.num_raw_data:
                                        tele_data = decompress(self.get_compressed_data(f, tele_data))
                                        if len(tele_data) // 2 != width * height:
                                            raise ValueError('Invalid tele data')
                                        for i in range(0, len(tele_data), 2):
                                            tele_list.append(tele_data[i:i+2])
                                        tele_tiles = items.TileManager(data=tele_list, _type=1)
                        elif game == 4:
                            speedup_list = []
                            if version >= 3:
                                # num of speedup data is right after tele data
                                if len(item_data) > items.TileLayer.type_size+1: # some security
                                    speedup_data = item_data[items.TileLayer.type_size+1]
                                    if speedup_data > -1 and speedup_data < self.header.num_raw_data:
                                        speedup_data = decompress(self.get_compressed_data(f, speedup_data))
                                        if len(speedup_data) // 6 != width * height:
                                            raise ValueError('Invalid speedup data')
                                        for i in range(0, len(speedup_data), 6):
                                            speedup_list.append(speedup_data[i:i+6])
                                        speedup_tiles = items.TileManager(data=speedup_list, _type=2)
                            else:
                                # num of speedup data is right after tele data
                                if len(item_data) > items.TileLayer.type_size-2: # some security
                                    speedup_data = item_data[items.TileLayer.type_size-2]
                                    if speedup_data > -1 and speedup_data < self.header.num_raw_data:
                                        speedup_data = decompress(self.get_compressed_data(f, speedup_data))
                                        if len(speedup_data) // 6 != width * height:
                                            raise ValueError('Invalid speedup data')
                                        for i in range(0, len(speedup_data), 6):
                                            speedup_list.append(speedup_data[i:i+6])
                                        speedup_tiles = items.TileManager(data=speedup_list, _type=2)
                        elif game == 16:
                            switch_list = []
                            if len(item_data) > type_size+3:
                                switch_data = item_data[type_size+3]
                                if switch_data > -1 and switch_data < self.header.num_raw_data:
                                    switch_data = decompress(self.get_compressed_data(f, switch_data))
                                    if len(switch_data) // 4 != width * height:
                                        raise ValueError('Invalid switch data')
                                    for i in range(0, len(switch_data), 4):
                                        switch_list.append(switch_data[i:i+4])
                                    switch_tiles = items.TileManager(data=switch_list, _type=3)
                        elif game == 32:
                            tune_list = []
                            if len(item_data) > type_size+4:
                                tune_data = item_data[type_size+4]
                                if tune_data > -1 and tune_data < self.header.num_raw_data:
                                    tune_data = decompress(self.get_compressed_data(f, tune_data))
                                    if len(tune_data) // 2 != width * height:
                                        raise ValueError('Invalid tune data')
                                    for i in range(0, len(tune_data), 2):
                                        tune_list.append(tune_data[i:i+2])
                                    tune_tiles = items.TileManager(data=tune_list, _type=4)

                        if game == 1:
                            if has_gamelayer:
                                raise ValueError('Only one Game layer allowed')
                            has_gamelayer = True
                        elif game == 2:
                            if not tele_tiles:
                                raise ValueError('Tele layer is missing tele data')
                            if has_telelayer:
                                raise ValueError('Only one Tele layer allowed')
                            has_telelayer = True
                        elif game == 4:
                            if not speedup_tiles:
                                raise ValueError('Speedup layer is missing speedup data')
                            if has_speeduplayer:
                                raise ValueError('Only one Speedup layer allowed')
                            has_speeduplayer = True
                        elif game == 8:
                            if has_frontlayer:
                                raise ValueError('Only one Front layer allowed')
                            has_frontlayer = True
                        elif game == 16:
                            if not switch_tiles:
                                raise ValueError('Switch layer is missing switch data')
                            if has_switchlayer:
                                raise ValueError('Only one Switch layer allowed')
                            has_switchlayer = True
                        elif game == 32:
                            if not tune_tiles:
                                raise ValueError('Tune layer is missing tune data')
                            if has_tunelayer:
                                raise ValueError('Only one Tune layer allowed')
                            has_tunelayer = True
                        else:
                            if game:
                                raise ValueError('Unknown Gamelayer id {}'.format(game))

                        layer = items.TileLayer(width=width, height=height,
                                                name=name, detail=detail, game=game,
                                                color=tuple(color), color_env=color_env,
                                                color_env_offset=color_env_offset,
                                                image_id=image_id, tiles=tiles,
                                                tele_tiles=tele_tiles,
                                                speedup_tiles=speedup_tiles,
                                                switch_tiles=switch_tiles,
                                                tune_tiles=tune_tiles)
                        layers.append(layer)
                    elif type_ == LAYERTYPE_QUADS:
                        type_size = items.QuadLayer.type_size
                        version, num_quads, data, image_id = item_data[3:type_size-3]
                        name = None
                        if version >= 2:
                            name = ints_to_string(item_data[type_size-3:type_size]) or None
                        quad_data = decompress(self.get_compressed_data(f, data))
                        quad_list = []
                        for k in range(0, len(quad_data), 152):
                            quad_list.append(quad_data[k:k+152])
                        quads = items.QuadManager(data=quad_list)
                        layer = items.QuadLayer(name=name, detail=detail,
                                                image_id=image_id, quads=quads)
                        layers.append(layer)
                    elif type_ == LAYERTYPE_SOUNDS:
                        type_size = 10
                        version, num_sources, data, sound = item_data[3:type_size-3]
                        if version != 2:
                            raise ValueError('Wrong version')
                        name = ints_to_string(item_data[type_size-3:type_size])
                        layer = items.SoundLayer(name=name, detail=detail,
                                                 num_sources=num_sources)
                        layers.append(layer)

                if is_game_group and not has_gamelayer:
                    raise ValueError('A Game layer is required')

                group = items.Group(name=group_name, offset_x=offset_x,
                                    offset_y=offset_y, parallax_x=parallax_x,
                                    parallax_y=parallax_y,
                                    use_clipping=use_clipping, clip_x=clip_x,
                                    clip_y=clip_y, clip_w=clip_w,
                                    clip_h=clip_h, layers=layers)
                self.groups.append(group)

            if not has_game_group:
                raise ValueError('A Game group is required')

            # load envpoints
            item_size, item = self.find_item(f, ITEM_ENVPOINT, 0)
            fmt = '{0}i'.format(item_size//4)
            item = unpack(fmt, item)
            type_size = items.Envpoint.type_size
            for i in range(len(item)//6):
                point = list(item[(i*6):(i*6+6)])
                time, curvetype = point[:type_size-4]
                values = point[type_size-4:type_size]
                envpoint = items.Envpoint(time=time, curvetype=curvetype,
                                          values=values)
                self.envpoints.append(envpoint)

            # load envelopes
            start, num = self.get_item_type(ITEM_ENVELOPE)
            type_size = items.Envelope.type_size
            for i in range(num):
                item_size, item_data = self.get_item(f, start+i)
                fmt = '{0}i'.format(item_size//4)
                item_data = unpack(fmt, item_data)
                version, channels, start_point, \
                num_point = item_data[:type_size-9]
                name = ints_to_string(item_data[type_size-9:type_size-1])
                envpoints = self.envpoints[start_point:start_point+num_point]
                synced = True if version < 2 or item_data[type_size-1] else False
                envelope = items.Envelope(name=name, version=version,
                                          channels=channels,
                                          envpoints=envpoints,
                                          synced=synced)
                self.envelopes.append(envelope)

    def get_item_type(self, item_type):
        """Returns the index of the first item and the number of items for the type."""
        for i in range(self.header.num_item_types):
            if self.item_types[i]['type'] == item_type:
                return (self.item_types[i]['start'], self.item_types[i]['num'])
        return (0, 0)

    def _get_item_size(self, index):
        """Returns the size of the item."""
        if index == self.header.num_items - 1:
            return (self.header.item_size - self.item_offsets[index]) - 8   # -8 to cut out type_and_id and size
        return (self.item_offsets[index+1] - self.item_offsets[index]) - 8

    def get_item(self, f, index):
        """Returns the item from the file."""
        if index < self.header.num_items:
            f.seek(self.header.size + self.item_offsets[index] + 8) # +8 to cut out type_and_id and size
            size = self._get_item_size(index)
            return (size, f.read(size))
        return None

    def find_item(self, f, item_type, index):
        """Finds the item and returns it from the file.

        :param f: Filepointer
        :param item_type:
        :param index:
        """
        start, num = self.get_item_type(item_type)
        if num and index < num:
            return self.get_item(f, start+index)
        return None

    def _get_compressed_data_size(self, index):
        """Returns the size of the compressed data part."""
        if index == self.header.num_raw_data - 1:
            return self.header.data_size - self.data_offsets[index]
        return self.data_offsets[index+1] - self.data_offsets[index]

    def get_compressed_data(self, f, index):
        """Returns the compressed data and size of it from the file."""
        size = self._get_compressed_data_size(index)
        f.seek(self.header.size + self.header.item_size + self.data_offsets[index])
        return f.read(size)

class DataFileWriter(object):

    class DataFileItem(object):

        def __init__(self, type_, id_, data):
            self.type = type_
            self.id = id_
            self.data = '{0}{1}'.format(pack('2i', (self.type<<16)|self.id, len(data)), data)
            self.size = len(self.data)

        def __lt__(self, other):
            if self.type < other.type:
                return True
            elif self.type == other.type and self.id < other.id:
                return True
            return False

        def __repr__(self):
            return '<DataFileItem ({0})>'.format((self.type<<16)|self.id)

    class DataFileData(object):

        def __init__(self, data):
            self.uncompressed_size = len(data)
            self.data = compress(data)
            self.compressed_size = len(self.data)

    def __init__(self, teemap, map_path):
        path, filename = os.path.split(map_path)
        name, extension = os.path.splitext(filename)
        if extension == '':
            map_path = os.extsep.join([map_path, 'map'])
        elif extension != ''.join([os.extsep, 'map']):
            raise ValueError('Invalid fileextension')
        teemap.validate()
        items_ = []
        datas = []
        # add version item
        items_.append(DataFileWriter.DataFileItem(ITEM_VERSION, 0, pack('i', 1)))
        # save map info
        if teemap.info:
            num = 5*[-1]
            for i, type_ in enumerate(['author', 'map_version', 'credits', 'license']):
                item_data = getattr(teemap.info, type_)
                if item_data:
                    num[i] = len(datas)
                    item_data += '\x00' # 0 termination
                    datas.append(DataFileWriter.DataFileData(item_data))
            items_.append(DataFileWriter.DataFileItem(ITEM_INFO, 0,
                              pack('6i', 1, *num)))
        # save images
        for i, image in enumerate(teemap.images):
            image_name = len(datas)
            name_str = '{0}\x00'.format(image.name)
            datas.append(DataFileWriter.DataFileData(name_str))
            image_data = -1
            if image.external is False and image.data:
                image_data = len(datas)
                datas.append(DataFileWriter.DataFileData(image.data))
            items_.append(DataFileWriter.DataFileItem(ITEM_IMAGE, i,
                              pack('6i', 1, image.width, image.height,
                              image.external, image_name, image_data)))
        # save layers and groups
        layer_count = 0
        for i, group in enumerate(teemap.groups):
            start_layer = layer_count
            for layer in group.layers:
                if layer.type == 'tilelayer':
                    tile_data = -1
                    tele_tile_data = -1
                    speedup_tile_data = -1
                    tiles_str = ''
                    name = string_to_ints(layer.name or 'Tiles', 3)
                    if layer.is_telelayer:
                        tile_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(len(layer.tele_tiles.tiles)*'\x00\x00\x00\x00'))
                        for tile in layer.tele_tiles.tiles:
                            tiles_str += tile
                        tele_tile_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(tiles_str))
                        name = string_to_ints('Tele', 3)
                    elif layer.is_speeduplayer:
                        tile_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(len(layer.speedup_tiles.tiles)*'\x00\x00\x00\x00'))
                        for tile in layer.speedup_tiles.tiles:
                            tiles_str += tile
                        speedup_tile_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(tiles_str))
                        name = string_to_ints('Speedup', 3)
                    else:
                        for tile in layer.tiles.tiles:
                            tiles_str += tile
                        tile_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(tiles_str))
                        if layer.is_gamelayer:
                            name = string_to_ints('Game', 3)
                    if teemap.telelayer or teemap.speeduplayer:
                        items_.append(DataFileWriter.DataFileItem(ITEM_LAYER, layer_count,
                               pack('20i', 0, LAYERTYPE_TILES, layer.detail, 3, layer.width,
                               layer.height, layer.game, layer.color[0], layer.color[1],
                               layer.color[2], layer.color[3], layer.color_env,
                               layer.color_env_offset, layer.image_id, tile_data, name[0],
                               name[1], name[2], tele_tile_data, speedup_tile_data)))
                    else:
                        items_.append(DataFileWriter.DataFileItem(ITEM_LAYER, layer_count,
                               pack('18i', 0, LAYERTYPE_TILES, layer.detail, 3, layer.width,
                               layer.height, layer.game, layer.color[0], layer.color[1],
                               layer.color[2], layer.color[3], layer.color_env,
                               layer.color_env_offset, layer.image_id, tile_data, *name)))
                    layer_count += 1
                elif layer.type == 'quadlayer':
                    if len(layer.quads.quads):
                        quads_str = ''
                        for quad in layer.quads.quads:
                            quads_str += quad
                        quad_data = len(datas)
                        datas.append(DataFileWriter.DataFileData(quads_str))
                        name = string_to_ints(layer.name, 3)
                        items_.append(DataFileWriter.DataFileItem(ITEM_LAYER, layer_count,
                               pack('10i', 7, LAYERTYPE_QUADS, layer.detail, 2,
                               len(layer.quads.quads), quad_data, layer.image_id, *name)))
                        layer_count += 1
            name = string_to_ints('Game' if group.is_gamegroup else group.name, 3)
            items_.append(DataFileWriter.DataFileItem(ITEM_GROUP, i,
                   pack('15i', 3, group.offset_x, group.offset_y, group.parallax_x,
                   group.parallax_y, start_layer, len(group.layers),
                   group.use_clipping, group.clip_x, group.clip_y, group.clip_w,
                   group.clip_h, *name)))

        # save envelopes
        start_point = 0
        for i, envelope in enumerate(teemap.envelopes):
            num_points = len(envelope.envpoints)
            name = string_to_ints(envelope.name)
            synced = 1 if envelope.synced else 0
            fmt = '{0}i'.format(items.Envelope.type_size)
            items_.append(DataFileWriter.DataFileItem(ITEM_ENVELOPE, i,
                   pack(fmt, 1, envelope.channels, start_point, num_points,
                   name[0], name[1], name[2], name[3], name[4], name[5], name[6], name[7],
                   synced)))
            start_point += num_points

        # save points
        envpoints = []
        for envpoint in teemap.envpoints:
            values = 4*[0]
            for i, value in enumerate(envpoint.values):
                values[i] = value
            envpoints.extend([envpoint.time, envpoint.curvetype, values[0],
                              values[1], values[2], values[3]])
        fmt = '{0}i'.format(len(envpoints))
        items_.append(DataFileWriter.DataFileItem(ITEM_ENVPOINT, 0,
               pack(fmt, *envpoints)))
        items_.sort()

        # calculate header
        item_size = 0
        num_item_types = 1
        item_types = []
        for i in range(len(items_)):
            item_size += items_[i].size
            if i > 0 and items_[i].type != items_[i-1].type:
                num_item_types += 1
        for i in range(7):
            num = 0
            start = -1
            for j, item in enumerate(items_):
                if item.type == i:
                    num += 1
                    if start < 0:
                        start = j
            if start > -1:
                item_types.extend([i, start, num])
        data_size = 0
        for data in datas:
            data_size += data.compressed_size
        item_types_size = num_item_types*12
        header_size = 36
        offset_size = (len(items_) + 2*len(datas)) * 4
        file_size = header_size + item_types_size + offset_size + item_size + data_size - 16
        swaplen = file_size - data_size

        # write file
        with open(map_path, 'wb') as f:
            f.write('DATA') # file signature
            header_str = pack('8i', 4, file_size, swaplen, num_item_types,
                          len(items_), len(datas), item_size, data_size)
            f.write(header_str)
            fmt = '{0}i'.format(len(item_types))
            item_types_str = pack(fmt, *item_types)
            f.write(item_types_str)
            item_offset_str = ''
            offset = 0
            for item in items_:
                item_offset_str += pack('i', offset)
                offset += item.size
            f.write(item_offset_str)
            data_offset_str = ''
            offset = 0
            for data in datas:
                data_offset_str += pack('i', offset)
                offset += data.compressed_size
            f.write(data_offset_str)
            for data in datas:
                f.write(pack('i', data.uncompressed_size))
            for item in items_:
                f.write(item.data)
            for data in datas:
                f.write(data.data)
