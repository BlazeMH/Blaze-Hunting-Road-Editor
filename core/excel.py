
import os, re, openpyxl
from .constants import MONSTERS, DETAILS_XLSX_DEFAULT
from .models import SpawnTable
from .io import parse_rengoku_data

def add_key_sheet(wb, name, fields_desc: dict):
    sheet = wb.create_sheet(name)
    sheet.append(["Field", "Description", "Notes"])
    for field, val in fields_desc.items():
        if isinstance(val, tuple):
            if len(val) >= 2:
                desc, notes = val[0], val[1]
            else:
                desc, notes = val[0], ""
        else:
            desc = val
            notes = ""
        sheet.append([field, desc, notes])


def _append_details_sheet_if_present(wb, dest_name="Details"):
    details_path = os.environ.get("ROAD_DETAILS_XLSX", DETAILS_XLSX_DEFAULT)
    if not os.path.exists(details_path):
        return False, None
    try:
        src = openpyxl.load_workbook(details_path, data_only=False)
        if not src.sheetnames:
            return False, None
        src_ws = src[src.sheetnames[0]]
        name = dest_name
        base = dest_name
        i = 2
        while name in wb.sheetnames:
            name = f"{base} ({i})"; i += 1
        dst_ws = wb.create_sheet(name)
        for r in src_ws.iter_rows():
            for c in r:
                d = dst_ws.cell(row=c.row, column=c.col_idx, value=c.value)
                if c.has_style:
                    d.font = c.font.copy(); d.fill = c.fill.copy()
                    d.border = c.border.copy(); d.alignment = c.alignment.copy()
                    d.number_format = c.number_format; d.protection = c.protection.copy()
                if c.hyperlink: d.hyperlink = c.hyperlink.target or c.hyperlink
                if c.comment:   d.comment = openpyxl.comments.Comment(c.comment.text, c.comment.author or "")
        for m in src_ws.merged_cells.ranges: dst_ws.merge_cells(str(m))
        for col, dim in src_ws.column_dimensions.items():
            if dim.width is not None: dst_ws.column_dimensions[col].width = dim.width
        for idx, dim in src_ws.row_dimensions.items():
            if dim.height is not None: dst_ws.row_dimensions[idx].height = dim.height
        dst_ws.freeze_panes = src_ws.freeze_panes
        if getattr(src_ws, "auto_filter", None) and src_ws.auto_filter.ref:
            dst_ws.auto_filter.ref = src_ws.auto_filter.ref
        return True, details_path
    except Exception:
        return False, None


def create_excel_from_bin(rengoku_data, output_file):
    spawn_tables, floor_stats, _, _, _, _ = rengoku_data
    wb = openpyxl.Workbook()

    wb.active.title = "Floor Stats"
    floor_stats_sheet = wb.active
    headers = ["FloorNumber", "SpawnTableUsed", "Unk0", "PointMulti1", "PointMulti2", "FinalLoop"]
    floor_stats_sheet.append(headers)
    for stats in floor_stats:
        floor_stats_sheet.append([stats.FloorNumber, stats.SpawnTableUsed, stats.Unk0,
                                  stats.PointMulti1, stats.PointMulti2, stats.FinalLoop])

    # Spawn Tables
    spawn_table_sheet = wb.create_sheet("Spawn Table")
    headers = ["FirstMonsterID", "FirstMonsterVariant", "SecondMonsterID", "SecondMonsterVariant",
               "MonstersStatTable", "Bonus Spawns", "SpawnWeighting", "AdditionalFlag"]
    for group in spawn_tables:
        spawn_table_sheet.append([f"-- Group {spawn_tables.index(group)} --"])
        spawn_table_sheet.append(headers)
        for spawn in group:
            spawn_table_sheet.append(spawn.output_excel_row(MONSTERS))

    # Monster Key
    monster_key = wb.create_sheet("Monster Key")
    monster_key.append(["EM ID", "Monster Name"])
    for i, monster in enumerate(MONSTERS): monster_key.append([i, monster])

    # Field key
    spawn_table_fields = {
        "FirstMonsterID": ("ID of the first monster in the spawn pair",),
        "FirstMonsterVariant": ("Variant index of the first monster", "Different skins/forms or subspecies"),
        "SecondMonsterID": ("ID of the second monster in the spawn pair",),
        "SecondMonsterVariant": ("Variant index of the second monster", "Same as above but for the second monster"),
        "MonstersStatTable": ("Pointer/index to the monster stat table used", "Links to stats like HP, attack modifiers"),
        "Bonus Spawns": ("Stage-specific / bonus spawn parameters.",
                         "0 = Shakalaka \n1 = Blango Spawns \n2 = King Shakalaka \n3 = Custom Spawn 1 \n4 = Custom Spawn 2 \n5 = Custom Spawn 3"),
        "SpawnWeighting": ("Relative chance of this spawn being chosen", "Higher number = more likely"),
        "AdditionalFlag": ("Extra flags",
                           "0 = Default \n2 = Forced Spawn \n4 = Bonus Stage Flag \n6 = Forced Bonus Stage \n8 = Spawn Disabled ?"),
    }
    add_key_sheet(wb, "Spawn Table Key", spawn_table_fields)

    _append_details_sheet_if_present(wb, dest_name="Details")
    wb.save(output_file)


def export_excel_to_bin(excel_file, output_file, template_file):
    wb = openpyxl.load_workbook(excel_file)
    spawn_tables_ws = wb["Spawn Table"]
    tables = []; spawn_group = []; headers_row = False; headers = []
    for row in spawn_tables_ws.rows:
        first = row[0].value
        if isinstance(first, str) and re.match(r"-- Group \d+ --", first.strip()):
            if spawn_group: tables.append(spawn_group); spawn_group = []
            headers_row = True
        elif headers_row:
            headers = [cell.value for cell in row]; headers_row = False
        else:
            if all(cell.value is None for cell in row): continue
            spawn_table = {k: v for k, v in zip(headers, [cell.value for cell in row])}
            spawn_group.append(spawn_table)
    if spawn_group: tables.append(spawn_group)

    floor_stats_ws = wb["Floor Stats"]
    stats = []; headers = []
    for i, row in enumerate(floor_stats_ws.rows):
        if i == 0: headers = [cell.value for cell in row]
        else:
            if all(cell.value is None for cell in row): continue
            stat = {k: v for k, v in zip(headers, [cell.value for cell in row])}
            stats.append(stat)

    from .io import parse_rengoku_data
    structs = parse_rengoku_data(template_file)
    with open(template_file, "rb") as f: data = bytearray(f.read())

    rengoku_tables = structs[0]
    for table, group in zip(rengoku_tables, tables):
        for i, spawn in enumerate(table):
            if i >= len(group): break
            spawn.reset_values_from_row(MONSTERS, group[i])
            data[spawn.offset:spawn.offset + 32] = spawn.serialize()

    floor_stats = structs[1]
    for i, stat in enumerate(stats):
        if i >= len(floor_stats): break
        floor_stats[i].FloorNumber = int(stat["FloorNumber"])
        floor_stats[i].SpawnTableUsed = int(stat["SpawnTableUsed"])
        floor_stats[i].Unk0 = int(stat["Unk0"])
        floor_stats[i].PointMulti1 = float(stat["PointMulti1"])
        floor_stats[i].PointMulti2 = float(stat["PointMulti2"])
        floor_stats[i].FinalLoop = int(stat["FinalLoop"])
        data[floor_stats[i].offset:floor_stats[i].offset + 24] = floor_stats[i].serialize()

    with open(output_file, "wb") as out_f: out_f.write(data)
