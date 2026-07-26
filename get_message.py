# =========================
# APPLY LOGIN + DRIVER + ELEMENT INTERACTION FROM SOURCE 1
# INTO SOURCE 2
# =========================

import os
import gc
import json
import time
import pytz
import gspread
import tempfile
import undetected_chromedriver as uc
import re
import html
from datetime import datetime, timezone
from oauth2client.service_account import ServiceAccountCredentials

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from gspread_formatting import *

gc.disable()

# =========================
# CONFIG
# =========================
local_tz = pytz.timezone("Asia/Ho_Chi_Minh")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1_m7s-1-I-SOFfzlWe7CBf5fstFir7qXYAKW4j-8hKYM/edit?usp=sharing"

email = "tech.qtdata@gmail.com"
password = "passnotE@1234"

# =========================
# GOOGLE SHEETS
# =========================
def get_gsclient():
    creds_dict = json.loads(gcp_credentials_json)

    # Combined scopes to guarantee Drive manipulation permissions are passed
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Explicitly use the Service Account dict constructor with combined scopes
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)

    # Force gspread to maintain authorization across both API endpoints
    return gspread.authorize(creds)


# =========================
# SCREENSHOT
# =========================
def save_screenshot(driver, file_name="error.png"):
    try:
        driver.save_screenshot(file_name)
        print(f"📸 Saved: {file_name}")
    except:
        print(f"❌ Failed to save screenshot: {e}")


# =========================
# NEW DRIVER FROM SOURCE 1
# =========================
def get_driver():
    options = uc.ChromeOptions()

    # 1. Do NOT use options.add_argument("--headless=new") here!
    # 2. DO NOT force the chromium-browser binary unless absolutely necessary.

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-infobars")

    # Cookie and password prefs
    prefs = {
        "profile.cookie_controls_mode": 0,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    options.page_load_strategy = "eager"
    options.add_argument("--lang=en-GB")

    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        options.add_argument(f"--proxy-server={proxy_url}")

    # 3. Pass headless=True directly into the uc.Chrome constructor instead
    driver = uc.Chrome(options=options, headless=True, version_main=150)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'credentials', {
                    get: () => undefined
                });
                window.PublicKeyCredential = undefined;
            """
        }
    )

    return driver


# =========================
# LOGIN FROM SOURCE 1
# =========================
def login():
    driver = get_driver()

    # Truy cập link chuẩn cho Work/School
    driver.get("https://teams.microsoft.com/")
    wait = WebDriverWait(driver, 30)

    try:
        print("⏳ Logging in...")

        # 1. Xử lý nút Sign in (nếu bị đẩy ra trang chờ)
        try:
            sign_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//button[contains(., "Sign in")] | //a[contains(., "Sign in")] | //button[contains(., "Đăng nhập")]',
                    )
                )
            )
            sign_btn.click()
        except:
            pass  # Bỏ qua nếu form điền email hiện ra trực tiếp

        # 2. Ô nhập Email (Sử dụng Selector linh hoạt cho Microsoft)
        email_box = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="email"], input[name="loginfmt"]')
            )
        )
        email_box.send_keys(email)
        email_box.send_keys(Keys.RETURN)

        time.sleep(3)
        # ====== THÊM ĐOẠN NÀY VÀO ======
        # Xử lý trường hợp Microsoft đòi gửi mã code, ép nó quay về dùng Mật khẩu
        try:
            use_pass_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[contains(text(), "Use your password") or contains(text(), "Sử dụng mật khẩu")]',
                    )
                )
            )
            use_pass_btn.click()
            time.sleep(2)
        except:
            pass  # Nếu màn hình đi thẳng tới ô mật khẩu thì cứ bỏ qua bước này
        # ===============================
        # 3. Ô nhập Password
        pass_box = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="password"], input[name="passwd"]')
            )
        )
        pass_box.send_keys(password)
        pass_box.send_keys(Keys.RETURN)

        # 4. Xử lý nút "Stay signed in?" (Chọn No để không lưu đăng nhập)
        try:
            print("⏳ Đang xử lý màn hình Stay signed in...")
            no_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="declineButton"] | //*[@id="idBtn_Back"] | //*[@value="No"] | //button[contains(., "No")]',
                    )
                )
            )
            no_btn.click()
            time.sleep(3)
        except:
            print("⚠️ Không thấy màn hình Stay signed in, tiếp tục...")
            pass

        print("✅ Login success")

        # Chờ giao diện Teams load hẳn
        time.sleep(15)

        return driver

    except Exception as e:
        save_screenshot(driver, "login_error.png")
        print("❌ Login failed:", e)
        driver.quit()
        return None


# =========================
# CREATE SHEET
# =========================
def sanitize_sheet_title(title):
    # Remove characters forbidden by Google Sheets: * ? : / \ [ ]
    clean_title = re.sub(r'[*?:\/\\\[\]]', '', title)
    # Truncate to maximum 100 characters allowed by Google Sheets
    return clean_title[:100].strip()

def create_worksheet(title):
    gcx = get_gsclient()
    sheet = gcx.open_by_url(SPREADSHEET_URL)

    names = [x.title for x in sheet.worksheets()]

    if title in names:
        ws = sheet.worksheet(title)
    else:
        ws = sheet.add_worksheet(title=title, rows=1000, cols=4)
        ws.update("A1:D1", [["NAME", "DATE", "TIME", "CONTENT"]])
        ws.freeze(rows=1)

    # REPLACED: Use safe native format wrappers instead of global set_column_widths
    try:
        # Wrap text formatting rule
        fmt = cellFormat(wrapStrategy="WRAP")
        format_cell_range(ws, "D:D", fmt)

        # Safe column width formatting
        set_column_width(ws, 'A', 180)
        set_column_width(ws, 'B', 100)
        set_column_width(ws, 'C', 100)
        set_column_width(ws, 'D', 1000)
        print(f"✅ Updated sheet formatting: {title}")
    except Exception as formatting_error:
        # If formatting fails due to scope restrictions, do not let it crash your script execution
        print(f"⚠️ Formatting skipped for {title}: {formatting_error}")


# =========================
# SAVE DATA
# =========================
def save_to_excel(rows, worksheet):
    gcx = get_gsclient()
    sheet = gcx.open_by_url(SPREADSHEET_URL)
    ws = sheet.worksheet(worksheet)

    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        print(f"✅ Added {len(rows)} rows -> {worksheet}")


# =========================
# GET MESSAGE
# =========================
def get_messages(driver, worksheet):
    try:
        wait = WebDriverWait(driver, 20)

        pane = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-tid="message-pane-list-runway"]')
            )
        )

        items = pane.find_elements(By.CSS_SELECTOR, '[data-tid="chat-pane-item"]')

        data = []

        for item in items:
            try:
                name = item.find_element(
                    By.CSS_SELECTOR, '[data-tid="message-author-name"]'
                ).text

                timestamp = item.find_element(By.TAG_NAME, "time").get_attribute(
                    "datetime"
                )

                dt_utc = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                    tzinfo=timezone.utc
                )

                dt_local = dt_utc.astimezone(local_tz)

                date_str = dt_local.strftime("%Y-%m-%d")
                time_str = dt_local.strftime("%H:%M:%S")

                # --- CÁCH XỬ LÝ TẬN GỐC BẰNG HTML ---
                content_el = item.find_element(By.CSS_SELECTOR, '[id^="content-"]')

                raw_html = content_el.get_attribute("innerHTML")

                # 1. MỚI: Xóa các thẻ inline (mention, span, link) TRƯỚC để tránh bị cắt vụn chữ
                text = re.sub(
                    r"</?(span|at|a|strong|b|i|em)[^>]*>",
                    "",
                    raw_html,
                    flags=re.IGNORECASE,
                )

                # 2. Chủ động thay thế các thẻ ngắt dòng phổ biến thành ký tự \n
                text = re.sub(r"<br\s*/>", "\n", text, flags=re.IGNORECASE)
                text = re.sub(r"</(div|p)>", "\n", text, flags=re.IGNORECASE)

                # 3. Xóa sạch mọi thẻ HTML còn sót lại
                text = re.sub(r"<[^>]+>", "", text)

                # 4. Dịch các ký tự đặc biệt của web (như &nbsp; thành dấu cách)
                text = html.unescape(text)

                # 5. Dọn dẹp khoảng trắng thừa và nối lại thành đoạn văn hoàn chỉnh
                lines = [line.strip() for line in text.split('\n')]
                content = "\n".join([line for line in lines if line])
                # ------------------------------------
                data.append([name, date_str, time_str, content])
            except:
                continue

        save_to_excel(data, worksheet)

    except Exception as e:
        print("❌ get_messages error:", e)


# =========================
# SEARCH CHAT FROM SOURCE 1
# =========================
def open_chat_by_search(driver, chat_name):
    wait = WebDriverWait(driver, 20)
    chat_item_xpath = '//*[contains(@data-tid, "chat-list") or contains(@data-tid, "chat-item") or @role="treeitem" or @role="listitem"]'

    try:
        # 1. Chờ danh sách tải xong bằng XPath mới
        wait.until(EC.presence_of_element_located((By.XPATH, chat_item_xpath)))
        groups = driver.find_elements(By.XPATH, chat_item_xpath)

        for g in groups:
            txt = g.text.strip().split("\n")[0]
            if not txt:
                txt = g.get_attribute("aria-label")

            # 3. SO SÁNH TUYỆT ĐỐI
            if txt == chat_name:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", g
                )
                time.sleep(1)
                g.click()
                time.sleep(5)
                print(f"📂 Đã mở đúng nhóm: {chat_name}")
                return True

        print(f"⚠️ Không thấy {chat_name} ở ngoài, thử dùng thanh Search...")
        search_xpath = (
            '//input[@placeholder="Search"]'
            ' | //input[@aria-label="Search"]'
            ' | //input[@id="ms-searchux-input"]'
        )

        search = wait.until(EC.presence_of_element_located((By.XPATH, search_xpath)))
        search.click()
        search.send_keys(Keys.CONTROL + "a")
        search.send_keys(Keys.BACKSPACE)
        search.send_keys(chat_name)

        time.sleep(4)
        dropdown_result = driver.find_element(
            By.XPATH, f"//*[contains(text(), '{chat_name}')]"
        )
        dropdown_result.click()

        time.sleep(5)
        print(f"📂 Opened via search: {chat_name}")
        return True

    except Exception as e:
        print("❌ Cannot open:", chat_name, e)
        return False


# =========================
# GET ALL GROUPS
# =========================
def get_all_groups(driver):
    wait = WebDriverWait(driver, 30) # Increased timeout for initial heavy load

    try:
        print("⏳ Waiting for Teams chat list sidebar to load...")
        # First, ensure the left navigation pane container is present
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tid="left-rail-header"], #left-rail-list, [role="list"]')))
        time.sleep(5) # Give the DOM an extra moment to populate names

        # Target list items specifically by common Teams structures
        chat_item_xpath = (
            '//div[@role="listitem"]'
            ' | //div[@role="treeitem"]'
            ' | //*[contains(@data-tid, "chat-list-item")]'
            ' | //*[contains(@data-tid, "chat-item")]'
        )

        groups = driver.find_elements(By.XPATH, chat_item_xpath)

        names = []
        for g in groups:
            try:
                # Prioritize explicit data properties or text
                txt = g.text.strip().split("\n")[0]
                if not txt:
                    txt = g.get_attribute("aria-label") or g.get_attribute("title")

                # Clean up extracted string variations
                if txt:
                    txt = txt.strip()

                # Filter out standard UI elements and empty entries
                if (
                    txt
                    and txt not in names
                    and len(txt) > 2
                    and not any(x in txt for x in ["Chat", "Unread", "Pinned", "Recent", "Meeting"])
                ):
                    names.append(txt)
            except:
                pass

        print(f"Found {len(names)} groups")
        return names

    except Exception as e:
        save_screenshot(driver, "error_groups.png")
        print("❌ get_all_groups failed:", e)
        return []


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    driver = login()

    if driver:
        group_names = get_all_groups(driver)

        for group in group_names:
            try:
                print(f"\n===== Processing: {group} =====")

                # 1. Actually call the sanitizer function here!
                safe_sheet_name = sanitize_sheet_title(group)

                # 2. Pass the SAFE cleaned name to Google Sheets
                create_worksheet(safe_sheet_name)

                # 3. Use the RAW group name to find the chat inside MS Teams
                if open_chat_by_search(driver, group):
                    get_messages(driver, safe_sheet_name)

                time.sleep(3)

            except Exception as e:
                # If something else fails, this prints the error type and message cleanly
                print(f"❌ Skip Error on '{group}': {repr(e)}")

        driver.quit()
        print("✅ DONE")
