# core/catshop_io.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import struct

# -----------------------------
# Entry (16 bytes, little-endian):
#   u16 item_id
#   u32 unk1
#   u16 pad1
#   u16 item_id2
#   u32 unk2
#   u16 pad2
#
# Block is a sequence of entries starting at pointer @ 0xB10.
# Valid rows have unk1 == 0xFFFFFFFF. Stop when unk1 != 0xFFFFFFFF (terminator).
#
# On save:
#   - Write rows with unk1=unk2=0xFFFFFFFF; pad1=pad2=0
#   - Write one terminator row with unk1=0 (zeros OK)
#   - Append at EOF (aligned) and update pointer @ 0xB10
#   - Update counters.CatShopItemCounter (u16) at counters.offset + 4
# -----------------------------

POINTER_OFFSET_B10 = 0xB10
ENTRY_PACK = "<H I H H I H"
ENTRY_SIZE = struct.calcsize(ENTRY_PACK)
SENTINEL = 0xFFFFFFFF

ALIGN = 0x10
END_PADDING = 0x400


@dataclass
class CatShopItem:
    item_id: int
    item_id2: int
    # Internal fields retained for completeness
    unk1: int = SENTINEL
    pad1: int = 0
    unk2: int = SENTINEL
    pad2: int = 0
    offset: int = -1  # original file offset of entry (informational)


@dataclass
class CatShopParsed:
    rows: list[CatShopItem]


def _read_u32_le(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _write_u32_le(b: bytearray, off: int, val: int) -> None:
    struct.pack_into("<I", b, off, val)


def _align_up(n: int, align: int) -> int:
    r = n % align
    return n if r == 0 else n + (align - r)


def parse_catshop(mhfdat_path: str | os.PathLike[str]) -> CatShopParsed | None:
    """Parse Cat Shop entries from pointer @ 0xB10; stop when unk1 != 0xFFFFFFFF."""
    data = Path(mhfdat_path).read_bytes()
    if len(data) < POINTER_OFFSET_B10 + 4:
        return None

    ptr = _read_u32_le(data, POINTER_OFFSET_B10)
    if ptr == 0 or ptr + ENTRY_SIZE > len(data):
        return None

    rows: list[CatShopItem] = []
    cursor = ptr
    while cursor + ENTRY_SIZE <= len(data):
        item_id, unk1, pad1, item_id2, unk2, pad2 = struct.unpack_from(ENTRY_PACK, data, cursor)
        if unk1 != SENTINEL:
            break  # terminator
        rows.append(CatShopItem(
            item_id=item_id,
            item_id2=item_id2,
            unk1=unk1, pad1=pad1,
            unk2=unk2, pad2=pad2,
            offset=cursor
        ))
        cursor += ENTRY_SIZE

    return CatShopParsed(rows=rows)


def save_catshop(
    mhfdat_in: str | os.PathLike[str],
    mhfdat_out: str | os.PathLike[str],
    parsed: CatShopParsed,
    *,
    counters,                      # DataCounters with .offset (start of <5H>) and CatShopItemCounter field (c_unk3)
    counter_items_count: int,      # u16 value to write = total number of items (not rows)
    always_move_to_eof: bool = True,
    eof_align: int = ALIGN,
    end_padding: int = END_PADDING,
) -> None:
    """
    Save Cat Shop:
      - rebuild rows (unk1=unk2=SENTINEL, pads=0)
      - append a terminator row (unk1=0)
      - write at EOF (aligned), update pointer @ 0xB10
      - update counters.CatShopItemCounter (u16) at counters.offset + 4 with 'counter_items_count'
    """
    # Build block bytes
    block = bytearray()

    # Real rows
    for r in parsed.rows:
        block += struct.pack(
            ENTRY_PACK,
            int(r.item_id),
            SENTINEL,  # unk1
            0,         # pad1
            int(r.item_id2),
            SENTINEL,  # unk2
            0          # pad2
        )

    # Terminator row: unk1 != SENTINEL (zeros OK)
    block += struct.pack(ENTRY_PACK, 0, 0, 0, 0, 0, 0)

    # Read base file, compute target offset, insert block, update pointer
    base = bytearray(Path(mhfdat_in).read_bytes())

    target_off = _align_up(len(base), eof_align) if always_move_to_eof else _read_u32_le(base, POINTER_OFFSET_B10)
    if target_off > len(base):
        base.extend(b"\x00" * (target_off - len(base)))

    base[target_off:target_off] = block
    _write_u32_le(base, POINTER_OFFSET_B10, target_off)

    # Update CatShopItemCounter (3rd u16 in <5H> counters block)
    # Layout: c_unk1 (0), c_unk2 (2), c_unk3 (4) ← CatShopItemCounter, c_unk4 (6), c_RoadEntries (8)
    if hasattr(counters, "offset"):
        catshop_off_u16 = counters.offset + 4
        if 0 <= catshop_off_u16 <= len(base) - 2:
            val = min(max(int(counter_items_count), 0), 0xFFFF)
            struct.pack_into("<H", base, catshop_off_u16, val)
            # Keep the in-memory object in sync
            if hasattr(counters, "CatShopItemCounter"):
                counters.CatShopItemCounter = val

    # Trailing padding after the block
    if end_padding:
        base.extend(b"\x00" * end_padding)

    Path(mhfdat_out).write_bytes(base)
