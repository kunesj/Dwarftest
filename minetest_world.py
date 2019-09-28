#!/usr/bin/env python3
# encoding: utf-8

import os
import shutil
import sqlite3
import struct
import zlib
import numpy as np


def get_block_as_integer(x, y, z):
    """
    :return: database block index
    """
    return to_int64(z*16777216 + y*4096 + x)


def to_int64(u):
    while u >= 2**63:
        u -= 2**64
    while u <= -2**63:
        u += 2**64
    return u


def get_integer_as_block(i):
    """
    :param i: database block index
    :return: (x, y, z)
    """
    x = unsigned_to_signed(i % 4096, 2048)
    i = int((i - x) / 4096)
    y = unsigned_to_signed(i % 4096, 2048)
    i = int((i - y) / 4096)
    z = unsigned_to_signed(i % 4096, 2048)
    return x, y, z


def unsigned_to_signed(i, max_positive):
    if i < max_positive:
        return i
    else:
        return i - 2 * max_positive


class MinetestWorld(object):
    """
    https://github.com/minetest/minetest/blob/master/doc/world_format.txt
    !Warning! Documentation in world_format is outdated/incorrect

    Incorrect light/shadow problems can be fixed by running:
        \fixlight (x1, y1, z1) (x2, y2, z2)
    """
    GAME_ID = 'dwarftest'
    BLOCK_NUMPY_DTYPE = np.dtype([('content_id', 'object'), ('param1', np.uint8), ('param2', np.uint8)])
    TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), './templates/world')

    # Open/Close

    def __init__(self, path, allow_overwrite=False):
        self.path = path
        self.auth_sqlite_connection = None
        self.auth_sqlite_cursor = None
        self.map_sqlite_connection = None
        self.map_sqlite_cursor = None

        # create directory

        if os.path.exists(path) and not allow_overwrite:
            raise Exception('Path already exists')
        if not os.path.exists(path):
            shutil.copytree(self.TEMPLATE_PATH, self.path)

        # init text files

        self.init_auth_txt()
        self.init_env_meta_txt()
        self.init_ipban_txt()
        self.init_map_meta_txt()
        self.init_world_mt()

        # init sqlite files

        self.init_auth_sqlite()
        self.init_map_sqlite()

    def commit_sql_connections(self):
        self.auth_sqlite_connection.commit()
        self.map_sqlite_connection.commit()

    def close_sql_connections(self):
        self.commit_sql_connections()
        self.auth_sqlite_connection.close()
        self.map_sqlite_connection.close()

    # Init world files

    def init_auth_txt(self):
        with open(os.path.join(self.path, 'auth.txt'), 'w') as f:
            f.write(
                'singleplayer::server, shout, fly, password, bring, kick, teleport, ban, noclip, debug, '
                'privs, fast, basic_privs, zoom, give, protection_bypass, rollback, settime, interact\n'
            )

    def init_env_meta_txt(self):
        with open(os.path.join(self.path, 'env_meta.txt'), 'w') as f:
            f.write(
                'game_time = 12000\n'
                'time_of_day = 12000\n'
                'EnvArgsEnd\n'
            )

    def init_ipban_txt(self):
        with open(os.path.join(self.path, 'ipban.txt'), 'w') as f:
            f.write('\n')

    def init_map_meta_txt(self):
        with open(os.path.join(self.path, 'map_meta.txt'), 'w') as f:
            f.write('[end_of_params]\n')

    def init_world_mt(self):
        with open(os.path.join(self.path, 'world.mt'), 'w') as f:
            f.write(
                'gameid = {}\n'
                'creative_mode = true\n'
                'enable_damage = false\n'
                'backend = sqlite3\n'
                'player_backend = sqlite3\n'
                'auth_backend = sqlite3\n'.format(self.GAME_ID)
            )

    def init_auth_sqlite(self):
        db_path = os.path.join(self.path, 'auth.sqlite')
        db_exists = os.path.exists(db_path)

        self.auth_sqlite_connection = sqlite3.connect(db_path)
        self.auth_sqlite_cursor = self.auth_sqlite_connection.cursor()

        if not db_exists:
            self.auth_sqlite_cursor.execute('''
            CREATE TABLE `auth` (
              `id` INTEGER PRIMARY KEY AUTOINCREMENT,
              `name` VARCHAR(32) UNIQUE,
              `password` VARCHAR(512),
              `last_login` INTEGER
            );
            ''')
            self.auth_sqlite_cursor.execute('''
            CREATE TABLE `user_privileges` (
              `id` INTEGER,
              `privilege` VARCHAR(32),
              PRIMARY KEY (id, privilege)
              CONSTRAINT fk_id FOREIGN KEY (id) REFERENCES auth (id) ON DELETE CASCADE
            );
            ''')

    def init_map_sqlite(self):
        db_path = os.path.join(self.path, 'map.sqlite')
        db_exists = os.path.exists(db_path)

        self.map_sqlite_connection = sqlite3.connect(db_path)
        self.map_sqlite_cursor = self.map_sqlite_connection.cursor()

        if not db_exists:
            self.map_sqlite_cursor.execute('''
            CREATE TABLE `blocks` (`pos` INT NOT NULL PRIMARY KEY,`data` BLOB);
            ''')

    # Map Block

    def build_map_block(self, nodes):
        """
        :param nodes: numpy array of length 4096 and dtype of self.BLOCK_NUMPY_DTYPE
        :return: bytes
        """
        assert nodes.size == 4096
        nodes = nodes.copy()
        block = b''

        # u8 version
        block += struct.pack('>B', 28)

        # u8 flags
        block += struct.pack('>B', 0b00000000)

        # u16 lighting_complete
        block += struct.pack('>H', 0b0000000000000000)

        # u8 content_width
        block += struct.pack('>B', 2)

        # u8 params_width
        block += struct.pack('>B', 2)

        # zlib-compressed node data


        num_name_id_mappings = {}
        for n in nodes:
            if n['content_id'] not in num_name_id_mappings:
                num_name_id_mappings[n['content_id']] = len(num_name_id_mappings)
            n['content_id'] = num_name_id_mappings[n['content_id']]
        num_name_id_mappings = [(num_name_id_mappings[name], name) for name in num_name_id_mappings]

        node_data = [struct.pack('>H', n['content_id']) for n in nodes]
        node_data += [struct.pack('>B', n['param1']) for n in nodes]
        node_data += [struct.pack('>B', n['param2']) for n in nodes]
        node_data = b''.join(node_data)

        block += zlib.compress(node_data)

        # zlib-compressed node metadata list
        node_metadata = b''
        node_metadata += struct.pack('>I', 0)  # u32 count of metadata

        # TODO: This doc is probably incorrect! Look into source.
        # https://github.com/minetest/minetest/blob/master/src/nodemetadata.cpp#L43
        # foreach count:
        #     u16 position (p.Z*MAP_BLOCKSIZE*MAP_BLOCKSIZE + p.Y*MAP_BLOCKSIZE + p.X)
        #     u32 num_vars
        #     foreach num_vars:
        #         u16 key_len
        #         u8[key_len] key
        #         u32 val_len
        #         u8[val_len] value
        #         u8 is_private -- only for version >= 2. 0 = not private, 1 = private
        # serialized inventory

        block += zlib.compress(node_metadata)

        # u8 static object version
        block += struct.pack('>B', 0)

        # static_object_count
        block += struct.pack('>H', 0)  # u16 static_object_count

        # TODO
        # foreach static_object_count
        #     u8 type (object type-id)
        #     s32 pos_x_nodes * 10000
        #     s32 pos_y_nodes * 10000
        #     s32 pos_z_nodes * 10000
        #     u16 data_size
        #     u8[data_size] data

        # u32 timestamp
        block += struct.pack('>I', 0xffffffff)

        # u8 name-id-mapping version
        block += struct.pack('>B', 0)

        # num_name_id_mappings
        block += struct.pack('>H', len(num_name_id_mappings))  # u16 num_name_id_mappings

        name_mappings = []
        for id, name in num_name_id_mappings:
            name_mappings.append(
                struct.pack('>H', id) + struct.pack('>H', len(name)) + name.encode('ascii')
            )

        block += b''.join(name_mappings)

        # Node timers
        block += struct.pack('>B', 10)  # u8 length of the data of a single timer (always 2+4+4=10)
        block += struct.pack('>H', 0)  # u16 num_of_timers

        # TODO
        # foreach num_of_timers:
        #     u16 timer position (z*16*16 + y*16 + x)
        #     s32 timeout*1000
        #     s32 elapsed*1000

        # EOF
        return block

    def write_block(self, x, y, z, block):
        block_id = get_block_as_integer(x, y, z)

        self.map_sqlite_cursor.execute('SELECT pos FROM blocks WHERE pos=?', (block_id, ))
        rows = self.map_sqlite_cursor.fetchall()

        if len(rows) > 0:
            self.map_sqlite_cursor.execute('UPDATE blocks SET data=? WHERE pos=?', (block, block_id))
        else:
            self.map_sqlite_cursor.execute('INSERT INTO blocks(pos,data) VALUES(?,?)', (block_id, block))


if __name__ == '__main__':
    mw = MinetestWorld('./world', allow_overwrite=True)

    for x in range(-2, 2):
        for y in range(-2, 2):
            for z in range(-3, 3):
                nodes = np.zeros((4096, ), dtype=mw.BLOCK_NUMPY_DTYPE)
                nodes[:] = ('default:stone', 0, 0)

                block = mw.build_map_block(nodes)
                mw.write_block(x, y, z, block)

    mw.close_sql_connections()
