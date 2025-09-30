
import os, struct
from dataclasses import dataclass

MONSTER_BLOCK_SIZE = 4096  # bytes, per hexpat
PTR_MONSTER_DATA = 0xB20   # u32 pointer to Monster Data block
PTR_COUNTERS     = 0xB04   # u32 pointer to DataCounters block (contains RoadEntries at +8)

@dataclass
class MonsterPoints:
    monster_id: int
    monster_flag: int
    base_points: int
    level1_points: int
    level2_points: int
    level3_points: int
    level4_points: int
    level5_points: int
    offset: int  # absolute file offset of this row (start of struct)

    def to_bytes(self) -> bytes:
        return struct.pack('<8H',
            self.monster_id, self.monster_flag, self.base_points,
            self.level1_points, self.level2_points, self.level3_points,
            self.level4_points, self.level5_points
        )

@dataclass
class DataCounters:
    unk1: int
    unk2: int
    unk3: int
    unk4: int
    RoadEntries: int
    offset: int  # absolute offset to start of struct

    def to_bytes(self) -> bytes:
        return struct.pack('<5H', self.unk1, self.unk2, self.unk3, self.unk4, self.RoadEntries)


def _read_u32_le(buf: bytes, off: int) -> int:
    return struct.unpack_from('<I', buf, off)[0]

def _verify_mhfdat_signature(data: bytes):
    import struct
    header1 = struct.unpack_from("<I", data, 0x0)[0]
    header2 = struct.unpack_from("<I", data, 0x4)[0]
    # skip padding at 0x08–0x0B
    header3 = struct.unpack_from("<I", data, 0x0C)[0]

    if header1 != 0x1A66686D:  # LE: 6D 68 66 1A
        raise ValueError(f"Invalid mhfdat.bin (header1 mismatch: {header1:#X})")
    if header2 != 0x59:        # LE: 59 00 00 00
        raise ValueError(f"Invalid mhfdat.bin (header2 mismatch: {header2:#X})")
    if header3 != 0xBC8:       # LE: C8 0B 00 00
        raise ValueError(f"Invalid mhfdat.bin (header3 mismatch: {header3:#X})")

def parse_mhfdat(path: str):
    """Parse mhfdat for Monster Data table and DataCounters (RoadEntries)."""
    with open(path, 'rb') as f:
        data = f.read()

    _verify_mhfdat_signature(data)

    monster_ptr = _read_u32_le(data, PTR_MONSTER_DATA)
    counters_ptr = _read_u32_le(data, PTR_COUNTERS)

    # Parse MonsterData rows (each row 16 bytes = 8 * u16)
    rows = []
    pos = monster_ptr
    end = monster_ptr + MONSTER_BLOCK_SIZE
    while pos + 16 <= len(data) and pos < end:
        fields = struct.unpack_from('<8H', data, pos)
        md = MonsterPoints(*fields, offset=pos)
        # stop if early-termination condition (per hexpat): id == 0 or > 176
        if md.monster_id == 0 or md.monster_id > 176:
            break
        rows.append(md)
        pos += 16

    # Parse DataCounters: 5 x u16
    c_unk1, c_unk2, c_unk3, c_unk4, c_RoadEntries = struct.unpack_from('<5H', data, counters_ptr)
    counters = DataCounters(c_unk1, c_unk2, c_unk3, c_unk4, c_RoadEntries, offset=counters_ptr)

    return {
        'monster_rows': rows,
        'counters': counters,
        'monster_ptr': monster_ptr,
        'counters_ptr': counters_ptr,
        'buffer': data  # original bytes, useful for templated save
    }


def save_mhfdat(template_path: str, output_path: str, parsed: dict):
    """Write edits back using a template file, preserving everything else."""
    data = bytearray(parsed.get('buffer') or open(template_path, 'rb').read())
    # write monster rows
    for row in parsed['monster_rows']:
        data[row.offset:row.offset+16] = row.to_bytes()
    # write counters
    c = parsed['counters']
    data[c.offset:c.offset+10] = c.to_bytes()
    with open(output_path, 'wb') as f:
        f.write(data)
