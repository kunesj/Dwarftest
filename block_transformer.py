#!/usr/bin/env python3
# encoding: utf-8


class BlockTransformer(object):
    # size of DF objects in DF tiles
    DF_BLOCK_TILE_SIZE = (16, 16, 16)
    DF_REGION_TILE_SIZE = (48, 48, 48)
    # size of MT objects in MT nodes
    MT_BLOCK_NODE_SIZE = (16, 16, 16)

    def __init__(self, minetest_world, df_region_offset=(0, 0, 0), block_scale=(1, 1, 1)):
        self.minetest_world = minetest_world
        self.df_region_offset = df_region_offset  # used to move center of DF world to 0,0,0 in MT
        self.block_scale = block_scale  # Size of one DF tile/block in Minetest nodes

        self.mt_blocks = {}  # key: mt_block_pos

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
        mt_pos = (
            df_pos[0] * self.block_scale[0],
            df_pos[1] * self.block_scale[1],
            df_pos[2] * self.block_scale[2],
        )

        return mt_pos

    # def mt2df_pos(self, mt_pos):
    #     # convert to absolute DF tile position
    #     df_pos = (
    #         int(mt_pos[0] / self.block_scale[0]),
    #         int(mt_pos[1] / self.block_scale[1]),
    #         int(mt_pos[2] / self.block_scale[2]),
    #     )
    #
    #     # calculate region and tile position
    #     region_pos = (
    #         int(df_pos[0] / self.DF_REGION_TILE_SIZE[0]),
    #         int(df_pos[1] / self.DF_REGION_TILE_SIZE[1]),
    #         int(df_pos[2] / self.DF_REGION_TILE_SIZE[2]),
    #     )
    #     tile_pos = (
    #         df_pos[0] - region_pos[0] * self.DF_REGION_TILE_SIZE[0],
    #         df_pos[1] - region_pos[1] * self.DF_REGION_TILE_SIZE[1],
    #         df_pos[2] - region_pos[2] * self.DF_REGION_TILE_SIZE[2],
    #     )
    #
    #     # apply region offset
    #     region_pos = (
    #         region_pos[0] + self.df_region_offset[0],
    #         region_pos[1] + self.df_region_offset[1],
    #         region_pos[2] + self.df_region_offset[2],
    #     )
    #
    #     return region_pos, tile_pos

    def mt2mt_block_pos(self, mt_pos):
        mt_block_pos = (
            int(mt_pos[0] / self.MT_BLOCK_NODE_SIZE[0]),
            int(mt_pos[1] / self.MT_BLOCK_NODE_SIZE[1]),
            int(mt_pos[2] / self.MT_BLOCK_NODE_SIZE[2]),
        )
        mt_block_node_pos = (
            int(mt_pos[0] - mt_block_pos[0] * self.MT_BLOCK_NODE_SIZE[0]),
            int(mt_pos[1] - mt_block_pos[1] * self.MT_BLOCK_NODE_SIZE[1]),
            int(mt_pos[2] - mt_block_pos[2] * self.MT_BLOCK_NODE_SIZE[2]),
        )
        mt_block_node_index = mt_block_node_pos[0] + \
            (mt_block_node_pos[1] * self.MT_BLOCK_NODE_SIZE[1]) + \
            (mt_block_node_pos[2] * self.MT_BLOCK_NODE_SIZE[0]*self.MT_BLOCK_NODE_SIZE[1])

        return mt_block_pos, mt_block_node_pos, mt_block_node_index

    # block manipulation

    def set_mt_node(self, mt_pos, val):
        mt_block_pos, mt_block_node_pos, mt_block_node_index = self.mt2mt_block_pos(mt_pos)

        # init not used block
        if mt_block_pos not in self.mt_blocks:
            self.mt_blocks[mt_block_pos] = [None, ] * (
                    self.MT_BLOCK_NODE_SIZE[0]*self.MT_BLOCK_NODE_SIZE[1]*self.MT_BLOCK_NODE_SIZE[2]
            )

        # detect if we already wrote block to DB
        if self.mt_blocks[mt_block_pos] is None:
            raise Exception('Block was already dumped to database')

        # detect out of range
        if mt_block_node_index >= len(self.mt_blocks[mt_block_pos]) or mt_block_node_index < 0:
            raise Exception('Node index {} is out of range!'.format(mt_block_node_index))

        # set node value
        self.mt_blocks[mt_block_pos][mt_block_node_index] = val

    def complete_mt_blocks(self):
        for mt_block_pos in self.mt_blocks:
            if not self.mt_blocks[mt_block_pos] or None not in self.mt_blocks[mt_block_pos]:
                continue
            self.mt_blocks[mt_block_pos] = [(x or ['air', 0, 0]) for x in self.mt_blocks[mt_block_pos]]
        # TODO: try to spread defined nodes into undefined area

    def dump_mt_blocks(self):
        for mt_block_pos in self.mt_blocks:
            if self.mt_blocks[mt_block_pos] and None not in self.mt_blocks[mt_block_pos]:
                block = self.minetest_world.build_map_block(self.mt_blocks[mt_block_pos])
                self.minetest_world.write_block(mt_block_pos[0], mt_block_pos[1], mt_block_pos[2], block)
                self.mt_blocks[mt_block_pos] = None
        self.minetest_world.commit_sql_connections()

    # parse DF map

    def parse_df_tile_layers(self, region_pos, tile_layers):
        """
        tile_layer = {
            'matTypeTable': list of AIR/LIQUID/PLANT/INORGANIC,
            'matSubtypeTable': list of material subtype ids,
            'tileShapeTable': [],
            'tileColorTable': [],
        }
        """
        for z, tl in enumerate(tile_layers):
            if len(tl['matTypeTable']) != self.DF_REGION_TILE_SIZE[0]*self.DF_REGION_TILE_SIZE[1]:
                raise Exception('Unexpected size {} of tile layer'.format(len(tl['matTypeTable'])))

            for i, (mat_type, mat_subtype) in enumerate(zip(tl['matTypeTable'], tl['matSubtypeTable'])):
                content_id = 'air' if mat_type == 'AIR' else 'default:stone'  # TODO

                y = int(i / self.DF_REGION_TILE_SIZE[1])
                x = i - (y * self.DF_REGION_TILE_SIZE[1])
                tile_pos = (x, y, z)

                mt_pos = self.df2mt_pos(region_pos, tile_pos)
                self.set_mt_node(mt_pos, [content_id, 0, 0])
