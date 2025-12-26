# track.py
import json
from constants import SURFACE_TYPES

class Track:
    def __init__(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        self.name = data['name']
        self.width = data['width']
        self.height = data['height']
        self.tile_size = data['tile_size']
        self.grid = data['grid']
        self.start_pos = data['start_position']
        self.checkpoints = data.get('checkpoints', [])

    def get_tile(self, x, y):
        tile_x = int(x // self.tile_size)
        tile_y = int(y // self.tile_size)
        if 0 <= tile_x < self.width and 0 <= tile_y < self.height:
            return self.grid[tile_y][tile_x]
        return 2

    def get_surface_info(self, x, y):
        tile_id = self.get_tile(x, y)
        return SURFACE_TYPES.get(tile_id, SURFACE_TYPES[2])

    def is_checkpoint(self, x, y):
        tile_x = int(x // self.tile_size)
        tile_y = int(y // self.tile_size)
        for cp in self.checkpoints:
            area_size = 2.5
            if cp['x'] - area_size <= tile_x <= cp['x'] + area_size and cp['y'] - area_size <= tile_y <= cp['y'] + area_size:
                return cp['id']
        return None