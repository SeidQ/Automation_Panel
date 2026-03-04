from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support import expected_conditions as EC
import pytest
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

@pytest.fixture

def driver(request):
    service = Service(executable_path=r"C:\Users\sgaziyev\Desktop\chromedriver-win64\chromedriver.exe")
    options = webdriver.ChromeOptions()
    wd = webdriver.Chrome(service=service, options=options)
    wd.maximize_window()
    wd.implicitly_wait(120)
    yield wd
    wd.quit()

def test_contract_creation(driver):
    driver.get("https://dealer-online.azercell.com/login")
    wait = WebDriverWait(driver, 30)

    # ===== TEST DATA =====
    USERNAME = "ccequlamova"
    PASSWORD = "dealeronline"

    PLAN_TYPE = "postpaid"  # prepaid / postpaid
    TARIFF_TYPE = "flat"  # flat / la

    MSISDN = "102989151"
    SIMCARD = "2411010161241"

    DOC_NUMBER = "50000100"
    DOC_PIN = "9A4X4RM"

    # Login
    username_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    username_input.send_keys(USERNAME)

    password_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "password"))
    )
    password_input.send_keys(PASSWORD, Keys.ENTER)

    # Click Contract
    kontrakt = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Kontrakt']"))
    )
    kontrakt.click()

    # Select prepaid / postpaid
    plan = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, f"//input[@value='{PLAN_TYPE}']"))
    )
    plan.click()

    # Select flat / la
    tariff = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, f"//input[@value='{TARIFF_TYPE}']"))
    )
    tariff.click()

    # MSISDN
    msisdn_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_check_mhm_msisdn"))
    )
    msisdn_input.send_keys(MSISDN)

    # SIMCARD
    simcard_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_check_mhm_simcard"))
    )
    simcard_input.send_keys(SIMCARD)

    # eSIM toggle (stabil JS click)
    esim_toggle = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='primaryEsimCheckbox']//span[@class='switch-selector']"))
    )
    driver.execute_script("arguments[0].click();", esim_toggle)

    # Document Number
    doc_number_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_check_mhm_DocumentNumber"))
    )
    doc_number_input.send_keys(DOC_NUMBER)

    # Document PIN
    doc_pin_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_check_mhm_DocumentPin"))
    )
    doc_pin_input.send_keys(DOC_PIN)

    # Info Check
    info_check = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "customer_check_mhm_action"))
    )
    info_check.click()

    # Select
    tariff_dropdown = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "services_input_tariff"))
    )

    Select(tariff_dropdown).select_by_value("371")  # Yeni Her Yere
    # Continue

    continue_btn = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "btnGoToContract"))
    )
    continue_btn.click()

    # City
    city_dropdown = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "customer_data_city"))
    )
    Select(city_dropdown).select_by_value("Bakı")

    # ZIP
    zip_dropdown = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "customer_data_zip"))
    )
    Select(zip_dropdown).select_by_value("AZC1122")

    # Email
    email_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_data_email"))
    )
    email_input.send_keys("ccequlamova@azercell.com")

    # Prefix
    prefix_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_data_phone_1_prefix"))
    )
    prefix_input.send_keys("50")

    # Phone number
    phone_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "customer_data_phone_1_number"))
    )
    phone_input.send_keys("2310848")

    # Importer
    importer_dropdown = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "customer_data_importer"))
    )
    Select(importer_dropdown).select_by_value("AZERCELL")

    # Curator
    curator_dropdown = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "customer_data_curator"))
    )
    Select(curator_dropdown).select_by_value("ABUZERLI")

    time.sleep(20)