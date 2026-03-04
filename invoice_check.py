from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support import expected_conditions as EC
import pytest
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pdfplumber
import re
import base64
from io import BytesIO
from bs4 import BeautifulSoup


@pytest.fixture
def driver(request):
    service = Service(executable_path=r"C:\Users\sgaziyev\Desktop\chromedriver-win64\chromedriver.exe")
    options = webdriver.ChromeOptions()
    wd = webdriver.Chrome(service=service, options=options)
    wd.maximize_window()
    wd.implicitly_wait(120)
    yield wd
    wd.quit()


def safe_regex_search(pattern, text, group=1, default="N/A"):
    """Regex axtarışını təhlükəsiz edir"""
    try:
        match = re.search(pattern, text)
        if match:
            return match.group(group).strip()
        return default
    except:
        return default


def extract_amount_from_text(text):
    """Mətn içindən məbləği çıxarır (məs: 'AZN 0.57' -> 0.57)"""
    try:
        match = re.search(r'(?:AZN\s*)?([\d,]+\.?\d*)', text)
        if match:
            amount = match.group(1).replace(',', '')
            return round(float(amount), 2)
        return 0.0
    except:
        return 0.0


def extract_billing_overview_data(html_content):
    """HTML məzmunundan billing overview məlumatlarını çıxarır"""
    soup = BeautifulSoup(html_content, 'html.parser')

    billing_data = {
        'ümumi_məlumat': {},
        'recurring_charges': [],
        'non_recurring_charges': [],
        'usage_charges': [],
        'toplamlar': {}
    }

    # Service Name və MSISDN
    service_name = soup.find('span', class_='serviceNameId')
    msisdn = soup.find('span', class_='inlineExternal_id')

    if service_name:
        billing_data['ümumi_məlumat']['xidmət_növü'] = service_name.text.strip()
    if msisdn:
        billing_data['ümumi_məlumat']['msisdn'] = msisdn.text.strip()

    # Recurring Charges
    recurring_section = soup.find('div', string='Recurring Charges')
    if recurring_section:
        recurring_parent = recurring_section.find_parent('div')
        charges = recurring_parent.find_all('div', class_='chargeAtBillBreakDown')

        for charge in charges:
            desc = charge.find('span', class_='detail_desc')
            amount_span = charge.find('span', class_='detail_sum')
            vat_span = charge.find('span', class_='tax_desc')

            if desc and amount_span:
                amount_text = amount_span.get_text(strip=True)
                vat_text = vat_span.get_text(strip=True) if vat_span else ''

                cost = extract_amount_from_text(amount_text)
                vat = extract_amount_from_text(vat_text)

                charge_info = {
                    'təsvir': desc.text.strip(),
                    'məbləğ_text': amount_text,
                    'məbləğ': cost,
                    'vat_text': vat_text,
                    'vat': vat,
                    'toplam': round(cost + vat, 2)
                }
                billing_data['recurring_charges'].append(charge_info)

    # Non Recurring Charges
    non_recurring_section = soup.find('div', string='Non Recurring Charges')
    if non_recurring_section:
        non_recurring_parent = non_recurring_section.find_parent('div')
        charges = non_recurring_parent.find_all('div', class_='chargeAtBillBreakDown')

        for charge in charges:
            desc = charge.find('span', class_='detail_desc')
            amount_span = charge.find('span', class_='detail_sum')
            vat_span = charge.find('span', class_='tax_desc')

            if desc and amount_span:
                amount_text = amount_span.get_text(strip=True)
                vat_text = vat_span.get_text(strip=True) if vat_span else ''

                cost = extract_amount_from_text(amount_text)
                vat = extract_amount_from_text(vat_text)

                charge_info = {
                    'təsvir': desc.text.strip(),
                    'məbləğ_text': amount_text,
                    'məbləğ': cost,
                    'vat_text': vat_text,
                    'vat': vat,
                    'toplam': round(cost + vat, 2)
                }
                billing_data['non_recurring_charges'].append(charge_info)

    # Usage Charges
    usage_section = soup.find('div', string='Usage Charges')
    if usage_section:
        usage_parent = usage_section.find_parent('div')
        charges = usage_parent.find_all('div', class_='chargeAtBillBreakDown')

        for charge in charges:
            desc = charge.find('span', class_='detail_desc')
            external_id = charge.find('span', class_='external_id')
            amount_span = charge.find('span', class_='detail_sum')
            vat_span = charge.find('span', class_='tax_desc')

            if desc and amount_span:
                amount_text = amount_span.get_text(strip=True)
                vat_text = vat_span.get_text(strip=True) if vat_span else ''

                cost = extract_amount_from_text(amount_text)
                vat = extract_amount_from_text(vat_text)

                charge_info = {
                    'təsvir': desc.text.strip(),
                    'external_id': external_id.text.strip() if external_id else 'N/A',
                    'məbləğ_text': amount_text,
                    'məbləğ': cost,
                    'vat_text': vat_text,
                    'vat': vat,
                    'toplam': round(cost + vat, 2)
                }
                billing_data['usage_charges'].append(charge_info)

    return billing_data


def extract_invoice_data(pdf_content):
    """PDF məzmunundan invoice məlumatlarını çıxarır"""
    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
        all_text = ""

        for page in pdf.pages:
            page_text = page.extract_text()
            all_text += page_text + "\n"

        invoice_data = {
            'ümumi_məlumat': {},
            'xərclər_üzrə': {}
        }

        # Ümumi məlumatlar
        invoice_data['ümumi_məlumat']['ad_soyad'] = safe_regex_search(r'Ad, Soyad:\s*\n(.+)', all_text)
        invoice_data['ümumi_məlumat']['abunəçi_kodu'] = safe_regex_search(r'Abunəçinin kodu:\s*(\d+)', all_text)
        invoice_data['ümumi_məlumat']['telefon'] = safe_regex_search(r'Tel\. nömrəsi:\s*(\d+)', all_text)
        invoice_data['ümumi_məlumat']['faktura_nömrəsi'] = safe_regex_search(r'Fakturanın nömrəsi:\s*(\d+)', all_text)
        invoice_data['ümumi_məlumat']['faktura_dövrü'] = safe_regex_search(r'Fakturanın dövrü:\s*(.+)', all_text)

        # Xərclər üzrə məlumat
        xercler_bolme = re.search(r'Xərclər üzrə məlumat\s+Məbləğ\s+(.*?)Toplam:', all_text, re.DOTALL)
        if xercler_bolme:
            xercler_text = xercler_bolme.group(1)

            # Tarif paketi
            tarif_match = safe_regex_search(r'Tarif paketinin abunə haqqı\s+([\d,]+\.?\d*₼)', xercler_text)
            invoice_data['xərclər_üzrə']['tarif_paketi'] = {
                'text': tarif_match,
                'amount': extract_amount_from_text(tarif_match)
            }

            # İzahlı faktura
            izahli_match = safe_regex_search(r'İzahlı faktura\s+([\d,]+\.?\d*₼)', xercler_text)
            invoice_data['xərclər_üzrə']['izahlı_faktura'] = {
                'text': izahli_match,
                'amount': extract_amount_from_text(izahli_match)
            }

        return invoice_data


def compare_tarif_paketi(ui_data, pdf_data):
    """STEP 1: Tarif paketini müqayisə edir"""

    print("\n" + "=" * 80)
    print("STEP 1: TARİF PAKETİ MÜQAYISƏSI")
    print("=" * 80)

    # PDF-dən tarif paketi məbləği
    pdf_tarif_amount = pdf_data['xərclər_üzrə']['tarif_paketi']['amount']
    print(f"\nPDF Tarif Paketi: {pdf_data['xərclər_üzrə']['tarif_paketi']['text']} = {pdf_tarif_amount} AZN")

    # UI-dan Supersen paketini tap (GB dəyişə bilər)
    supersen_charge = None
    for charge in ui_data['recurring_charges']:
        # "Supersen" və "GB" və "monthly RC postpaid" keçən charge-ı tap
        if 'supersen' in charge['təsvir'].lower() and 'gb' in charge['təsvir'].lower() and 'monthly rc postpaid' in \
                charge['təsvir'].lower():
            supersen_charge = charge
            break

    if supersen_charge:
        ui_amount = supersen_charge['məbləğ']
        ui_vat = supersen_charge['vat']
        ui_total = supersen_charge['toplam']

        print(f"\nUI Supersen Paketi: {supersen_charge['təsvir']}")
        print(f"  - Məbləğ (Cost): {ui_amount} AZN")
        print(f"  - VAT: {ui_vat} AZN")
        print(f"  - Toplam (Cost + VAT): {ui_total} AZN")

        # Müqayisə et
        tolerance = 0.01  # 1 qəpik tolerans
        if abs(ui_total - pdf_tarif_amount) < tolerance:
            print(f"\n✅ UYĞUNDUR: UI Toplam ({ui_total}) = PDF Tarif Paketi ({pdf_tarif_amount})")
            return True
        else:
            print(f"\n❌ UYĞUN DEYİL: UI Toplam ({ui_total}) ≠ PDF Tarif Paketi ({pdf_tarif_amount})")
            print(f"   Fərq: {abs(ui_total - pdf_tarif_amount)} AZN")
            return False
    else:
        print("\n❌ XƏTA: UI-da Supersen paketi tapılmadı!")
        return False


def compare_izahli_faktura(ui_data, pdf_data):
    """STEP 2: İzahlı faktura müqayisə edir"""

    print("\n" + "=" * 80)
    print("STEP 2: İZAHLI FAKTURA MÜQAYISƏSI")
    print("=" * 80)

    # PDF-dən izahlı faktura məbləği
    pdf_izahli_amount = pdf_data['xərclər_üzrə']['izahlı_faktura']['amount']
    print(f"\nPDF İzahlı Faktura: {pdf_data['xərclər_üzrə']['izahlı_faktura']['text']} = {pdf_izahli_amount} AZN")

    # UI-dan Ətraflı hesab faktura və Izahcell-i tap
    etrafli_hesab = None
    izahcell = None

    for charge in ui_data['recurring_charges']:
        if 'ətraflı hesab faktura' in charge['təsvir'].lower() and 'rc postpaid' in charge['təsvir'].lower():
            etrafli_hesab = charge
            break

    for charge in ui_data['non_recurring_charges']:
        if 'izahcell' in charge['təsvir'].lower() and 'oc postpaid' in charge['təsvir'].lower():
            izahcell = charge
            break

    if etrafli_hesab and izahcell:
        # Ətraflı hesab
        etrafli_cost = etrafli_hesab['məbləğ']
        etrafli_vat = etrafli_hesab['vat']
        etrafli_total = etrafli_hesab['toplam']

        print(f"\nUI Ətraflı hesab faktura: {etrafli_hesab['təsvir']}")
        print(f"  - Məbləğ (Cost): {etrafli_cost} AZN")
        print(f"  - VAT: {etrafli_vat} AZN")
        print(f"  - Toplam: {etrafli_total} AZN")

        # Izahcell
        izahcell_cost = izahcell['məbləğ']
        izahcell_vat = izahcell['vat']
        izahcell_total = izahcell['toplam']

        print(f"\nUI Izahcell: {izahcell['təsvir']}")
        print(f"  - Məbləğ (Cost): {izahcell_cost} AZN")
        print(f"  - VAT: {izahcell_vat} AZN")
        print(f"  - Toplam: {izahcell_total} AZN")

        # İki charge-ın toplamı
        ui_combined_total = round(etrafli_total + izahcell_total, 2)
        print(f"\nUI İkisinin Toplamı: {etrafli_total} + {izahcell_total} = {ui_combined_total} AZN")

        # Müqayisə et
        tolerance = 0.01  # 1 qəpik tolerans
        if abs(ui_combined_total - pdf_izahli_amount) < tolerance:
            print(f"\n✅ UYĞUNDUR: UI Toplam ({ui_combined_total}) = PDF İzahlı Faktura ({pdf_izahli_amount})")
            return True
        else:
            print(f"\n❌ UYĞUN DEYİL: UI Toplam ({ui_combined_total}) ≠ PDF İzahlı Faktura ({pdf_izahli_amount})")
            print(f"   Fərq: {abs(ui_combined_total - pdf_izahli_amount)} AZN")
            return False
    else:
        if not etrafli_hesab:
            print("\n❌ XƏTA: UI-da Ətraflı hesab faktura tapılmadı!")
        if not izahcell:
            print("\n❌ XƏTA: UI-da Izahcell tapılmadı!")
        return False


def test_driver(driver):
    driver.get(
        "https://sso.apps.dbss.pr.azercell.com/auth/realms/csr-optima/protocol/openid-connect/auth?client_id=csr-web&redirect_uri=https%3A%2F%2Fcsr.apps.dbss.pr.azercell.com%2Ftenant1%2Fhome&state=2eca1adc-6b94-43eb-b1a1-7caf4b098048&response_mode=fragment&response_type=code&scope=openid&nonce=24cec170-bf4e-44d4-a507-b4db98977d1b&code_challenge=E9J4iN7OiCkYIx7FNU8uppSSY2kGgG_lGpGquYfeJQE&code_challenge_method=S256")

    # Login
    username_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    username_input.send_keys("pos-agent")

    password_input = driver.find_element(By.ID, "password")
    password_input.send_keys("Testing123", Keys.ENTER)

    # Search MSISDN
    search_icon = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//span[@class="oIcon search"]'))
    )
    search_icon.click()

    msisdn_input = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, "undefined.formControl"))
    )
    msisdn_input.send_keys("994102586644")

    search_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@class="primary btn btn-default"]'))
    )
    search_button.click()

    # Select criteria and proceed
    criteria_panel = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//div[@class="headerPart2Details "]'))
    )
    criteria_panel.click()

    proceed_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Proceed"]'))
    )
    proceed_button.click()

    # ==================== PART 1: BILLING OVERVIEW ====================
    # Hover Billing - Billing Overview
    billing_nav = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//p[@class='navText' and text()='Billing']"))
    )
    ActionChains(driver).move_to_element(billing_nav).perform()
    time.sleep(1)

    billing_overview = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Billing Overview']"))
    )
    billing_overview.click()

    time.sleep(3)

    # Scroll to and click Mobile Postpaid
    mobile_postpaid = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='col-xs-9' and text()='Mobile Postpaid']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", mobile_postpaid)
    time.sleep(1)
    mobile_postpaid.click()

    time.sleep(3)

    # Extract HTML content
    billing_content_div = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "bbd_contentDetailes"))
    )
    html_content = billing_content_div.get_attribute('outerHTML')
    billing_data = extract_billing_overview_data(html_content)

    # ==================== PART 2: DOCUMENT MANAGER (PDF) ====================
    # Hover Account - Document Manager
    account_nav = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//p[@class='navText' and text()='Account']"))
    )
    ActionChains(driver).move_to_element(account_nav).perform()
    time.sleep(1)

    document_manager = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Document Manager']"))
    )
    document_manager.click()

    # Click Etrafli hesab PDF
    etrafli_hesab = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//tspan[@class='triggerWrapper' and contains(text(), 'Etrafli_hes')]"))
    )
    etrafli_hesab.click()

    time.sleep(3)
    original_window = driver.current_window_handle

    for window in driver.window_handles:
        if window != original_window:
            driver.switch_to.window(window)
            break

    pdf_url = driver.current_url
    time.sleep(3)

    pdf_base64 = driver.execute_script("""
        return new Promise((resolve, reject) => {
            fetch(arguments[0])
                .then(response => response.blob())
                .then(blob => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                })
                .catch(reject);
        });
    """, pdf_url)

    pdf_content = base64.b64decode(pdf_base64)
    invoice_data = extract_invoice_data(pdf_content)

    # Əsas pəncərəyə qayıt
    driver.switch_to.window(original_window)

    # ==================== COMPARISON ====================
    result_step1 = compare_tarif_paketi(billing_data, invoice_data)
    result_step2 = compare_izahli_faktura(billing_data, invoice_data)

    # Final nəticə
    print("\n" + "=" * 80)
    print("FİNAL NƏTİCƏ")
    print("=" * 80)
    print(f"STEP 1 (Tarif Paketi): {'✅ PASS' if result_step1 else '❌ FAIL'}")
    print(f"STEP 2 (İzahlı Faktura): {'✅ PASS' if result_step2 else '❌ FAIL'}")
    print(f"\nÜmumi: {'✅ BÜTÜN TESTLƏR KEÇDİ' if (result_step1 and result_step2) else '❌ BƏZİ TESTLƏR UĞURSUZ OLDU'}")
    print("=" * 80)

    time.sleep(5)