# -*- coding: utf-8 -*-
from selenium.webdriver import Chrome, PhantomJS
from selenium.webdriver.chrome.options import Options
from loguru import logger
import glob
import os
import codecs
import simplejson as json
import yaml
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import unicodedata
import time
from multiprocessing import cpu_count, Pool
from itertools import repeat

opts = Options()

EXECUTABLE_PATH = "./drivers/phantomjs"
# EXECUTABLE_PATH = "./drivers/phantomjs.exe"
# EXECUTABLE_PATH = "./drivers/chromedriver"
COOKIES_PATH = "./cookies/"
CONF_FILE = "./conf/items.yaml"


def create_browser():
    # browser = Chrome(executable_path=EXECUTABLE_PATH, options=opts)
    browser = PhantomJS(executable_path=EXECUTABLE_PATH)
    return browser


def load_cookie(browser: Chrome):
    cookie_files = glob.glob(os.path.join(COOKIES_PATH, '*.cookie'))
    for file in cookie_files:
        with codecs.open(filename=file) as rfile:
            data_cookies = json.load(rfile)
            for data_cookie in data_cookies:
                if data_cookie['domain'][0] != '.':
                    data_cookie['domain'] = '.' + data_cookie['domain']
                browser.add_cookie(data_cookie)


def screen_shot(browser, file_name=None, item_name=None):
    browser.get_screenshot_as_png()
    if not file_name:
        file_name = './images/tmp.png'
    if item_name:
        item_name = unicodedata.normalize('NFC', item_name)
        for ch in ['~', '#', '%', '&', '*', '{', '}', '\\', '<', '>', '?', '/', '`', '\'', '"', '|', '+']:  # escape
            if ch in item_name:
                item_name = item_name.replace(ch, "_")
    browser.save_screenshot("./images/{}_".format(item_name) + file_name)


def is_logged_in(browser: PhantomJS):
    logger.info('Check login.')
    browser.get('https://tiki.vn/sales/order/history/')
    WebDriverWait(driver=browser, timeout=10).until(EC.presence_of_element_located((By.CLASS_NAME, 'profiles')))
    full_name = browser.find_element_by_css_selector('.profiles > h6:nth-child(3)')
    # screen_shot(browser, 'login.png')
    if full_name.text:
        logger.info("You has been login with name : {}".format(full_name.text))
        return True
    else:
        logger.info("Require export cookie for login.")
        return False


def get_price(string):
    result = re.findall(r'\d+', string)
    price = -1
    if result:
        price = int("".join(result))
    return price


def get_item(browser: PhantomJS, item: dict, check_inverter):
    price_expect = get_price(item.get('price'))
    max_retry = 60
    retry = 0
    while retry < max_retry:
        retry += 1

        browser.get(item.get('url'))
        browser.refresh()
        WebDriverWait(driver=browser, timeout=10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#product-name')))
        item_title = browser.find_element_by_css_selector('#product-name')
        item_name = item_title.text

        item_price = browser.find_element_by_css_selector('#span-price')
        logger.info("{} -> {}".format(item_price.text, item_name))
        price_seller = get_price(item_price.text)
        screen_shot(browser=browser, file_name='buy.png', item_name=item_name)
        if price_seller > 0 and price_seller <= price_expect:
            browser.find_element_by_css_selector('#\#mainAddToCart').click()
            logger.info("Add cart : {} < {} ,{}".format(price_seller, price_expect, item_name))
            return item_name
        else:
            logger.info("Retry : {}. {}".format(retry, item_title.text))
            time.sleep(check_inverter)


def check_out(browser: PhantomJS, item_name):
    logger.info('Checkout : {}'.format(item_name))
    browser.get('https://tiki.vn/checkout/cart')
    WebDriverWait(driver=browser, timeout=10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.btn-large')))
    screen_shot(browser, 'checkout.png', item_name=item_name)
    browser.find_element_by_css_selector('.btn-large').click()


def shipping(browser: PhantomJS, item_name):
    logger.info('Shipping : {}'.format(item_name))
    WebDriverWait(driver=browser, timeout=10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.is-blue')))
    screen_shot(browser, 'shipping.png', item_name=item_name)
    browser.find_element_by_css_selector('.is-blue').click()
    screen_shot(browser, 'shipping.png', item_name=item_name)


def payment(browser: PhantomJS, item_name):
    logger.info('Payment : {}'.format(item_name))
    WebDriverWait(driver=browser, timeout=10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#btn-placeorder')))
    browser.find_element_by_css_selector(
        '.method_payment_cod > div:nth-child(1) > label:nth-child(1) > div:nth-child(1) > ins:nth-child(2)').click()
    browser.find_element_by_css_selector('#btn-placeorder').click()
    screen_shot(browser, 'payment.png', item_name=item_name)


def run_process(item, check_inverter):
    logger.debug(item)
    browser = create_browser()
    # logger.debug(item)

    try:
        load_cookie(browser=browser)
        if is_logged_in(browser=browser):
            while 1:
                item_name = get_item(browser=browser, item=item, check_inverter=check_inverter)
                if item_name:
                    # logger.debug(item_name)
                    check_out(browser, item_name)
                    shipping(browser, item_name)
                    payment(browser, item_name)
                    break
                else:
                    logger.info("ahihi , eo mua dc :v")

    except Exception as ex:
        screen_shot(browser, 'exception.png')
        browser.close()


def main():
    logger.info("Run")
    conf = load_conf()
    items = conf['items']
    check_inverter = conf['check_inverter']

    with Pool(cpu_count() - 1) as p:
        p.starmap(run_process, zip(items, repeat(check_inverter)), 1)
    p.close()
    p.join()


def load_conf():
    logger.info("Load items need buy.")
    with codecs.open(CONF_FILE, 'r') as rfile:
        conf = yaml.load(rfile)
        return conf


if __name__ == '__main__':
    main()