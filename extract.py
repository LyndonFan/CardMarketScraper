import re
import pandas as pd


def extract(filename: str) -> pd.DataFrame:
    with open(filename) as f:
        lines = f.read()
    lines = lines.strip().split("\n")
    row_pat = re.compile("^([1-9]\d*) ([^\(\)]+)( \(.*\) \d+[a-z]?)?$")
    names = []
    cannot_find = []
    for l in lines:
        search = row_pat.search(l)
        if not search:
            cannot_find.append(l)
            continue
        names.append([search.group(1), search.group(2)])
    print(f"Found {len(names)} names")
    if cannot_find:
        print("Unable to find cards from these lines")
        print("\n".join(cannot_find))
    inp = input("Are you okay with the above? (y/n) ")
    while not inp and inp[0].lower() not in "yn":
        inp = input(f"Unable to recognised {inp}. Please enter y/n. ")
    if inp[0].lower() == "n":
        print("Okay, please edit the file.")
        return pd.DataFrame()
    return pd.DataFrame(names, columns=["quantity", "name"])


if __name__ == "__main__":
    import sys

    res = extract(sys.argv[1])
    if not res.empty:
        res.to_csv('wishlist.csv', index=False)
