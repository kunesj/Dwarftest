#!/usr/bin/env python3
# encoding: utf-8

import logging
import argparse
import json
import sys
import os
import shutil

from minetest_world import MinetestWorld
from dwarftest_transformer import DwarftestTransformer

sys.path.append(os.path.join(os.path.dirname(__file__), './DFHackRPC'))
from dfhack_rpc import DFHackRPC


def main():  # TODO: map is flipped on X axis!!!
    parser = argparse.ArgumentParser(
        description='Dwarftest'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Debug debug level')
    parser.add_argument(
        '--save_dump',
        action='store_true',
    )
    parser.add_argument(
        '--load_dump',
        action='store_true',
    )
    parser.add_argument(
        '--skip_material_build',
        action='store_true',
    )
    parser.add_argument(
        '--skip_block_build',
        action='store_true',
    )
    parser.add_argument(
        '--additional_tile_z_offset',
        type=int, default=37
    )
    parser.add_argument(
        '--path',
        default='./build',
    )
    args = parser.parse_args()

    logging.basicConfig()
    _logger = logging.getLogger()

    if args.debug:
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.WARNING)

    # Init dump directories

    path_dump_blocks = './dump/blocks'
    if args.save_dump and not os.path.exists(path_dump_blocks):
        os.makedirs(path_dump_blocks)

    # Init build directory

    print('Init build directory')

    path_games = os.path.join(args.path, 'games')
    if not os.path.exists(path_games):
        os.makedirs(path_games)

    path_worlds = os.path.join(args.path, 'worlds')
    if not os.path.exists(path_worlds):
        os.makedirs(path_worlds)

    path_games_dwarftest = os.path.join(path_games, 'dwarftest')
    if not os.path.exists(path_games_dwarftest):
        shutil.copytree(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates/game'),
            path_games_dwarftest
        )

    print('-------------------------------------------')

    # Init DFHack RPC

    rpc = DFHackRPC()
    rpc.bind_all_methods()

    # Print versions

    print('DFHack version: ', end='')
    resp, _ = rpc.call_method('GetVersion')
    print(resp.value)

    print('DF version: ', end='')
    resp, _ = rpc.call_method('GetDFVersion')
    print(resp.value)

    print('RemoteFortressReader version: ', end='')
    resp, _ = rpc.call_method('GetVersionInfo')
    print(resp.remote_fortress_reader_version)

    print('-------------------------------------------')

    # Get basic info

    print('World: ', end='')
    map_info, _ = rpc.call_method('GetMapInfo')
    # print(map_info)
    world_name = '{} - {} - {}'.format(map_info.world_name, map_info.world_name_english, map_info.save_name)
    print(world_name)

    print('Embark: ', end='')
    embark_info, _ = rpc.call_method('GetEmbarkInfo')
    # print(embark_info)
    print('available={}, size={}x{}, region_x={}, region_y={}'.format(
        embark_info.available, embark_info.region_size_x, embark_info.region_size_y,
        embark_info.region_x, embark_info.region_y
    ))
    if not embark_info.available:
        raise Exception('Embark is not available')

    print('Getting WorldMap...')
    world_map, _ = rpc.call_method('GetWorldMap')
    # print(world_map)

    print('-------------------------------------------')

    # Init Minetest world and block transformer

    print('Init of Minetest world and Dwarftest transformer..')

    df_region_offset = (world_map.center_x, world_map.center_y, world_map.center_z + args.additional_tile_z_offset)
    print('df_region_offset = {}'.format(df_region_offset))

    complex_block_scale = {'tile_x': 2, 'tile_y': 2, 'tile_z_floor': 1, 'tile_z_wall': 2}
    print('complex_block_scale = {}'.format(complex_block_scale))

    path_world = os.path.join(path_worlds, world_name)
    mw = MinetestWorld(path_world, allow_overwrite=True)
    dt = DwarftestTransformer(mw, df_region_offset=df_region_offset, complex_block_scale=complex_block_scale)

    print('-------------------------------------------')

    # Get block types

    print('Getting block types etc..')

    # enums, _ = rpc.call_method_dict('ListEnums')

    material_list, _ = rpc.call_method_dict('GetMaterialList')
    dt.load_df_material_list(material_list['materialList'])

    tiletype_list, _ = rpc.call_method_dict('GetTiletypeList')
    dt.load_df_tiletype_list(tiletype_list['tiletypeList'])

    if not args.skip_material_build:
        print('Building material mod')
        dt.build_material_mod()

    print('-------------------------------------------')

    # process tiles/nodes

    if not args.skip_block_build:

        print('Processing DF Blocks...')

        region_pos = (map_info.block_pos_x, map_info.block_pos_y, map_info.block_pos_z)
        for x in range(map_info.block_size_x):
            for y in range(map_info.block_size_y):
                print('Block x={} y={} z=0-{}'.format(x, y, map_info.block_size_z))

                # NOTE: reading more than 16*16*1=256 tiles causes problems
                for z in range(map_info.block_size_z):
                    path_dump_blocks_this = os.path.join(path_dump_blocks, '{}_{}_{}.json'.format(x, y, z))

                    if args.load_dump:
                        with open(path_dump_blocks_this, 'r') as f:
                            block_list = json.loads(f.read())
                    else:
                        block_list, _ = rpc.call_method_dict('GetBlockList', {
                            # 'blocksNeeded': 1,
                            'minX': x, 'maxX': x+1,
                            'minY': y, 'maxY': y+1,
                            'minZ': z, 'maxZ': z+1,
                        })
                    if args.save_dump:
                        with open(path_dump_blocks_this, 'w') as f:
                            f.write(json.dumps(block_list))

                    dt.parse_df_blocks(region_pos, block_list['mapBlocks'])

                # save completely filled block to MT database
                dt.dump_mt_blocks()

        # print('Processing DF EmbarkTiles..')
        #
        # for x in range(embark_info.region_size_x):
        #     for y in range(embark_info.region_size_y):
        #         print('EmbarkTile x={} y={}'.format(x, y))
        #
        #         embark_tile, text = rpc.call_method_dict('GetEmbarkTile', {'wantX': x, 'wantY': y})
        #         if not embark_tile.get('isValid'):
        #             raise Exception('EmbarkTile is not valid')
        #
        #         region_pos = (embark_tile['worldX'], embark_tile['worldY'], embark_tile['worldZ'])
        #         dt.parse_df_tile_layers(region_pos, embark_tile['tileLayer'])
        #
        #         dt.dump_mt_blocks()

        print('Completing partial blocks')

        dt.complete_mt_blocks()

        print('Saving blocks to database')

        dt.dump_mt_blocks()

        print('-------------------------------------------')

    # save world + close connection

    print('Saving and exiting..')

    mw.commit_sql_connections()
    mw.close_sql_connections()
    rpc.close_connection()


if __name__ == '__main__':
    main()
