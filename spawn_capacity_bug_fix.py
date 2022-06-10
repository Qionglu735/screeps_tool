
# —*- coding: utf-8 -*-

import json


def main():
    with open("db.json", "r") as f:
        db = json.load(f)

    for col in db["collections"]:
        if col["name"] == "rooms.objects":
            for obj in col["data"]:
                if obj["type"] == "spawn":
                    print obj
                    if "energy" not in obj["storeCapacityResource"]:
                        print("{}: {}".format("spawn storeCapacityResource", obj["storeCapacityResource"]))
                        obj["storeCapacityResource"]["energy"] = 300
                        if "energy" not in obj["store"]:
                            print("{}: {}".format("spawn store", obj["store"]))
                            obj["store"]["energy"] = 300
                        # with open("db.json", "w") as f:
                        #     json.dump(db, f)
                        #     print("fixed")

# {'hits': 5000, '_id': 'da9712ec449ce79', 'off': False, 'room': u'W8N3', 'storeCapacityResource': {'energy': 300},
# 'hitsMax': 5000, 'notifyWhenAttacked': True, u'$loki': 359, 'meta': {'updated': 1627544085213L,
# 'created': 1627544011849L, 'version': 0, 'revision': 25}, 'user': '217812c964bd915', u'y': 11, u'x': 17,
# 'spawning': None, 'type': 'spawn', 'store': {'energy': 125}, 'name': u'Spawn1'}


if __name__ == "__main__":
    main()
