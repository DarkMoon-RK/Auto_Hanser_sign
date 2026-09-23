import io
import json
import sys

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pushplus_utils import (
    get_access_key,
    send_email,
    send_pushplus_message,
)


# Windows GitHub Actions 使用 UTF-8 输出
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
    )


def load_json_file(path):
    with open(path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


# 读取用户配置
settings = load_json_file("setting.json")
user_settings = settings["Set"]

your_username = user_settings["NAME"]
your_password = user_settings["PASSWORD"]
use_email = user_settings["USE_EMAIL"]
to_email = user_settings["TO_EMAIL"]
pushplus_token = user_settings["PUSHPIUS-TOKEN"]


# 读取服务器配置
server = load_json_file("sever.json")
server_settings = server["Sc"]

secret_key = server_settings["SECRETKEY"]
smtp_server = server_settings["SMTP_SERVER"]
smtp_port = server_settings["SMTP_PORT"]
smtp_user = server_settings["SMTP_USER"]
smtp_password = server_settings["SMTP_PASSWORD"]
token_server = server_settings["TOKEN_SEVER"]


def send_notification(subject, body):
    """发送邮件或 PushPlus 通知。"""
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
        except Exception as error:
            print(f"邮件发送失败: {error}")
    else:
        try:
            access_key, _ = get_access_key(secret_key, token_server)
            send_pushplus_message(
                pushplus_token,
                access_key,
                subject,
                body,
            )
        except Exception as error:
            print(f"PushPlus 消息发送失败: {error}")


def create_driver():
    """
    创建 Chrome WebDriver。

    不手动指定 chromedriver 路径，让 Selenium Manager 根据当前
    Chrome 自动下载和匹配对应版本的 ChromeDriver。
    """
    options = webdriver.ChromeOptions()

    # GitHub Actions 必须使用无界面模式
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    # GitHub Actions 环境常用参数
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--remote-debugging-port=0")

    # 不使用已有用户配置，避免配置文件锁定或损坏导致 Chrome 崩溃
    options.add_argument("--user-data-dir=" + "selenium-profile")

    # Selenium 4.25 使用 Selenium Manager 自动匹配驱动
    return webdriver.Chrome(options=options)


driver = None

try:
    print("正在启动 Chrome WebDriver...")
    driver = create_driver()
    print("Chrome WebDriver 启动成功。")

    url = "https://2550505.com/"
    print(f"正在打开网页: {url}")
    driver.get(url)

    wait = WebDriverWait(driver, 20)

    try:
        login_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'h-button') "
                    "and contains(@class, 'h-button--small') "
                    "and normalize-space()='登录']",
                )
            )
        )

        print("找到登录按钮，开始登录。")
        login_button.click()

        username_field = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='text' and @placeholder='昵称/UID']",
                )
            )
        )

        password_field = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='password' and @placeholder='密码']",
                )
            )
        )

        username_field.clear()
        username_field.send_keys(your_username)

        password_field.clear()
        password_field.send_keys(your_password)

        submit_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'h-button')]"
                    "//span[normalize-space()='登录']",
                )
            )
        )

        submit_button.click()

        wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "sign-btn")
            )
        )

        print("登录成功。")
        send_notification("登录成功", "你已经成功登录。")

    except TimeoutException:
        print("没有找到登录按钮，可能已经登录，继续执行签到。")

    try:
        sign_in_button = wait.until(
            EC.element_to_be_clickable(
                (By.CLASS_NAME, "sign-btn")
            )
        )

        sign_in_button.click()

        print("签到成功。")
        send_notification("每日签到成功", "你今天已经成功签到。")

    except TimeoutException:
        print("没有找到签到按钮，可能今天已经签到过了。")
        send_notification("你今天已经签到过了", "等待明天吧。")

    except Exception as error:
        print(f"签到过程中出现错误: {error}")
        send_notification("签到失败", f"签到失败，请检查错误: {error}")
        raise

finally:
    if driver is not None:
        print("正在关闭浏览器。")
        driver.quit()
