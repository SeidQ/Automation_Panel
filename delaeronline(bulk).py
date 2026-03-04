from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
import pytest
import time
import logging

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== DYNAMIC TEST DATA ====================
TEST_DATA = [
    {
        "MSISDN": "102989151",
        "SIMCARD": "2411010161241",
        "DOC_NUMBER": "50000100",
        "DOC_PIN": "9A4X4RM",
        "TARIFF": "371",
        "EMAIL": "test1@azercell.com",
        "PREFIX": "50",
        "PHONE": "2310848"
    },
    {
        "MSISDN": "102989152",
        "SIMCARD": "2411010161242",
        "DOC_NUMBER": "50000101",
        "DOC_PIN": "8B3Y3QN",
        "TARIFF": "371",
        "EMAIL": "test2@azercell.com",
        "PREFIX": "50",
        "PHONE": "2310849"
    },
]

# ==================== CONSTANTS ====================
USERNAME = "ccequlamova"
PASSWORD = "dealeronline"
PLAN_TYPE = "postpaid"
TARIFF_TYPE = "flat"
CITY = "Bakı"
ZIP_CODE = "AZC1122"
IMPORTER = "AZERCELL"
CURATOR = "ABUZERLI"

# ==================== RESULTS TRACKER ====================
RESULTS = []


# ==================== FIXTURE ====================
@pytest.fixture
def driver():
    service = Service(executable_path=r"C:\Users\sgaziyev\Desktop\chromedriver-win64\chromedriver.exe")
    options = webdriver.ChromeOptions()
    wd = webdriver.Chrome(service=service, options=options)
    wd.maximize_window()
    yield wd
    wd.quit()


# ==================== TEST ====================
@pytest.mark.parametrize("data", TEST_DATA, ids=[
    f"MSISDN_{d['MSISDN']}" for d in TEST_DATA
])
def test_contract_creation(driver, data):
    """Bulk contract creation test"""

    logger.info(f"========== TEST START: MSISDN {data['MSISDN']} ==========")
    wait = WebDriverWait(driver, 30)

    try:
        # ---------- LOGIN ----------
        driver.get("https://dealer-online.azercell.com/login")

        wait.until(EC.visibility_of_element_located(
            (By.ID, "username")
        )).send_keys(USERNAME)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "password")
        )).send_keys(PASSWORD, Keys.ENTER)

        time.sleep(5)
        driver.refresh()
        time.sleep(1)

        # ---------- CONTRACT PAGE ----------
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[normalize-space()='Kontrakt']")
        )).click()
        time.sleep(1)

        # ---------- PLAN & TARIFF ----------
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//input[@value='{PLAN_TYPE}']")
        )).click()
        time.sleep(1)

        wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//input[@value='{TARIFF_TYPE}']")
        )).click()
        time.sleep(1)

        # ---------- MSISDN & SIMCARD ----------
        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_check_mhm_msisdn")
        )).send_keys(data["MSISDN"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_check_mhm_simcard")
        )).send_keys(data["SIMCARD"])
        time.sleep(1)

        # ---------- eSIM TOGGLE ----------
        esim = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[@id='primaryEsimCheckbox']//span[@class='switch-selector']")
        ))
        driver.execute_script("arguments[0].click();", esim)
        time.sleep(1)

        # ---------- DOCUMENT ----------
        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_check_mhm_DocumentNumber")
        )).send_keys(data["DOC_NUMBER"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_check_mhm_DocumentPin")
        )).send_keys(data["DOC_PIN"])
        time.sleep(1)

        # ---------- INFO CHECK ----------
        wait.until(EC.element_to_be_clickable(
            (By.ID, "customer_check_mhm_action")
        )).click()
        time.sleep(3)

        # ---------- TARIFF DROPDOWN ----------
        tariff_dropdown = wait.until(EC.element_to_be_clickable(
            (By.ID, "services_input_tariff")
        ))
        Select(tariff_dropdown).select_by_value(data["TARIFF"])
        time.sleep(1)

        # ---------- CONTINUE ----------
        wait.until(EC.element_to_be_clickable(
            (By.ID, "btnGoToContract")
        )).click()
        time.sleep(3)

        # ---------- CUSTOMER DATA ----------
        Select(wait.until(EC.element_to_be_clickable(
            (By.ID, "customer_data_city")
        ))).select_by_value(CITY)
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable(
            (By.ID, "customer_data_zip")
        ))).select_by_value(ZIP_CODE)
        time.sleep(1)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_data_email")
        )).send_keys(data["EMAIL"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_data_phone_1_prefix")
        )).send_keys(data["PREFIX"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located(
            (By.ID, "customer_data_phone_1_number")
        )).send_keys(data["PHONE"])
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable(
            (By.ID, "customer_data_importer")
        ))).select_by_value(IMPORTER)
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable(
            (By.ID, "customer_data_curator")
        ))).select_by_value(CURATOR)
        time.sleep(2)

        # ✅ PASSED
        RESULTS.append({"MSISDN": data["MSISDN"], "STATUS": "✅ PASSED", "ERROR": ""})
        logger.info(f"✅ PASSED: MSISDN {data['MSISDN']}")



    except Exception as e:

        RESULTS.append({"MSISDN": data["MSISDN"], "STATUS": "❌ FAILED", "ERROR": str(e)[:100]})

        logger.error(f"❌ FAILED: MSISDN {data['MSISDN']} - {e}")

# ==================== SUMMARY REPORT ====================
def test_zzz_summary():

    print("\n")
    print("=" * 60)
    print("                 📊 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for r in RESULTS:
        print(r)
        if "PASSED" in r:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"TOTAL: {len(RESULTS)} | ✅ PASSED: {passed} | ❌ FAILED: {failed}")
    print("=" * 60)