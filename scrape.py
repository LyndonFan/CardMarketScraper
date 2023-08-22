import re
import pandas as pd
import time
from typing import Union, List, Dict

from urllib.parse import urljoin, quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://www.cardmarket.com/en/Magic/Cards"


def get_driver():
    return webdriver.Chrome(service=Service())


def startup(driver: webdriver.Chrome):
    driver.get(URL)
    accept_xpath = "//button[contains(text(),'Accept All Cookies')]"
    timeout = 7
    try:
        elem_present = EC.presence_of_element_located((By.XPATH, accept_xpath))
        elem = WebDriverWait(driver, timeout).until(elem_present)
        elem.click()
    except TimeoutException:
        print("Timed out waiting for page to load")
    except NoSuchElementException:
        print("No such element found, ignore cookie comment")
    time.sleep(1)


def search(driver: webdriver.Chrome, card_name: str) -> str:
    name = card_name.replace("'", "").replace('"', "")
    # if has ", " and "-", then replace ", " and " " with "-"
    # if has "-" but no ", ", replace "-" with " " and " " with "-"
    # if has ", " but no "-", then replace ", " and " " with "-"
    # otherwise replace " " with "-"
    if ", " in name:
        name = name.replace(", ","-")
    elif "-" in name:
        name = name.replace("-","")
    name = name.replace(" ","-")
    return URL + "/" + quote_plus(name, safe="")


def get_results(driver: webdriver.Chrome, product_url: str) -> List:
    SUFFIX = "?sellerCountry=13&sellerReputation=4"
    url = product_url + SUFFIX
    driver.get(url)
    time.sleep(1)

    table_path = "//div[contains(@class, 'table-striped')]"
    # rows = driver.find_elements(By.CLASS_NAME, "article-row")
    sellers = driver.find_elements(
        By.XPATH, table_path + "//a[contains(@href, 'Magic/Users/')]"
    )
    print(f"Found {len(sellers)} sellers")
    if not sellers:
        return []
    expansion_symbols = driver.find_elements(
        By.XPATH, table_path + "//a[contains(@class, 'expansion-symbol')]"
    )
    offer_rows = driver.find_elements(
        By.XPATH, table_path + "//div[contains(@class, 'article-row')]"
    )
    prices = driver.find_elements(
        By.XPATH, table_path + "//div[contains(@class, 'price-container')]"
    )
    offers = driver.find_elements(
        By.XPATH,
        table_path
        + "//div[contains(@class, 'col-offer')]//div[contains(@class, 'amount-container')]",
    )
    res = []
    for row, seller, sym, price, offer in zip(
        offer_rows, sellers, expansion_symbols, prices, offers
    ):
        res_dict = {"offer_link": driver.current_url}
        if not seller.text:
            print(f"{seller} at {seller.location} doesn't have a name(?), skipping")
            continue
        res_dict["article_id"] = row.get_attribute("id")
        res_dict["seller_name"] = seller.text
        res_dict["seller_link"] = seller.get_attribute("href")
        try:
            res_dict["price"] = price.text
        except:
            print(f"Unable to find price of product, skipping")
            continue
        try:
            res_dict["expansion"] = sym.get_attribute("data-original-title")
        except Exception:
            pass
        try:
            res_dict["offer"] = offer.text
        except Exception:
            pass
        res.append(res_dict)
    return res


def scrape_info(names: List[str]) -> Dict[str, List[Dict[str, str]]]:
    driver = get_driver()
    startup(driver)
    full_dict = {}
    for name in names:
        try:
            print(f"Start crawling for {name}")
            card_url = search(driver, name)
            print(f"Computed url to be {card_url}")
            info = get_results(driver, card_url)
            full_dict[name] = info
        except Exception as e:
            print(f"Something went quite wrong when searching for {name}")
            print(e)
            print("Skipping...")
            continue
    driver.close()
    return full_dict


def main(input_df: pd.DataFrame) -> pd.DataFrame:
    names = input_df["name"].tolist()
    res_full_dict = scrape_info(names)
    df_rows = []
    for k, vs in res_full_dict.items():
        new_vs = [{**v, "name": k} for v in vs]
        df_rows.extend(new_vs)
    df = pd.DataFrame(df_rows)
    return df


if __name__ == "__main__":
    import sys

    fname = sys.argv[1]
    input_df = pd.read_csv(fname)
    res_df = main(input_df)
    res_df.to_csv("data_raw.csv", index=False)
