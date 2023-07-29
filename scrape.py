import re
import pandas as pd
import time
from typing import Union, List, Dict

import undetected_chromedriver as uc
from urllib.parse import urljoin, quote_plus
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

URL = "https://www.cardmarket.com/en/Magic/Cards"

def get_driver():
    return uc.Chrome()

def startup(driver: uc.Chrome):
    driver.get(URL)
    time.sleep(7)
    accept_xpath = "//button[contains(text(),'Accept All Cookies')]"
    try:
        elem = driver.find_element(By.XPATH, accept_xpath)
        elem.click()
    except:
        pass
    time.sleep(2)

def search(driver: uc.Chrome, card_name: str) -> str:
    name = card_name.replace(", ","-").replace(" ","-")
    name = name.replace("'","").replace('"',"")
    return URL+"/"+quote_plus(name, safe="")

    # old approach of going to products page and finding corr element
    # if '"' in name:
    #     elem_xpath = f"//a[text()='{name}']"
    # else:
    #     elem_xpath = f'//a[text()="{name}"]'
    # elem = driver.find_element(By.XPATH, elem_xpath)
    # return elem.get_attributes('href')
    # elem.click()
    # time.sleep(3)

    # old old approach of going through search bar and returning list of urls
    # res_xpath = '/html/body/main/section/div[3]/div[2]//div[1]/a'
    # children = driver.find_elements(By.XPATH, res_xpath)
    # children = [c for c in children if name in c.text]
    # urls = []
    # for c in children:
    #     try:
    #         urls.append(c.get_attribute('href'))
    #     except:
    #         print(f"Unable to get {c} at {c.location}")
    # return urls

def get_results(driver: uc.Chrome, product_url: str) -> List:
    SUFFIX = '?sellerCountry=13&sellerType=1,2'
    url = product_url + SUFFIX
    driver.get(url)
    time.sleep(1)

    table_path = "//div[contains(@class, 'table-striped')]"
    # rows = driver.find_elements(By.CLASS_NAME, "article-row")
    sellers = driver.find_elements(By.XPATH, table_path + "//a[contains(@href, 'Magic/Users/')]")
    print(f"Found {len(sellers)} sellers")
    if not sellers:
        return []
    expansion_symbols = driver.find_elements(By.XPATH, table_path + "//a[contains(@class, 'expansion-symbol')]")
    offer_rows = driver.find_elements(By.XPATH, table_path + "//div[contains(@class, 'article-row')]")
    prices = driver.find_elements(By.XPATH, table_path + "//div[contains(@class, 'price-container')]")
    offers = driver.find_elements(By.XPATH, table_path + "//div[contains(@class, 'col-offer')]//div[contains(@class, 'amount-container')]")
    res = []
    for row, seller, sym, price, offer in zip(offer_rows, sellers, expansion_symbols, prices, offers):
        res_dict = {"offer_link": driver.current_url}
        if not seller.text:
            print(f"{seller} at {seller.location} doesn't have a name(?), skipping")
            continue
        res_dict["article_id"] = row.get_attribute('id')
        res_dict['seller_name'] = seller.text
        res_dict['seller_link'] = seller.get_attribute('href')
        try:
            res_dict['price'] = price.text
        except:
            print(f"Unable to find price of product, skipping")
            continue
        try:
            res_dict['expansion'] = sym.get_attribute('data-original-title')
        except:
            pass
        try:
            res_dict['offer'] = offer.text
        except:
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

def main(filename: str):
    with open(filename) as f:
        lines = f.read()
    lines = lines.strip().split('\n')
    print(lines)
    row_pat = re.compile('^\d+ ([^\(\)]+) \(.*\) \d+$')
    names = []
    for l in lines:
        search = row_pat.search(l)
        if not search:
            print(f"Unable to find card name in {l}")
            continue
        names.append(search.group(1))
    print(names)
    inp = input("Are you okay with the above? (y/n) ")
    while not inp and inp[0].lower() not in 'yn':
        inp = input("Are you okay with the above? (y/n) ")
    if inp[0].lower() == 'n':
        print("Okay, please edit the file.")
        exit()
    print(f"Okay, proceeding with {len(names)} cards")
    res_full_dict = scrape_info(names)
    df_rows = []
    for k, vs in res_full_dict.items():
        new_vs = [
            {**v, 'name': k} for v in vs
        ]
        df_rows.extend(new_vs)
    df = pd.DataFrame(df_rows)
    df.to_csv('data_raw.csv', index=False)

if __name__ == "__main__":
    import sys
    fname = sys.argv[1]
    main(fname)