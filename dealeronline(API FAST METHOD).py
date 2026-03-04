import requests
import threading
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

# ==================== TEST DATA ====================
TEST_DATA = [
    {
        "MSISDN": "102989153",
        "SIMCARD": "2411010160896",
        "DOC_NUMBER": "AA0877974",
        "DOC_PIN": "70HF8GF",
        "TARIFF": "371",
        "PLAN_TYPE": "PostPaid", #PostPaid/Prepaid
        "PLAN_TYPE_REG": "PostPaid",
        "TARIFF_TYPE": "flat"   #flat(Fiziki şəxslər) #lat(Hüquqi şəxslər)
    },
    {
        "MSISDN": "102989141",
        "SIMCARD": "2411010161241",
        "DOC_NUMBER": "AA3386081",
        "DOC_PIN": "7K51ES1",
        "TARIFF": "371",
        "PLAN_TYPE": "Postpaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989142",
        "SIMCARD": "2411010161242",
        "DOC_NUMBER": "AA3386082",
        "DOC_PIN": "7K51ES2",
        "TARIFF": "371",
        "PLAN_TYPE": "Prepaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989143",
        "SIMCARD": "2411010161243",
        "DOC_NUMBER": "AA3386083",
        "DOC_PIN": "7K51ES3",
        "TARIFF": "371",
        "PLAN_TYPE": "Postpaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989144",
        "SIMCARD": "2411010161244",
        "DOC_NUMBER": "AA3386084",
        "DOC_PIN": "7K51ES4",
        "TARIFF": "371",
        "PLAN_TYPE": "Prepaid",
        "TARIFF_TYPE": "flat"
    },
    {
        "MSISDN": "102989145",
        "SIMCARD": "2411010161245",
        "DOC_NUMBER": "AA3386085",
        "DOC_PIN": "7K51ES5",
        "TARIFF": "371",
        "PLAN_TYPE": "Postpaid",
        "TARIFF_TYPE": "flat"
    },
]

# ==================== CONSTANTS ====================
USERNAME = "ccequlamova"
PASSWORD = "dealeronline"
BASE_URL = "https://dealer-online.azercell.com"

CITY = "Bak@012@"
ZIP_CODE = "AZC1122"
IMPORTER = "AZERCELL"
CURATOR = "TEST"
COUNTRY = "AZERBAIJAN"
NATIONALITY = "AZERBAIJAN"
PHONE_1_PREFIX = "10"
PHONE_1_NUMBER = "2210462"
EMAIL = "sgaziyev@azercell.com"

RESULTS = []
_lock = threading.Lock()


# ==================== LOGIN + CSRF ====================
def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest"
    })

    session.post(
        f"{BASE_URL}/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"{BASE_URL}/login",
            "Origin": BASE_URL
        },
        allow_redirects=True
    )

    session_cookie = session.cookies.get("SESSION")
    if not session_cookie:
        raise Exception("Login uğursuz - SESSION cookie yoxdur")
    logger.info(f"✅ Login uğurlu - SESSION: {session_cookie[:20]}...")

    customer_page = session.get(
        f"{BASE_URL}/customer",
        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    )

    csrf_token = _extract_csrf(customer_page.text)
    if not csrf_token:
       
        csrf_token = session.cookies.get("XSRF-TOKEN")

    if not csrf_token:
        raise Exception("CSRF token alınmadı")

    session.headers.update({"X-CSRF-TOKEN": csrf_token})
    logger.info(f"✅ CSRF token alındı: {csrf_token[:20]}...")

    return session


def _extract_csrf(html: str) -> str:
    import re

    match = re.search(r'<meta[^>]*name=["\']_csrf["\'][^>]*content=["\'](.*?)["\']', html)
    if match:
        return match.group(1)

    match = re.search(r'<input[^>]*name=["\']_csrf["\'][^>]*value=["\'](.*?)["\']', html)
    if match:
        return match.group(1)

    match = re.search(r'["\']X-CSRF-TOKEN["\']\s*:\s*["\'](.*?)["\']', html)
    if match:
        return match.group(1)
    return None


# ==================== CHECK MHM ====================
def check_mhm(session, data):
    params = {
        "documentType": "1",
        "documentNumber": data["DOC_NUMBER"],
        "msisdn": data["MSISDN"],
        "simcard": data["SIMCARD"],
        "customerType": data["PLAN_TYPE"],
        "companyVoen": "null",
        "documentPin": data["DOC_PIN"],
        "requestType": data["TARIFF_TYPE"],
        "companySun": "",
        "segmentType": ""
    }

    resp = session.get(
        f"{BASE_URL}/customer/checkMHM",
        params=params,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{BASE_URL}/customer",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
    )

    logger.info(f"checkMHM [{data['MSISDN']}] → HTTP {resp.status_code} | {resp.text}")

    if resp.status_code != 200:
        raise Exception(f"checkMHM failed: {resp.text}")

    return resp.json()


# ==================== REGISTER CUSTOMER ====================
def register_customer(session, data):
    params = {
        "country": COUNTRY,
        "city": CITY,
        "zip": ZIP_CODE,
        "tariff": data["TARIFF"],
        "imei": "",
        "msisdnDeviceType": "voice",
        "email": EMAIL,
        "additionalAddress": "",
        "additionalCity": "",
        "additional": "true",
        "nationality": NATIONALITY,
        "phone_1_prefix": PHONE_1_PREFIX,
        "phone_1_number": PHONE_1_NUMBER,
        "phone_2_prefix": "",
        "phone_2_number": "",
        "fax_prefix": "",
        "fax_number": "",
        "importer": IMPORTER,
        "curator": CURATOR,
        "foreign_day": "",
        "foreign_month": "",
        "foreign_year": "",
        "documentType": "1",
        "documentNumber": data["DOC_NUMBER"],
        "documentSeries": "",
        "msisdn": data["MSISDN"],
        "simcard": data["SIMCARD"],
        "customerType": data["PLAN_TYPE_REG"],
        "companyVoen": "null",
        "documentPin": data["DOC_PIN"],
        "requestType": data["TARIFF_TYPE"],
        "companySun": "",
        "campaign": "0",
        "shouldOpenIntLine": "false",
        "shouldBlockAds": "false",
        "shouldRefuseVHF": "false",
        "street": "",
        "segmentType": ""
    }

    resp = session.get(
        f"{BASE_URL}/customer/registerCustomer",
        params=params,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{BASE_URL}/customer",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
    )

    logger.info(f"registerCustomer [{data['MSISDN']}] → HTTP {resp.status_code} | {resp.text}")

    if resp.status_code != 200:
        raise Exception(f"registerCustomer failed: {resp.text}")

    return resp.json()


# ==================== INFO ====================
def run_contract(data):
    logger.info(f"===== START: MSISDN {data['MSISDN']} =====")

    try:
        # 1. Login + CSRF
        session = create_session()

        # 2. checkMHM
        check_result = check_mhm(session, data)
        logger.info(f"checkMHM OK: {check_result}")

        # 3. registerCustomer
        reg_result = register_customer(session, data)
        logger.info(f"registerCustomer OK: {reg_result}")

        with _lock:
            RESULTS.append({
                "MSISDN": data["MSISDN"],
                "PLAN_TYPE": data["PLAN_TYPE"],
                "TARIFF_TYPE": data["TARIFF_TYPE"],
                "STATUS": "✅ PASSED",
                "ERROR": ""
            })

    except Exception as e:
        with _lock:
            RESULTS.append({
                "MSISDN": data["MSISDN"],
                "PLAN_TYPE": data["PLAN_TYPE"],
                "TARIFF_TYPE": data["TARIFF_TYPE"],
                "STATUS": "❌ FAILED",
                "ERROR": str(e)
            })
        logger.error(f"❌ FAILED: {data['MSISDN']} → {e}")


# ==================== MAIN ====================
if __name__ == "__main__":
    threads = [threading.Thread(target=run_contract, args=(d,)) for d in TEST_DATA]
    for t in threads: t.start()
    for t in threads: t.join()

    print("\n" + "=" * 75)
    print("                     📊 TEST SUMMARY")
    print("=" * 75)
    for r in RESULTS:
        print(f"MSISDN      : {r['MSISDN']}")
        print(f"PLAN_TYPE   : {r['PLAN_TYPE']}")
        print(f"TARIFF_TYPE : {r['TARIFF_TYPE']}")
        print(f"STATUS      : {r['STATUS']}")
        if r['ERROR']:
            print(f"ERROR       : {r['ERROR']}")
        print("-" * 75)

    passed = sum(1 for r in RESULTS if "PASSED" in r["STATUS"])
    failed = sum(1 for r in RESULTS if "FAILED" in r["STATUS"])
    print(f"TOTAL: {len(RESULTS)} | ✅ PASSED: {passed} | ❌ FAILED: {failed}")
    print("=" * 75)