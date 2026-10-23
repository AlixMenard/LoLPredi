import os

def func1():
    files = ["match_records/"+f for f in os.listdir("match_records")]
    names = set()
    replaces = {}

    for file in files:
        with open(file, "r", encoding="utf8") as f:
            t = f.read()

        lines = [l.strip() for l in t.split("\n")]
        for line in lines:
            sides = line.split(";")
            for side in sides:
                names.add(side.split(",")[0])

    names = sorted(list(names))
    for name in names:
        if "(" in name:
            print(name)
            i = name.index("(")
            while name[i-1] == " ":
                i -= 1
            replaces[name] = name[:i]
        

    for file in files:
        with open(file, "r", encoding="utf8") as f:
            t = f.read()

        for r in replaces:
            t = t.replace(r, replaces[r])

        with open(file, "w", encoding="utf8") as f:
                f.write(t)

def func2():
    files = ["match_records/"+f for f in os.listdir("match_records")]

    for file in files:
        with open(file, "r", encoding="utf8") as f:
            t = f.read()

        lines = [l.strip() for l in t.split("\n")]
        new_lines = []
        for line in lines:
            if "Los Ratones" in line or "Karmine Corp Blue" in line:
                continue
            new_lines.append(line)

        text = "\n".join(new_lines)

        with open(file, "w", encoding="utf8") as f:
            f.write(text)

def renames():
    files = ["match_records/"+f for f in os.listdir("match_records")]

    renames = {
        "AG.AL" : "Anyone's Legend",
        "Dplus KIA": "Dplus Kia",
        "MIBR.LOS": "LØS"
    }

    for file in files:
        with open(file, "r", encoding="utf8") as f:
            t = f.read()

        for key, value in renames.items():
            t = t.replace(key, value)

        with open(file, "w", encoding="utf8") as f:
            f.write(t)

def get_last_names():
    file = "match_records/" + os.listdir("match_records")[-1]

    with open(file, "r") as f:
        text = f.read()

    lines = [l.strip() for l in text.split("\n")]
    names = set()

    for line in lines:
        sides = line.split(";")
        for side in sides:
            name = side.split(",")[0]
            names.add(name)

    return names