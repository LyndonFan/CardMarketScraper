import mip
import pandas as pd
from typing import List, Dict

# TODO: make this dynamic?
# for now it's basic UK to UK postage cost
# i.e. royal mail 2nd class
# could be changed if may hit higher tier of weight
SHIPPING_COST = 1.19
# max time (seconds) the optimizer can take
MAX_SOLVE_TIME = 300
# probably not needed?
ZERO_TOL = 1e-5


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Picks the cheapest offer per seller per card,
    and for sellers who don't sell more than a card,
    pick the cheapest offer per card.

    Args:
        df (pd.DataFrame)
    Returns:
        pd.DataFrame
    """
    df = df.rename(columns={"seller_name": "seller", "name": "card"})
    link_lookup = df["seller_link"].to_dict()
    df = df.groupby(["seller", "card"])["price"].min().reset_index()
    sellers_vc = df["seller"].value_counts()
    repeated_sellers = sellers_vc[sellers_vc > 1].index
    seller_is_repeated = df["seller"].isin(repeated_sellers)
    repeated_df = df[seller_is_repeated].copy()
    unique_df = df[~seller_is_repeated].copy()
    unique_df = unique_df.sort_values(by="price", ascending=True)
    unique_df = unique_df.drop_duplicates(subset=["card"], keep="first")
    df = pd.concat([repeated_df, unique_df], ignore_index=True)
    print(
        "After preprocessing, we have "
        f"{df['seller'].nunique()} sellers and {len(df)} offers"
    )
    sellers = df["seller"].unique().tolist()
    seller_lookup = {x: i for i, x in enumerate(sellers)}
    cards = df["card"].unique().tolist()
    card_lookup = {c: i for i, c in enumerate(cards)}
    df["seller"] = df["seller"].map(seller_lookup.get).astype("int32")
    df["card"] = df["card"].map(card_lookup.get).astype("int32")
    df.index.name = "offer_number"
    df = df[["seller", "card", "price"]].reset_index()
    return df, sellers, cards, link_lookup


def create_model(df: pd.DataFrame) -> mip.Model:
    n_sellers = df["seller"].max() + 1
    n_offers = len(df)

    m = mip.Model("MKM Optimizer")
    xs = [m.add_var(f"offer_{i:03}", var_type=mip.BINARY) for i in range(n_offers)]
    ys = [m.add_var(f"seller_{i:03}", var_type=mip.BINARY) for i in range(n_sellers)]

    costs = df["price"].tolist()
    costs += [SHIPPING_COST] * n_sellers
    objective_vals = [x * p for x, p in zip(xs, df["price"])]
    objective_vals += [y * SHIPPING_COST for y in ys]

    m.objective = mip.xsum(objective_vals)
    for _, row in df.iterrows():
        # not choose seller -> can't choose corresponding offer
        m += xs[int(row["offer_number"])] <= ys[int(row["seller"])]

    card_constraints = df.groupby("card")["offer_number"].agg(list).reset_index()
    for _, row in card_constraints.iterrows():
        # must buy >=1 copy of that card
        # (constraint would be tight anyways, left as >= for convenience)
        m += mip.xsum([xs[i] for i in row["offer_number"]]) >= 1

    return m


def solve(m: mip.Model) -> mip.Model:
    # erm not really sure what this is, copied from quickstart page
    # maybe max allowed diff from current value to theoretical minimum?
    m.max_gap = 2

    status = m.optimize(max_seconds=MAX_SOLVE_TIME)
    if status == mip.OptimizationStatus.OPTIMAL:
        print(f"Minimal cost {m.objective_value:.02} found")
    elif status == mip.OptimizationStatus.FEASIBLE:
        print(f"Sol cost {m.objective_value} found, best possible: {m.objective_bound}")
    elif status == mip.OptimizationStatus.NO_SOLUTION_FOUND:
        print(f"No feasible solution found, lower bound is: {m.objective_bound}")
    return m


def decode_results(
    m: mip.Model,
    df: pd.DataFrame,
    sellers: List[str],
    cards: List[str],
    link_lookup: Dict[int, str],
) -> pd.DataFrame:
    keep_offers = [v.name for v in m.vars if "offer" in v.name and v.x >= 1 - ZERO_TOL]
    offer_rows = [int(s.split("_")[1]) for s in keep_offers]
    decoded_df = df.copy()
    sellers_dict = {i: v for i, v in enumerate(sellers)}
    cards_dict = {i: v for i, v in enumerate(cards)}
    res = decoded_df[decoded_df["offer_number"].isin(offer_rows)]
    res["seller"] = res["seller"].map(sellers_dict.get)
    res["card"] = res["card"].map(cards_dict.get)
    res["seller_link"] = res["offer_number"].map(link_lookup.get)
    return res


def main(df: pd.DataFrame):
    df, sellers, cards, link_lookup = preprocess(df)
    model = create_model(df)
    print(model, type(model))
    model.write("model_unsolved.lp")
    model = solve(model)
    model.write("model_solved.lp")
    res = decode_results(model, df, sellers, cards, link_lookup)
    res.to_csv("buylist.csv", index=False)


if __name__ == "__main__":
    import sys

    fname = sys.argv[1]
    df = pd.read_csv(fname)
    main(df)
