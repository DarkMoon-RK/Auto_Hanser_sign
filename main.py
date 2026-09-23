import io
import json
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pushplus_utils import get_access_key, send_email, send_pushplus_message


# Windows GitHub Actions 下输出 UTF-8
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
    )


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


settings = load_json("setting.json")
set_config = settings["Set"]

your_username = set_config["NAME"]
your_password = set_config["PASSWORD"]
use_email = set_config["USE_EMAIL"]
to_email = set_config["TO_EMAIL"]
pushplus_token = set_config["PUSHPIUS-TOKEN"]

server = load_json("sever.json")
server_cfg = server["Sc"]

secret_key = server_cfg["SECRETKEY"]
smtp_server = server_cfg["SMTP_SERVER"]
smtp_port = server_cfg["SMTP_PORT"]
smtp_user = server_cfg["SMTP_USER"]
smtp_password = server_cfg["SMTP_PASSWORD"]
token_server = server_cfg["TOKEN_SEVER"]


def send_notification(subject, body):
    if use_email:
        try:
            send_email(
                smtp_server,
                smtp_port,
                smtp_user,
                smtp_password,
                to_email,
                subject,
                body,
            )
        except Exception as e:
            print(f"邮件发送失败: {e}")
    else:
        try:
            access_key, _ = get_access_key(secret_key, token_server)
            send_pushplus_message(
                pushplus_token,
                access_key,
                subject,
                body,
            )
        except Exception as e:
            print(f"PushPlus 消息发送失败: {e}")


chrome_binary = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_driver = r"C:\tools\chromedriver\chromedriver.exe"

options = webdriver.ChromeOptions()
options.binary_location = chrome_binary
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-extensions")
options.add_argument("--disable-notifications")
options.add_argument("--remote-debugging-port=0")
options.add_argument("--user-data-dir=C:\\selenium-profile")

driver = None

try:
    print("正在启动 Chrome WebDriver...")
    driver = webdriver.Chrome(
        service=Service(chrome_driver),
        options=options,
    )
    print("Chrome WebDriver 启动成功。")

    driver.get("https://2550505.com/")
    wait = WebDriverWait(driver, 20)

    try:
        login_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'h-button') and contains(@class, 'h-button--small') and normalize-space()='登录']",
                )
            )
        )
        print("找到登录按钮，开始登录。")
        login_button.click()

        username_field = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='text' and @placeholder='昵称/UID']")
            )
        )
        password_field = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='password' and @placeholder='密码']")
            )
        )

        username_field.clear()
        username_field.send_keys(your_username)

        password_field.clear()
        password_field.send_keys(your_password)

        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, 'h-button')]//span[normalize-space()='登录']")
            )
        )
        submit_button.click()

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sign-btn")))
        print("登录成功。")
        send_notification("登录成功", "你已经成功登录。")

    except TimeoutException:
        print("未找到登录按钮，可能已登录，继续执行签到。")

    try:
        sign_in_button = wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, "sign-btn"))
        )
        sign_in_button.click()
        print("签到成功。")
        send_notification("每日签到成功", "你今天已经成功签到。")

    except TimeoutException:
        print("未找到签到按钮，可能已签到过。")
        send_notification("你今天已经签到过了", "等待明天再试。")

    except Exception as e:
        print(f"签到过程中出现错误: {e}")
        send_notification("签到失败", f"签到失败，请检查错误: {e}")

finally:
    if driver is not None:
        print("正在关闭浏览器。")
        driver.quit()
