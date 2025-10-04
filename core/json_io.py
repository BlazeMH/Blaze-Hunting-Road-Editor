import json
from typing import Any, Dict
from core.catshop_io import CatShopParsed, CatShopItem, parse_catshop, save_catshop
from core.medalshop_io import MedalParsed, MedalItem, parse_medal_shop, save_medal_shop

def catshop_to_json(parsed: CatShopParsed) -> str:
    data = {
        "entries": [
            {"item_id": r.item_id, "item_id2": r.item_id2}
            for r in parsed.rows
        ]
    }
    return json.dumps(data, indent=2)

def catshop_from_json(json_str: str) -> CatShopParsed:
    obj = json.loads(json_str)
    ent = obj.get("entries", [])
    rows = []
    for i, e in enumerate(ent):
        item_id = e.get("item_id", 0)
        item_id2 = e.get("item_id2", 0)
        print(f"[DEBUG json_io] entry {i}: item_id={item_id}, item_id2={item_id2}")
        rows.append(CatShopItem(item_id=item_id, item_id2=item_id2))
    return CatShopParsed(rows=rows)


def medalshop_to_json(parsed: MedalParsed) -> str:
    data = {
        "entries": [
            {
                "item": r.item,
                "flag1": r.random,
                "flag2": r.quantity,
                "price": r.price
            }
            for r in parsed.rows
        ]
    }
    return json.dumps(data, indent=2)

def medalshop_from_json(json_str: str) -> MedalParsed:
    obj = json.loads(json_str)
    ent = obj.get("entries", [])
    rows = []
    for e in ent:
        item = e.get("item", 0)
        rand = e.get("flag1", 0)
        qty = e.get("flag2", 0)
        price = e.get("price", 0)
        rows.append(MedalItem(item=item, random=rand, quantity=qty, price=price))
    return MedalParsed(rows=rows)
