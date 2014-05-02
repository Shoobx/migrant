def up(db):
    db.data["value"] = "c"
    db.data["hello"] = "world"


def down(db):
    del db.data["hello"]
