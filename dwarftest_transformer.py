#!/usr/bin/env python3
# encoding: utf-8

import os
import logging
import json
import re
import numpy as np
from PIL import Image  # Pillow package

_logger = logging.getLogger(__name__)


class DwarftestTransformer(object):
    # size of DF objects in DF tiles
    DF_BLOCK_TILE_SIZE = (16, 16, 16)
    DF_REGION_TILE_SIZE = (48, 48, 1)

    # size of MT objects in MT nodes
    MT_BLOCK_NODE_SIZE = (16, 16, 16)

    # MT content ids
    MT_CONTENT_ID_PREFIX = 'dwarftest:'
    MT_AIR_CONTENT_ID = 'air'
    MT_UNKNOWN_CONTENT_ID = MT_CONTENT_ID_PREFIX + 'unknown'
    MT_WATER_CONTENT_ID = MT_CONTENT_ID_PREFIX + 'water_source'
    MT_LAVA_CONTENT_ID = MT_CONTENT_ID_PREFIX + 'lava_source'

    # DF blacklisted mat types
    DF_BLACKLISTED_MAT_TYPES = ['AIR', 'UNKNOWN', 'CREATURE']

    # templates
    TEXTURE_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), './templates/textures')

    def __init__(self, minetest_world, df_region_offset=(0, 0, 0), complex_block_scale=None):

        self.minetest_world = minetest_world
        self.df_region_offset = df_region_offset  # used to move center of DF world to 0,0,0 in MT

        # Size of one DF tile/block in Minetest nodes

        self.complex_block_scale = complex_block_scale or {
            'tile_x': 1, 'tile_y': 1, 'tile_z_floor': 0, 'tile_z_wall': 1
        }
        self.block_scale = (
            self.complex_block_scale['tile_x'],
            self.complex_block_scale['tile_y'],
            self.complex_block_scale['tile_z_floor'] + self.complex_block_scale['tile_z_wall'],
        )

        # List of unfinished MT blocks

        self.mt_blocks = {}  # key: mt_block_pos

        # tile types

        self.tiletype_list = []
        self.tiletype_df_lookup = {}

        # material list

        self.material_list = []
        self.material_df_lookup = {}

        mt_air_mat = {
            'name': 'air',
            'color': (0, 0, 0),
            'df_id': 'AIR',
            'mt_id': self.MT_AIR_CONTENT_ID,
        }
        self.material_list.append(mt_air_mat)
        self.material_df_lookup[(-1, -1)] = mt_air_mat

        mt_unknown_mat = {
            'name': 'unknown',
            'color': (0, 0, 0),
            'df_id': 'UNKNOWN',
            'mt_id': self.MT_UNKNOWN_CONTENT_ID,
        }
        self.material_list.append(mt_unknown_mat)
        self.material_df_lookup[(None, None)] = mt_unknown_mat

    # coordinates conversions

    def df2mt_pos(self, region_pos, tile_pos):
        # apply region offset
        region_pos = (
            region_pos[0] - self.df_region_offset[0],
            region_pos[1] - self.df_region_offset[1],
            region_pos[2] - self.df_region_offset[2],
        )

        # absolute DF tile position
        df_pos = (
            region_pos[0] * self.DF_REGION_TILE_SIZE[0] + tile_pos[0],
            region_pos[1] * self.DF_REGION_TILE_SIZE[1] + tile_pos[1],
            region_pos[2] * self.DF_REGION_TILE_SIZE[2] + tile_pos[2],
        )

        # convert to MT node position
        mt_pos = (  # NOTE: MT pos is (X, Z, Y)
            df_pos[0] * self.block_scale[0],
            df_pos[2] * self.block_scale[2],
            df_pos[1] * self.block_scale[1],
        )

        return mt_pos

    def mt2mt_block_pos(self, mt_pos):
        mt_block_pos = [
            int(mt_pos[0] / self.MT_BLOCK_NODE_SIZE[0]),
            int(mt_pos[1] / self.MT_BLOCK_NODE_SIZE[1]),
            int(mt_pos[2] / self.MT_BLOCK_NODE_SIZE[2]),
        ]

        mt_block_node_pos = [
            int(mt_pos[0] - mt_block_pos[0] * self.MT_BLOCK_NODE_SIZE[0]),
            int(mt_pos[1] - mt_block_pos[1] * self.MT_BLOCK_NODE_SIZE[1]),
            int(mt_pos[2] - mt_block_pos[2] * self.MT_BLOCK_NODE_SIZE[2]),
        ]

        if mt_block_node_pos[0] < 0:
            mt_block_node_pos[0] = mt_block_node_pos[0] + self.MT_BLOCK_NODE_SIZE[0]
        if mt_block_node_pos[1] < 0:
            mt_block_node_pos[1] = mt_block_node_pos[1] + self.MT_BLOCK_NODE_SIZE[1]
        if mt_block_node_pos[2] < 0:
            mt_block_node_pos[2] = mt_block_node_pos[2] + self.MT_BLOCK_NODE_SIZE[2]

        mt_block_node_index = mt_block_node_pos[0] + \
            (mt_block_node_pos[1] * self.MT_BLOCK_NODE_SIZE[1]) + \
            (mt_block_node_pos[2] * self.MT_BLOCK_NODE_SIZE[0]*self.MT_BLOCK_NODE_SIZE[1])

        return tuple(mt_block_pos), tuple(mt_block_node_pos), mt_block_node_index

    # block manipulation

    def set_mt_node(self, mt_pos, val):
        """
        :param mt_pos: minetest position (x, y, z)
        :param val: (content_id, param1, param2)
        """
        mt_block_pos, mt_block_node_pos, mt_block_node_index = self.mt2mt_block_pos(mt_pos)

        # init not used block
        if mt_block_pos not in self.mt_blocks:
            self.mt_blocks[mt_block_pos] = np.zeros(
                (self.MT_BLOCK_NODE_SIZE[0]*self.MT_BLOCK_NODE_SIZE[1]*self.MT_BLOCK_NODE_SIZE[2], ),
                dtype=self.minetest_world.BLOCK_NUMPY_DTYPE
            )
            self.mt_blocks[mt_block_pos][:] = (None, 0, 0)

        # detect if we already wrote block to DB
        if self.mt_blocks[mt_block_pos] is None:
            raise Exception('Block was already dumped to database')

        # detect out of range
        if mt_block_node_index >= self.mt_blocks[mt_block_pos].size or mt_block_node_index < 0:
            raise Exception('Node index {} is out of range! [mt_pos={}, mt_block_pos={}, mt_block_node_pos={}]'.format(
                mt_block_node_index, mt_pos, mt_block_pos, mt_block_node_pos))

        # set node value
        self.mt_blocks[mt_block_pos][mt_block_node_index] = val

    def complete_mt_blocks(self):
        for mt_block_pos in self.mt_blocks:
            if self.mt_blocks[mt_block_pos] is None:
                continue
            for i in range(self.mt_blocks[mt_block_pos].size):
                if self.mt_blocks[mt_block_pos][i]['content_id'] is not None:
                    continue
                self.mt_blocks[mt_block_pos][i] = (self.MT_AIR_CONTENT_ID, 0, 0)
        # TODO: try to spread defined nodes into undefined area

    def dump_mt_blocks(self):
        for mt_block_pos in self.mt_blocks:
            if self.mt_blocks[mt_block_pos] is None:
                continue
            if None in self.mt_blocks[mt_block_pos]['content_id']:
                continue

            _logger.debug('Saving block {} into database'.format(mt_block_pos))
            block = self.minetest_world.build_map_block(self.mt_blocks[mt_block_pos])
            self.minetest_world.write_block(mt_block_pos[0], mt_block_pos[1], mt_block_pos[2], block)
            self.mt_blocks[mt_block_pos] = None

        self.minetest_world.commit_sql_connections()

    # Tile Types

    def load_df_tiletype_list(self, df_tiletype_list):
        for df_tile_type in df_tiletype_list:
            tiletype = {
                'df_id': df_tile_type['id'],
                'name': df_tile_type['name'],
                'caption': df_tile_type['caption'],
                'shape': df_tile_type['shape'],
                'special': df_tile_type['special'],
                'material': df_tile_type['material'],
                'variant': df_tile_type['variant'],
                'direction': df_tile_type['direction'],
            }
            self.tiletype_list.append(tiletype)
            self.tiletype_df_lookup[tiletype['df_id']] = tiletype

    def get_tiletype(self, df_id):
        if df_id in self.tiletype_df_lookup:
            return self.tiletype_df_lookup[df_id]
        else:
            raise Exception('Could not find tiletype with id {}'.format(df_id))

    # Materials

    def load_df_material_list(self, df_mat_list):
        for df_mat in df_mat_list:
            # build MT material format

            if df_mat.get('stateColor'):
                mat_color = (df_mat['stateColor']['red'], df_mat['stateColor']['green'], df_mat['stateColor']['blue'])
            else:
                mat_color = None

            mat_type = df_mat.get('matPair', {}).get('matType')
            mat_type_str = df_mat['id'].split(':')[0]
            mat_subtype = df_mat.get('matPair', {}).get('matIndex')

            if mat_type_str in self.DF_BLACKLISTED_MAT_TYPES:
                continue

            mt_mat = {
                'name': df_mat.get('name'),
                'color': mat_color,
                'df_id': df_mat['id'],
                'mt_id': self.MT_CONTENT_ID_PREFIX + re.sub(r'[^a-zA-Z0-9_]', '_', df_mat['id']).lower(),
            }

            # save material definition

            self.material_list.append(mt_mat)
            self.material_df_lookup[(mat_type, mat_subtype)] = mt_mat

    def build_material_mod(self):
        # get paths

        dwarftest_mod_path = os.path.join(self.minetest_world.path, 'worldmods', 'dwarftest')
        dwarftest_mod_material_list_path = os.path.join(dwarftest_mod_path, 'material_list.json')
        dwarftest_mod_textures_path = os.path.join(dwarftest_mod_path, 'textures')

        if not os.path.exists(dwarftest_mod_path) or not os.path.exists(dwarftest_mod_material_list_path) or \
            not os.path.exists(dwarftest_mod_textures_path):
            raise Exception('Could not find Dwarftest world mod paths!')

        # filter material list
        material_list = []
        for mat in self.material_list:
            mat_type_str = mat['df_id'].split(':')[0]
            if mat_type_str in self.DF_BLACKLISTED_MAT_TYPES:
                continue
            material_list.append(mat)

        # fill material_list.json

        with open(dwarftest_mod_material_list_path, 'w') as f:
            f.write(json.dumps(material_list))

        # generate node textures

        for mat in material_list:
            mat_type_str = mat['df_id'].split(':')[0]

            # init base color image
            pixel_data = np.zeros((16, 16, 4), dtype=np.uint8)
            pixel_data[:, :, 0] = mat['color'][0] if mat['color'] else 255
            pixel_data[:, :, 1] = mat['color'][1] if mat['color'] else 255
            pixel_data[:, :, 2] = mat['color'][2] if mat['color'] else 255
            pixel_data[:, :, 3] = 255
            img = Image.fromarray(pixel_data, 'RGBA')

            # apply template
            template_name = mat_type_str + '.png'
            # TODO
            # img = Image.open(stream)
            # img.paste(new_layer, (0, 0), new_layer)

            # save image
            tex_name = mat['mt_id'].replace(':', '_') + '.png'
            img.save(os.path.join(dwarftest_mod_textures_path, tex_name))

    def get_material(self, mat_dict=None, mat_tuple=None):
        if mat_dict:
            mat_tuple = (mat_dict['matType'], mat_dict['matIndex'])
        assert mat_tuple

        if mat_tuple in self.material_df_lookup:
            return self.material_df_lookup[mat_tuple]
        else:
            _logger.error('Could not find material for {}'.format(mat_tuple))
            return self.material_df_lookup[(None, None)]

    # parse DF map

    def df_tile_to_mt_nodes(self, tiletype, material, water_height, lava_height):
        """
        DF tile includes info about wall-level and floor-level. roof-level is defined by floor-level of tile above it. (maybe?)

        This function should eventually be used to generate other shapes than just wall/floor.

        Useful sources:
            https://github.com/DFHack/dfhack/blob/8a1979b8a7aecee299c0d74720ee37eeaef9fee5/plugins/reveal.cpp#L331

        :returns: [(node_pos_difference, mt_node), ...]
        """
        converted_nodes = []

        #
        # Detect shape
        #

        # Walls
        if tiletype['shape'] in ['WALL', 'FORTIFICATION', ]:
            fill_wall = True
            fill_floor = True
            # TODO: fortification should change block "variant" to something "transparent"

        # Open space
        elif tiletype['shape'] in ['NONE', 'EMPTY', 'RAMP_TOP', 'STAIR_UPDOWN', 'STAIR_DOWN', 'BROOK_TOP']:
            fill_wall = False
            fill_floor = False

        # Floors
        elif tiletype['shape'] in ['STAIR_UP', 'RAMP', 'FLOOR', 'BRANCH', 'TRUNK_BRANCH', 'TWIG',
                                   'SAPLING', 'SHRUB', 'BOULDER', 'PEBBLES', 'BROOK_BED', 'ENDLESS_PIT']:
            fill_wall = False
            fill_floor = True

        else:
            raise Exception('Unexpected tile shape "{}"'.format(tiletype['shape']))

        #
        # Detect MT content ids
        #

        if fill_wall:
            wall_content_id = material['mt_id']
        elif water_height:
            wall_content_id = self.MT_WATER_CONTENT_ID
        elif lava_height:
            wall_content_id = self.MT_LAVA_CONTENT_ID
        else:
            wall_content_id = self.MT_AIR_CONTENT_ID

        if fill_floor:
            floor_content_id = material['mt_id']
        elif water_height:
            floor_content_id = self.MT_WATER_CONTENT_ID
        elif lava_height:
            floor_content_id = self.MT_LAVA_CONTENT_ID
        else:
            floor_content_id = self.MT_AIR_CONTENT_ID

        #
        # Build shape
        #

        for x in range(self.block_scale[0]):
            for y in range(self.block_scale[1]):
                for z in range(self.block_scale[2]):
                    if z < self.complex_block_scale['tile_z_floor']:
                        mt_node = (floor_content_id, 0, 0)
                    else:
                        mt_node = (wall_content_id, 0, 0)
                    converted_nodes.append(((x, z, y), mt_node))

        return converted_nodes

    def parse_df_blocks(self, region_pos, block_list):
        """
        For some weird reason blocks can be requested from DFHack only once, after that API starts returning empty data.
        This can only be fixed by restarting Dwarf Fortress + DFHack.

        block = {
            'mapX': int,
            'mapY': int,
            'mapZ': int,
            'tiles': list of 256 int,
            'materials': list of ??? {'matType': int, 'matIndex': int},
            'layerMaterials': list of ??? {'matType': int, 'matIndex': int},
            'veinMaterials': list of ??? {'matType': int, 'matIndex': int},
            'baseMaterials': list of ??? {'matType': int, 'matIndex': int},
            'magma': list of 256 int,
            'water': list of 256 int,
            'hidden': list of 256 bool,
            'light': list of 256 bool,
            'subterranean': list of 256 bool,
            'outside': list of 256 bool,
            'aquifer': list of 256 bool,
            'waterStagnant': list of 256 bool,
            'waterSalt': list of 256 bool,
            'constructionItems': list of ??? {'matType': int, 'matIndex': int},
            'buildings': {},
            'treePercent': list of 256 int,
            'treeX': list of 256 int,
            'treeY': list of 256 int,
            'treeZ': list of 256 int,
            'tileDigDesignation': list of 256 str,
            'tileDigDesignationMarker': list of 256 bool,
            'tileDigDesignationAuto': list of 256 bool,
            'spatterPile': list of ???,
            'items': list of dict,
            'grassPercent': list of ???,
            'flows': list of ???,
        }

        Parent BlockList object also includes:
           'mapX': region_x_pos,
           'mapY': region_y_pos,
           'engravings': list of ???,
           'oceanWaves': list of ???,
        """
        for block in block_list:
            if len(block['materials']) != 256:
                raise Exception(
                    'List of block materials has invalid length! Try to restart Dwarf Fortress.'
                )

            for i in range(256):
                # parse "tile" values

                tiletype = self.get_tiletype(block['tiles'][i])
                mat = self.get_material(mat_dict=block['materials'][i])
                # layer_mat = self.get_material(mat_dict=block['layerMaterials'][i])  # useless?
                # vain_mat = self.get_material(mat_dict=block['veinMaterials'][i])  # useless?
                # base_mat = self.get_material(mat_dict=block['baseMaterials'][i])  # ground floor?
                # cons_mat = self.get_material(mat_dict=block['constructionItems'][i])  # mat of construction
                water_height = block['water'][i]
                lava_height = block['magma'][i]

                # convert tile to nodes

                converted_nodes = self.df_tile_to_mt_nodes(tiletype, mat, water_height, lava_height)

                # set nudes

                tile_pos = (
                    int(i % self.DF_BLOCK_TILE_SIZE[0]) + block['mapX'],
                    int(i / self.DF_BLOCK_TILE_SIZE[0]) + block['mapY'],
                    int(i / (self.DF_BLOCK_TILE_SIZE[0] * self.DF_BLOCK_TILE_SIZE[1])) + block['mapZ'],
                )

                mt_pos = self.df2mt_pos(region_pos, tile_pos)
                for node_pos, mt_node in converted_nodes:
                    mt_node_pos = (
                        mt_pos[0] + node_pos[0],
                        mt_pos[1] + node_pos[1],
                        mt_pos[2] + node_pos[2],
                    )
                    self.set_mt_node(mt_node_pos, mt_node)

    # def parse_df_tile_layers(self, region_pos, tile_layers):  # TODO: might be wrong use of data?
    #     """
    #     tile_layer = {
    #         'matTypeTable': list of AIR/LIQUID/PLANT/INORGANIC,
    #         'matSubtypeTable': list of material subtype ids,
    #         'tileShapeTable': always empty list?,
    #         'tileColorTable': always empty list?,
    #     }
    #     """
    #     for z, tl in enumerate(tile_layers):
    #         if len(tl['matTypeTable']) != self.DF_REGION_TILE_SIZE[0]*self.DF_REGION_TILE_SIZE[1]:
    #             raise Exception('Unexpected size {} of tile layer'.format(len(tl['matTypeTable'])))
    #
    #         for i, (mat_type, mat_subtype) in enumerate(zip(tl['matTypeTable'], tl['matSubtypeTable'])):
    #             content_id = self.MT_AIR_CONTENT_ID if mat_type == 'AIR' else self.MT_UNKNOWN_CONTENT_ID  # TODO
    #             mt_node = (content_id, 0, 0)
    #
    #             y = int(i / self.DF_REGION_TILE_SIZE[1])
    #             x = i - (y * self.DF_REGION_TILE_SIZE[1])
    #             tile_pos = (x, y, z)
    #
    #             mt_pos = self.df2mt_pos(region_pos, tile_pos)
    #             self.set_mt_node(mt_pos, mt_node)
