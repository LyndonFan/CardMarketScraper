import pandas as pd

def summarize(fname: str) -> None:
    df = pd.read_csv(fname)
    print(f"{df['name'].nunique()} unique cards")
    print(f"{df['seller_name'].nunique()} unique sellers")
    print(f"{len(df)} total offers")
    df["price"] = df["price"].str.replace("\n","").str.replace(" €.*$", "", regex=True)
    df["price"] = df["price"].str.replace(",",".").astype(float)
    sellers_summary = df.groupby(["seller_name"])["name"].agg(["count", "nunique", set])
    sellers_summary = sellers_summary.reset_index()
    sellers_summary = sellers_summary.sort_values(by="nunique", ascending=False)
    print("Summary of Sellers")
    print(sellers_summary.head(10))
    sellers_summary.to_csv("summary_sellers.csv", index=False)
    card_summary_vals = []
    for gp, _df in df.groupby(["name"]):
        cname = gp[0]
        num_sellers = len(_df)
        mean_price = _df["price"].mean()
        min_price = _df["price"].min()
        q1_price = _df["price"].quantile(0.25)
        median_price = _df["price"].median()
        q3_price = _df["price"].quantile(0.75)
        vals = [
            cname, num_sellers, mean_price,
            min_price, q1_price, median_price, q3_price
        ]
        card_summary_vals.append(vals)
    cols = ["name", "num_sellers", "avg_price", "min_price", "q1_price", "median_price", "q3_price"]
    card_summary = pd.DataFrame(card_summary_vals, columns=cols)
    print(card_summary)
    card_summary.to_csv("card_summary.csv", index=False)

if __name__ == "__main__":
    import sys
    fname = sys.argv[1]
    summarize(fname)