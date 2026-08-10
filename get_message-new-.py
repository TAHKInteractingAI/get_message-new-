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
from datetime import datetime, timezone, timedelta
from datetime import time as dtime
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

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    return gspread.authorize(creds)


# =========================
# SCREENSHOT
# =========================
def save_screenshot(driver, file_name="error.png"):
    try:
        driver.save_screenshot(file_name)
        print(f"📸 Saved: {file_name}")
    except Exception as e:
        print(f"❌ Failed to save screenshot: {e}")


# =========================
# NEW DRIVER FROM SOURCE 1
# =========================
def get_driver():
    options = uc.ChromeOptions()

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

    driver.get("https://teams.microsoft.com/")
    wait = WebDriverWait(driver, 30)

    try:
        print("⏳ Logging in...")

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
            pass

        email_box = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="email"], input[name="loginfmt"]')
            )
        )
        email_box.send_keys(email)
        email_box.send_keys(Keys.RETURN)

        time.sleep(3)

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
            pass

        pass_box = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="password"], input[name="passwd"]')
            )
        )
        pass_box.send_keys(password)
        pass_box.send_keys(Keys.RETURN)

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

        print("✅ Login success! Đang chờ giao diện Teams render...")

        time.sleep(10)
        
        try:
            first_chat = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '(//div[@role="listitem"] | //div[@role="treeitem"])[1]')
                )
            )
            first_chat.click()
            print("👉 Đã click kích hoạt nhóm đầu tiên để load giao diện bên phải.")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Không thể click nhóm đầu tiên: {e}")

        save_screenshot(driver, "after_login_rendered.png")
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
    clean_title = re.sub(r'[*?:\/\\\[\]]', '', title)
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

    try:
        fmt = cellFormat(wrapStrategy="WRAP")
        format_cell_range(ws, "D:D", fmt)

        set_column_width(ws, 'A', 180)
        set_column_width(ws, 'B', 100)
        set_column_width(ws, 'C', 100)
        set_column_width(ws, 'D', 1000)
        print(f"✅ Updated sheet formatting: {title}")
    except Exception as formatting_error:
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
# GET MESSAGE WITH FLEXIBLE SHIFT FILTERING
# =========================
def is_in_shift_range(dt_local, content_text, current_hour):
    """
    Xác định linh hoạt tin nhắn thuộc Ca Sáng (crawl ~12h30), Ca Chiều (crawl ~18h), hoặc Ca Tối (crawl ~05h sáng hôm sau)
    """
    now_vn = datetime.now(local_tz)
    msg_date = dt_local.date()
    msg_time = dt_local.time()

    today = now_vn.date()
    yesterday = (now_vn - timedelta(days=1)).date()
    content_lower = content_text.lower()

    # --- KHUNG 1: CA SÁNG (Chạy từ 05:00 sáng đến 15:00 chiều) ---
    if 5 <= current_hour < 15:
        # Nhánh 1: Ngày hôm nay và giờ gửi từ 05:00 đến 13:30
        if msg_date == today and dtime(5, 0) <= msg_time <= dtime(13, 30):
            return True
        # Nhánh 2: Từ khóa nhận diện ca sáng trong text
        if msg_date == today and any(kw in content_lower for kw in ["ca sáng", "ca sang", "-11h", "- 11h", "-12h", "8h-12h"]):
            return True

    # --- KHUNG 2: CA CHIỀU (Chạy từ 15:00 đến 21:00 tối) ---
    elif 15 <= current_hour < 21:
        # Nhánh 1: Ngày hôm nay và giờ gửi từ 12:00 đến 18:30
        if msg_date == today and dtime(12, 0) <= msg_time <= dtime(18, 30):
            return True
        # Nhánh 2: Từ khóa nhận diện ca chiều trong text
        if msg_date == today and any(kw in content_lower for kw in ["ca chiều", "ca chieu", "13h-17h", "13h-18h"]):
            return True

    # --- KHUNG 3: CA TỐI (Chạy đêm/rạng sáng từ 21:00 đêm đến 05:00 sáng hôm sau) ---
    else:
        # Nhánh 1: Tin gửi tối HÔM QUA (từ 17:30 đến 23:59)
        if msg_date == yesterday and msg_time >= dtime(17, 30):
            return True
        # Nhánh 2: Tin gửi rạng sáng HÔM NAY (từ 00:00 đến 05:30)
        if msg_date == today and msg_time <= dtime(5, 30):
            return True
        # Nhánh 3: Từ khóa nhận diện ca tối/đêm
        if (msg_date == yesterday or msg_date == today) and any(kw in content_lower for kw in ["ca tối", "ca toi", "ca đêm", "ca dem", "18h-22h", "22:00"]):
            return True

    return False


def get_messages(driver, worksheet, current_hour):
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

                # Bóc tách nội dung HTML
                content_el = item.find_element(By.CSS_SELECTOR, '[id^="content-"]')
                raw_html = content_el.get_attribute("innerHTML")

                text = re.sub(
                    r"</?(span|at|a|strong|b|i|em)[^>]*>",
                    "",
                    raw_html,
                    flags=re.IGNORECASE,
                )
                text = re.sub(r"<br\s*/>", "\n", text, flags=re.IGNORECASE)
                text = re.sub(r"</(div|p)>", "\n", text, flags=re.IGNORECASE)
                text = re.sub(r"<[^>]+>", "", text)
                text = html.unescape(text)

                lines = [line.strip() for line in text.split('\n')]
                content = "\n".join([line for line in lines if line])

                # -------------------------------------------------------------
                # 🛑 LỌC THEO CA LÀM VIỆC DỰA TRÊN CẢ TIME VÀ TỪ KHÓA NỘI DUNG
                # -------------------------------------------------------------
                if not is_in_shift_range(dt_local, content, current_hour):
                    continue

                date_str = dt_local.strftime("%Y-%m-%d")
                time_str = dt_local.strftime("%H:%M:%S")

                data.append([name, date_str, time_str, content])
            except Exception:
                continue

        if data:
            save_to_excel(data, worksheet)
        else:
            print(f"ℹ️ Không có tin nhắn nào thuộc ca làm việc cho [{worksheet}]")

    except Exception as e:
        print("❌ get_messages error:", e)


# =========================
# SEARCH CHAT FROM SOURCE 1
# =========================
def open_chat_by_search(driver, chat_name):
    wait = WebDriverWait(driver, 20)
    chat_item_xpath = '//*[contains(@data-tid, "chat-list") or contains(@data-tid, "chat-item") or @role="treeitem" or @role="listitem"]'

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, chat_item_xpath)))
        groups = driver.find_elements(By.XPATH, chat_item_xpath)

        for g in groups:
            txt = g.text.strip().split("\n")[0]
            if not txt:
                txt = g.get_attribute("aria-label")

            if txt == chat_name:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", g
                )
                time.sleep(1)
                g.click()
                time.sleep(3)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tid="message-pane-list-runway"], [role="document"], [data-tid="chat-pane-item"]'))
                    )
                except:
                    pass

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
    wait = WebDriverWait(driver, 30)

    try:
        print("⏳ Waiting for Teams chat list sidebar to load...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tid="left-rail-header"], #left-rail-list, [role="list"]')))
        time.sleep(5)

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
                txt = g.text.strip().split("\n")[0]
                if not txt:
                    txt = g.get_attribute("aria-label") or g.get_attribute("title")

                if txt:
                    txt = txt.strip()

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
        current_hour = datetime.now(local_tz).hour
        print(f"⏰ Thời điểm chạy script: {current_hour}h")

        group_names = get_all_groups(driver)

        for group in group_names:
            try:
                print(f"\n===== Processing: {group} =====")

                safe_sheet_name = sanitize_sheet_title(group)
                create_worksheet(safe_sheet_name)

                if open_chat_by_search(driver, group):
                    get_messages(driver, safe_sheet_name, current_hour)

                time.sleep(3)

            except Exception as e:
                print(f"❌ Skip Error on '{group}': {repr(e)}")

        driver.quit()
        print("✅ DONE")
