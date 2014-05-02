def up(db):
    db.data["value"] = "a"


def down(db):
    del db.data["value"]
