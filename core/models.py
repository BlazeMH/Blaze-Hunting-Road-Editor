
import struct
from dataclasses import dataclass

@dataclass
class RoadMode:
    FloorStatsCount: int
    SpawnCountCount: int
    SpawnTablePointersCount: int
    FloorStatsPointer: int
    SpawnTablePointers: int
    SpawnCountPointers: int
    offset: int = 0

    @classmethod
    def from_bytes(cls, data: bytes, offset: int):
        fields = struct.unpack('<6I', data)
        return cls(*fields, offset)

    def serialize(self) -> bytes:
        return struct.pack('<6I', self.FloorStatsCount, self.SpawnCountCount, self.SpawnTablePointersCount,
                           self.FloorStatsPointer, self.SpawnTablePointers, self.SpawnCountPointers)

    def todict(self):  # debug helper
        return {
            'FloorStatsCount': self.FloorStatsCount,
            'SpawnCountCount': self.SpawnCountCount,
            'SpawnTablePointersCount': self.SpawnTablePointersCount,
            'FloorStatsPointer': self.FloorStatsPointer,
            'SpawnTablePointers': self.SpawnTablePointers,
            'SpawnCountPointers': self.SpawnCountPointers
        }


@dataclass
class SpawnTable:
    FirstMonsterID: int
    FirstMonsterVariant: int
    SecondMonsterID: int
    SecondMonsterVariant: int
    MonstersStatTable: int
    MapZoneOverride: int
    SpawnWeighting: int
    AdditionalFlag: int
    offset: int = 0

    @classmethod
    def from_bytes(cls, data: bytes, offset: int):
        fields = struct.unpack('<2I2I4I', data)
        return cls(*fields, offset)

    def serialize(self) -> bytes:
        import struct
        return struct.pack('<2I2I4I',
                           self.FirstMonsterID, self.FirstMonsterVariant,
                           self.SecondMonsterID, self.SecondMonsterVariant,
                           self.MonstersStatTable, self.MapZoneOverride,
                           self.SpawnWeighting, self.AdditionalFlag)

    def output_excel_row(self, monsters: list[str]) -> list:
        return [
            monsters[self.FirstMonsterID], self.FirstMonsterVariant,
            monsters[self.SecondMonsterID], self.SecondMonsterVariant,
            self.MonstersStatTable, self.MapZoneOverride, self.SpawnWeighting, self.AdditionalFlag
        ]

    def check_monster_id(self, monsters: list[str], monster_id):
        if isinstance(monster_id, str):
            if monster_id.isdigit():
                monster_id = int(monster_id)
            else:
                monster_id = monsters.index(monster_id)
        return monster_id

    def reset_values_from_row(self, monsters: list[str], group: dict):
        self.FirstMonsterID = self.check_monster_id(monsters, group["FirstMonsterID"])
        self.FirstMonsterVariant = int(group["FirstMonsterVariant"])
        self.SecondMonsterID = self.check_monster_id(monsters, group["SecondMonsterID"])
        self.SecondMonsterVariant = int(group["SecondMonsterVariant"])
        self.MonstersStatTable = int(group["MonstersStatTable"])
        mzo = group.get("Bonus Spawns", group.get("Bonus Spawn", group.get("MapZoneOverride", 0)))
        self.MapZoneOverride = int(mzo)
        self.SpawnWeighting = int(group["SpawnWeighting"])
        self.AdditionalFlag = int(group["AdditionalFlag"])


@dataclass
class FloorStats:
    FloorNumber: int
    SpawnTableUsed: int
    Unk0: int
    PointMulti1: float
    PointMulti2: float
    FinalLoop: int
    offset: int = 0

    @classmethod
    def from_bytes(cls, data: bytes, offset: int):
        fields = struct.unpack('<3I2fI', data)
        return cls(*fields, offset)

    def serialize(self) -> bytes:
        import struct
        return struct.pack('<3I2fI',
                           self.FloorNumber, self.SpawnTableUsed, self.Unk0,
                           self.PointMulti1, self.PointMulti2, self.FinalLoop)
