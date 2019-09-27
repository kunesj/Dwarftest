#!/usr/bin/env python3
# encoding: utf-8
from dfhack_rpc import DFHackRPC
from minetest_world import MinetestWorld
from block_transformer import BlockTransformer

import logging
import argparse


def main():
    logging.basicConfig()
    _logger = logging.getLogger()
    _logger.setLevel(logging.WARNING)

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
    print('{} ({}) [{}]'.format(map_info.world_name, map_info.world_name_english, map_info.save_name))

    print('Embark: ', end='')
    embark_info, _ = rpc.call_method('GetEmbarkInfo')
    # print(embark_info)
    print('available={}, size={}x{}, region_x={}, region_y={}'.format(
        embark_info.available, embark_info.region_size_x, embark_info.region_size_y,
        embark_info.region_x, embark_info.region_y
    ))
    if not embark_info.available:
        raise Exception('Embark is not available')

    print('-------------------------------------------')

    # Get block types

    print('Getting block types etc..')

    enums, _ = rpc.call_method_dict('ListEnums')
    material_list, _ = rpc.call_method_dict('GetMaterialList')
    tiletype_list, _ = rpc.call_method_dict('GetTiletypeList')
    world_map, _ = rpc.call_method('GetWorldMap')
    # print(world_map)

    print('-------------------------------------------')

    # Init Minetest world and block transformer

    print('Init of Minetest world and block transformer..')

    mw = MinetestWorld('./world', allow_overwrite=True)
    bt = BlockTransformer(mw, df_region_offset=(world_map.center_x, world_map.center_y, world_map.center_z))

    print('-------------------------------------------')

    # process tiles/nodes

    print('Processing DF EmbarkTiles..')

    for x in range(embark_info.region_size_x):
        for y in range(embark_info.region_size_y):
            print('EmbarkTile x={} y={}'.format(x, y))

            embark_tile, text = rpc.call_method_dict('GetEmbarkTile', {'wantX': x, 'wantY': y})
            if not embark_tile.get('isValid'):
                raise Exception('EmbarkTile is not valid')

            region_pos = (embark_tile['worldX'], embark_tile['worldY'], embark_tile['worldZ'])
            bt.parse_df_tile_layers(region_pos, embark_tile['tileLayer'])

            bt.dump_mt_blocks()

    bt.complete_mt_blocks()
    bt.dump_mt_blocks()

    print('-------------------------------------------')

    # save world + close connection

    print('Saving and exiting..')

    mw.commit_sql_connections()
    mw.close_sql_connections()
    rpc.close_connection()


if __name__ == '__main__':
    main()
