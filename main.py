import io
import json
import sys
import os

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pushplus_utils import get_access_key, send_email, send_pushplus_message


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
cfg = settings["Set"]

your_username = cfg["NAME"]
your_password = cfg["PASSWORD"]
use_email = cfg["USE_EMAIL"]
to_email = cfg["TO_EMAIL"]
pushplus_token = cfg["PUSHPIUS-TOKEN"]

server = load_json("sever.json")
sc = server["Sc"]

secret_key = sc["SECRETKEY"]
smtp_server = sc["SMTP_SERVER"]
smtp_port = sc["SMTP_PORT"]
smtp_user = sc["SMTP_USER"]
smtp_password = sc["SMTP_PASSWORD"]
token_server = sc["TOKEN_SEVER"]


def send_notification(subject, body):
    if use_email:
        try:
            send_email(smtp_server, smtp_port, smtp_user, smtp_password, to_email, subject, body)
        except Exception as e:
            print(f"邮件发送失败: {e}")
    else:
        try:
            access_key, _ = get_access_key(secret_key, token_server)
            send_pushplus_message(pushplus_token, access_key, subject, body)
        except Exception as e:
            print(f"PushPlus 消息发送失败: {e}")


chrome_binary = os.environ.get(
    "CHROME_BINARY",
    r"C:\tools\chrome\chrome-win64\chrome.exe",
)

chrome_driver = os.environ.get(
    "CHROME_DRIVER",
    r"C:\tools\chromedriver\chromedriver-win64\chromedriver.exe",
)

print(f"Chrome path: {chrome_binary}")
print(f"ChromeDriver path: {chrome_driver}")

if not os.path.isfile(chrome_binary):
    raise FileNotFoundError(
        f"Chrome executable not found: {chrome_binary}"
    )

if not os.path.isfile(chrome_driver):
    raise FileNotFoundError(
        f"ChromeDriver executable not found: {chrome_driver}"
    )

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
        sign_in_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "sign-btn")))
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
