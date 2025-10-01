
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

def _pad_to_alignment(buf: bytearray, align: int) -> int:
    """Pad buf with 0x00 so len(buf) becomes a multiple of 'align'. Returns bytes added."""
    if align <= 1:
        return 0
    pad = (-len(buf)) & (align - 1)  # works for power-of-two aligns
    if pad:
        buf += b"\x00" * pad
    return pad

def _build_monster_block(rows) -> bytes:
    """Serialize rows -> contiguous <8H> records and pad to 0x10 alignment."""
    import struct
    out = bytearray()
    for r in rows:
        out += struct.pack(
            '<8H',
            r.monster_id, r.monster_flag, r.base_points,
            r.level1_points, r.level2_points, r.level3_points,
            r.level4_points, r.level5_points
        )
    # pad to 0x10 (safe, compact). Use 0x1000 if you want to preserve original size.
    while len(out) % 0x10 != 0:
        out += b'\x00'
    return bytes(out)

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


def save_mhfdat(
    template_path: str,
    output_path: str,
    parsed: dict,
    *,
    always_move_to_eof: bool = True,
    eof_align: int = 0x10,
    end_padding: int = 0x400  # padding after the new block (tweak as needed)
):
    """
    Save edits to mhfdat:
      - Always relocate Monster Data block to EOF (if always_move_to_eof=True),
      - Align the insertion point to 'eof_align',
      - Add 'end_padding' bytes after the written block,
      - Update PTR_MONSTER_DATA (0xB20) to the new EOF address,
      - Write DataCounters (RoadEntries).
    """
    import struct

    # Base buffer: original file or fallback template
    data = bytearray(parsed.get("buffer") or open(template_path, "rb").read())

    rows = parsed["monster_rows"]
    counters = parsed["counters"]

    # Build the new Monster Data block (8 x u16 per row, padded to 0x10)
    new_block = _build_monster_block(rows)

    # --- always relocate to EOF if requested ---
    if always_move_to_eof:
        # Align the EOF before we drop the new block
        _pad_to_alignment(data, eof_align)

        new_ptr = len(data)            # <-- absolute offset of new block at EOF
        data += new_block              # append the new block
        if end_padding > 0:
            data += b"\x00" * end_padding  # ensure trailing padding at file end

        # Update the pointer at 0xB20 to point to the new block
        struct.pack_into("<I", data, PTR_MONSTER_DATA, new_ptr)
    else:
        original_ptr = parsed["monster_ptr"]
        data[original_ptr:original_ptr + len(new_block)] = new_block
        slack_start = original_ptr + len(new_block)
        slack_end = original_ptr + MONSTER_BLOCK_SIZE
        if slack_start < slack_end:
            data[slack_start:slack_end] = b"\x00" * (slack_end - slack_start)
        new_ptr = original_ptr

    # Write DataCounters (RoadEntries, etc.)
    data[counters.offset : counters.offset + 10] = counters.to_bytes()

    # Persist to disk
    with open(output_path, "wb") as f:
        f.write(data)

    # Keep parsed in sync for any follow-up operations
    parsed["monster_ptr"] = new_ptr
    parsed["buffer"] = bytes(data)


