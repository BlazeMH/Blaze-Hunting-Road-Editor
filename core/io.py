
import os, struct
from .models import RoadMode, SpawnTable, FloorStats

def parse_rengoku_data(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'rb') as f:
        f.seek(0x14)
        offset = f.tell()
        multi_def = RoadMode.from_bytes(f.read(24), offset)
        offset = f.tell()
        solo_def = RoadMode.from_bytes(f.read(24), offset)

        # multi spawn tables
        spawn_tables = []
        for i in range(multi_def.SpawnTablePointersCount):
            f.seek(multi_def.SpawnTablePointers + (i * 4))
            table_pointer = struct.unpack('<I', f.read(4))[0]
            f.seek(multi_def.SpawnCountPointers + (i * 4))
            entry_count = struct.unpack('<I', f.read(4))[0]
            spawns = []
            f.seek(table_pointer)
            for _ in range(entry_count):
                offset = f.tell()
                spawns.append(SpawnTable.from_bytes(f.read(32), offset))
            spawn_tables.append(spawns)
        multi_def.spawnTables = spawn_tables

        # multi floor stats
        floor_stats = []
        f.seek(multi_def.FloorStatsPointer)
        for _ in range(multi_def.FloorStatsCount):
            offset = f.tell()
            floor_stats.append(FloorStats.from_bytes(f.read(24), offset))
        multi_def.floorStats = floor_stats

        # solo spawn tables
        spawn_tables_solo = []
        for i in range(solo_def.SpawnTablePointersCount):
            f.seek(solo_def.SpawnTablePointers + (i * 4))
            table_pointer = struct.unpack('<I', f.read(4))[0]
            f.seek(solo_def.SpawnCountPointers + (i * 4))
            entry_count = struct.unpack('<I', f.read(4))[0]
            spawns = []
            f.seek(table_pointer)
            for _ in range(entry_count):
                offset = f.tell()
                spawns.append(SpawnTable.from_bytes(f.read(32), offset))
            spawn_tables_solo.append(spawns)
        solo_def.spawnTables = spawn_tables_solo

        # solo floor stats
        floor_stats_solo = []
        f.seek(solo_def.FloorStatsPointer)
        for _ in range(solo_def.FloorStatsCount):
            offset = f.tell()
            floor_stats_solo.append(FloorStats.from_bytes(f.read(24), offset))
        solo_def.floorStats = floor_stats_solo

    return [spawn_tables, floor_stats, multi_def, spawn_tables_solo, floor_stats_solo, solo_def]


def save_structs_to_bin(template_file: str, output_file: str, structs):
    (spawn_tables, floor_stats, _multi_def, spawn_tables_solo, floor_stats_solo, _solo_def) = structs
    with open(template_file, "rb") as f:
        data = bytearray(f.read())

    for group in spawn_tables:
        for spawn in group:
            data[spawn.offset:spawn.offset+32] = spawn.serialize()
    for fs in floor_stats:
        data[fs.offset:fs.offset+24] = fs.serialize()

    for group in spawn_tables_solo:
        for spawn in group:
            data[spawn.offset:spawn.offset+32] = spawn.serialize()
    for fs in floor_stats_solo:
        data[fs.offset:fs.offset+24] = fs.serialize()

    with open(output_file, "wb") as out_f:
        out_f.write(data)
