# core/medalshop_io.py

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct

POINTER_OFFSET_MEDAL = 0x948
EXTRA_POINTER_OFFSET = 0x910  # location where pointer to counters is stored

TOWER_PACK = "<H H B B B B H H"
TOWER_SIZE = struct.calcsize(TOWER_PACK)

@dataclass
class MedalItem:
    item: int
    random: int
    quantity: int
    price: int
    offset: int = -1

@dataclass
class MedalParsed:
    rows: list[MedalItem]

def parse_medal_shop(mhfdat_path: str | Path) -> MedalParsed | None:
    data = Path(mhfdat_path).read_bytes()
    if len(data) < POINTER_OFFSET_MEDAL + 4:
        return None
    ptr = struct.unpack_from("<I", data, POINTER_OFFSET_MEDAL)[0]
    if ptr == 0 or ptr + TOWER_SIZE > len(data):
        return None
    rows = []
    cur = ptr
    while True:
        if cur + TOWER_SIZE > len(data):
            break
        (item, randv, qty, pad, pad2, pad3, price, pad4) = struct.unpack_from(TOWER_PACK, data, cur)
        if item == 0:
            break
        rows.append(MedalItem(item=item, random=randv, quantity=qty, price=price, offset=cur))
        cur += TOWER_SIZE
    return MedalParsed(rows=rows)

def _write_u32_le(barr: bytearray, off: int, val: int):
    struct.pack_into("<I", barr, off, val)

def _write_u16_le(barr: bytearray, off: int, val: int):
    struct.pack_into("<H", barr, off, val)

def _read_u32_le(barr: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", barr, off)[0]

def save_medal_shop(
    mhfdat_in: str | Path,
    mhfdat_out: str | Path,
    parsed: MedalParsed,
    *,
    eof_align: int = 0x20,
    end_padding: int = 0x400
) -> None:
    data_orig = Path(mhfdat_in).read_bytes()
    buf = bytearray(data_orig)

    # Align to boundary
    cur_len = len(buf)
    rem = cur_len % eof_align
    if rem != 0:
        buf.extend(b"\x00" * (eof_align - rem))

    new_ptr = len(buf)
    # Append medal entries
    for mi in parsed.rows:
        buf.extend(
            struct.pack(
                TOWER_PACK,
                mi.item,
                mi.random,
                mi.quantity,
                0, 0, 0,
                mi.price,
                0
            )
        )
    # Terminator
    buf.extend(struct.pack(TOWER_PACK, 0, 0, 0, 0, 0, 0, 0, 0))

    # Update pointer to medal block
    _write_u32_le(buf, POINTER_OFFSET_MEDAL, new_ptr)

    # **New logic**: read pointer at EXTRA_POINTER_OFFSET to find where extra counters begin
    if len(buf) < EXTRA_POINTER_OFFSET + 4:
        raise ValueError("File too small to contain extra pointer")
    extra_ptr = _read_u32_le(buf, EXTRA_POINTER_OFFSET)
    if extra_ptr == 0:
        raise ValueError("Extra counters pointer is zero")
    # Compute where MedalShopEntries should be
    # In struct, MedalShopEntries is index 7 (zero-based) of u16 fields
    medal_index = 7
    cnt_off = extra_ptr + (medal_index * 2)

    entries_count = len(parsed.rows)
    if entries_count < 0:
        entries_count = 0
    if entries_count > 0xFFFF:
        entries_count = 0xFFFF

    _write_u16_le(buf, cnt_off, entries_count)

    # Optionally for debugging
    # readback = struct.unpack_from("<H", buf, cnt_off)[0]
    # print(f"Writing Counter {entries_count} at 0x{cnt_off:X}, read back {readback}")

    if end_padding:
        buf.extend(b"\x00" * end_padding)

    Path(mhfdat_out).write_bytes(buf)
