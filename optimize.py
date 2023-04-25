import mip
import pandas as pd
from typing import List

SHIPPING_COST = 1.10
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
    df = df[["seller_name", "name", "price"]]
    df.columns = ["seller", "card", "price"]
    df["price"] = df["price"].str.replace("\n","").str.replace(" €.*$", "", regex=True)
    df["price"] = df["price"].str.replace(",",".").astype(float)
    df = df.groupby(["seller", "card"])["price"].min().reset_index()
    sellers_vc = df["seller"].value_counts()
    repeated_sellers = sellers_vc[sellers_vc>1].index
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
    seller_lookup = {x: i for i,x in enumerate(sellers)}
    cards = df["card"].unique().tolist()
    card_lookup = {c: i for i,c in enumerate(cards)}
    df["seller"] = df["seller"].map(seller_lookup.get).astype("int32")
    df["card"] = df["card"].map(card_lookup.get).astype("int32")
    df.index.name = "offer_number"
    df = df.reset_index()
    return df, sellers, cards

def create_model(df: pd.DataFrame) -> mip.Model:
    n_sellers = df["seller"].max()+1
    n_offers = len(df)

    m = mip.Model("MKM Optimizer")
    xs = [
        m.add_var(f"offer_{i:03}", var_type=mip.BINARY)
        for i in range(n_offers)
    ]
    ys = [
        m.add_var(f"seller_{i:03}", var_type=mip.BINARY)
        for i in range(n_sellers)
    ]

    costs = df["price"].tolist()
    costs += [SHIPPING_COST] * n_sellers
    objective_vals = [x*p for x,p in zip(xs, df["price"])]
    objective_vals += [y*SHIPPING_COST for y in ys]

    m.objective = mip.xsum(objective_vals)
    for _, row in df.iterrows():
        m += xs[int(row["offer_number"])] <= ys[int(row["seller"])]

    card_constraints = df.groupby("card")["offer_number"].agg(list).reset_index()
    for _, row in card_constraints.iterrows():
        m += mip.xsum([xs[i] for i in row['offer_number']]) >= 1
    
    return m

def solve(m: mip.Model) -> mip.Model:
    m.max_gap = 2
    status = m.optimize(max_seconds=300)
    if status == mip.OptimizationStatus.OPTIMAL:
        print('optimal solution cost {} found'.format(m.objective_value))
    elif status == mip.OptimizationStatus.FEASIBLE:
        print('sol.cost {} found, best possible: {}'.format(m.objective_value, m.objective_bound))
    elif status == mip.OptimizationStatus.NO_SOLUTION_FOUND:
        print('no feasible solution found, lower bound is: {}'.format(m.objective_bound))
    if status == mip.OptimizationStatus.OPTIMAL or status == mip.OptimizationStatus.FEASIBLE:
        print('solution:')
        for v in m.vars:
            if abs(v.x) > ZERO_TOL: # only printing non-zeros
                print('{} : {}'.format(v.name, v.x))
    return m

def decode(m: mip.Model, df: pd.DataFrame, sellers: List[str], cards: List[str]) -> None:
    keep_offers = [
        v.name for v in m.vars
        if 'offer' in v.name and v.x >= 1-ZERO_TOL
    ]
    offer_rows = [int(s.split('_')[1]) for s in keep_offers]
    decoded_df = df.copy()
    sellers_dict = {i:v for i,v in enumerate(sellers)}
    cards_dict = {i:v for i,v in enumerate(cards)}
    decoded_df["seller"] = decoded_df["seller"].map(sellers_dict.get)
    decoded_df["card"] = decoded_df["card"].map(cards_dict.get)
    print(decoded_df[decoded_df["offer_number"].isin(offer_rows)])

def main(df: pd.DataFrame):
    df, sellers, cards = preprocess(df)
    model = create_model(df)
    print(model, type(model))
    model.write("model_unsolved.lp")
    model = solve(model)
    model.write("model_solved.lp")
    decode(model, df, sellers, cards)



if __name__ == "__main__":
    import sys
    fname = sys.argv[1]
    df = pd.read_csv(fname)
    main(df)

