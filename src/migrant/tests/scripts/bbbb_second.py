def up(db):
    db.data["value"] = "b"


def down(db):
    db.data["value"] = "a"
