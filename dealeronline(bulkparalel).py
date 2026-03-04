from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
import time
import logging
import threading

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
        "PHONE": "2310848",
        "PLAN_TYPE": "postpaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989152",
        "SIMCARD": "2411010161242",
        "DOC_NUMBER": "50000101",
        "DOC_PIN": "8B3Y3QN",
        "TARIFF": "372",
        "EMAIL": "test2@azercell.com",
        "PREFIX": "51",
        "PHONE": "2310849",
        "PLAN_TYPE": "prepaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989153",
        "SIMCARD": "2411010161243",
        "DOC_NUMBER": "50000102",
        "DOC_PIN": "7C2Z2PM",
        "TARIFF": "373",
        "EMAIL": "test3@azercell.com",
        "PREFIX": "55",
        "PHONE": "2310850",
        "PLAN_TYPE": "postpaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989154",
        "SIMCARD": "2411010161244",
        "DOC_NUMBER": "50000103",
        "DOC_PIN": "6D1W1LK",
        "TARIFF": "374",
        "EMAIL": "test4@azercell.com",
        "PREFIX": "70",
        "PHONE": "2310851",
        "PLAN_TYPE": "prepaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989155",
        "SIMCARD": "2411010161245",
        "DOC_NUMBER": "50000104",
        "DOC_PIN": "5E0V0KJ",
        "TARIFF": "375",
        "EMAIL": "test5@azercell.com",
        "PREFIX": "77",
        "PHONE": "2310852",
        "PLAN_TYPE": "postpaid",
        "TARIFF_TYPE": "flat"
    },
]

# ==================== CONSTANTS ====================
USERNAME = "ccequlamova"
PASSWORD = "dealeronline"
CITY = "Bakı"
ZIP_CODE = "AZC1122"
IMPORTER = "AZERCELL"
CURATOR = "ABUZERLI"

CHROMEDRIVER_PATH = r"C:\Users\sgaziyev\Desktop\chromedriver-win64\chromedriver.exe"

# ==================== THREAD-SAFE RESULTS ====================
RESULTS = []
_lock = threading.Lock()


# ==================== CORE FUNCTION ====================
def run_contract(data):
    logger.info(f"========== THREAD START: MSISDN {data['MSISDN']} ==========")

    service = Service(executable_path=CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 30)

    try:
        # ---------- LOGIN ----------
        driver.get("https://dealer-online.azercell.com/login")

        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(PASSWORD, Keys.ENTER)

        time.sleep(5)
        driver.refresh()
        time.sleep(1)

        # ---------- CONTRACT PAGE ----------
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Kontrakt']"))).click()
        time.sleep(1)

        # ---------- PLAN TYPE (test data-dan oxunur) ----------
        wait.until(EC.element_to_be_clickable((By.XPATH, f"//input[@value='{data['PLAN_TYPE']}']"))).click()
        time.sleep(1)

        # ---------- TARIFF TYPE (test data-dan oxunur) ----------
        wait.until(EC.element_to_be_clickable((By.XPATH, f"//input[@value='{data['TARIFF_TYPE']}']"))).click()
        time.sleep(1)

        # ---------- MSISDN & SIMCARD ----------
        wait.until(EC.visibility_of_element_located((By.ID, "customer_check_mhm_msisdn"))).send_keys(data["MSISDN"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located((By.ID, "customer_check_mhm_simcard"))).send_keys(data["SIMCARD"])
        time.sleep(1)

        # ---------- eSIM TOGGLE ----------
        esim = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[@id='primaryEsimCheckbox']//span[@class='switch-selector']")
        ))
        driver.execute_script("arguments[0].click();", esim)
        time.sleep(1)

        # ---------- DOCUMENT ----------
        wait.until(EC.visibility_of_element_located((By.ID, "customer_check_mhm_DocumentNumber"))).send_keys(data["DOC_NUMBER"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located((By.ID, "customer_check_mhm_DocumentPin"))).send_keys(data["DOC_PIN"])
        time.sleep(1)

        # ---------- INFO CHECK ----------
        wait.until(EC.element_to_be_clickable((By.ID, "customer_check_mhm_action"))).click()
        time.sleep(3)

        # ---------- TARIFF DROPDOWN ----------
        tariff_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "services_input_tariff")))
        Select(tariff_dropdown).select_by_value(data["TARIFF"])
        time.sleep(1)

        # ---------- CONTINUE ----------
        wait.until(EC.element_to_be_clickable((By.ID, "btnGoToContract"))).click()
        time.sleep(3)

        # ---------- CUSTOMER DATA ----------
        Select(wait.until(EC.element_to_be_clickable((By.ID, "customer_data_city")))).select_by_value(CITY)
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable((By.ID, "customer_data_zip")))).select_by_value(ZIP_CODE)
        time.sleep(1)

        wait.until(EC.visibility_of_element_located((By.ID, "customer_data_email"))).send_keys(data["EMAIL"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located((By.ID, "customer_data_phone_1_prefix"))).send_keys(data["PREFIX"])
        time.sleep(1)

        wait.until(EC.visibility_of_element_located((By.ID, "customer_data_phone_1_number"))).send_keys(data["PHONE"])
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable((By.ID, "customer_data_importer")))).select_by_value(IMPORTER)
        time.sleep(1)

        Select(wait.until(EC.element_to_be_clickable((By.ID, "customer_data_curator")))).select_by_value(CURATOR)
        time.sleep(2)

        with _lock:
            RESULTS.append({"MSISDN": data["MSISDN"], "PLAN_TYPE": data["PLAN_TYPE"], "TARIFF_TYPE": data["TARIFF_TYPE"], "STATUS": "✅ PASSED", "ERROR": ""})
        logger.info(f"✅ PASSED: MSISDN {data['MSISDN']}")

    except Exception as e:
        with _lock:
            RESULTS.append({"MSISDN": data["MSISDN"], "PLAN_TYPE": data["PLAN_TYPE"], "TARIFF_TYPE": data["TARIFF_TYPE"], "STATUS": "❌ FAILED", "ERROR": str(e)[:100]})
        logger.error(f"❌ FAILED: MSISDN {data['MSISDN']} - {e}")

    finally:
        driver.quit()


# ==================== MAIN ====================
if __name__ == "__main__":
    threads = []

    for data in TEST_DATA:
        t = threading.Thread(target=run_contract, args=(data,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # ==================== SUMMARY ====================
    print("\n" + "=" * 70)
    print("                        📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in RESULTS if "PASSED" in r["STATUS"])
    failed = sum(1 for r in RESULTS if "FAILED" in r["STATUS"])

    print(f"{'MSISDN':<15} {'PLAN_TYPE':<12} {'TARIFF_TYPE':<14} {'STATUS':<12} {'ERROR'}")
    print("-" * 70)
    for r in RESULTS:
        print(f"{r['MSISDN']:<15} {r['PLAN_TYPE']:<12} {r['TARIFF_TYPE']:<14} {r['STATUS']:<12} {r['ERROR']}")

    print("=" * 70)
    print(f"TOTAL: {len(RESULTS)} | ✅ PASSED: {passed} | ❌ FAILED: {failed}")
    print("=" * 70)