# main.py (完整替换)
import io
import json
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pushplus_utils import get_access_key, send_email, send_pushplus_message

# 保证 Windows Actions 输出 UTF-8
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

# 读取配置
settings = load_json("setting.json")
cfg = settings["Set"]

your_username = cfg["NAME"]
your_password = cfg["PASSWORD"]
use_email = cfg["USE_EMAIL"]
to_email = cfg["TO_EMAIL"]
pushplus_token = cfg.get("PUSHPIUS-TOKEN", "")

server = load_json("sever.json")
sc = server["Sc"]

secret_key = sc.get("SECRETKEY")
smtp_server = sc.get("SMTP_SERVER")
smtp_port = sc.get("SMTP_PORT")
smtp_user = sc.get("SMTP_USER")
smtp_password = sc.get("SMTP_PASSWORD")
token_server = sc.get("TOKEN_SEVER")

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

# 从环境变量读取 workflow 提供的路径（fallback 与之前一致）
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
    print(f"警告：Chrome 可执行文件不存在: {chrome_binary}")
if not os.path.isfile(chrome_driver):
    print(f"警告：ChromeDriver 可执行文件不存在: {chrome_driver}")

# 保存页面和截图的工具函数
def save_debug_artifacts(driver, name_prefix="debug"):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = f"{name_prefix}_{ts}"
    html_path = f"{base}.html"
    png_path = f"{base}.png"
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved page source to {html_path}")
    except Exception as e:
        print(f"保存 page_source 失败: {e}")
    try:
        driver.save_screenshot(png_path)
        print(f"Saved screenshot to {png_path}")
    except Exception as e:
        print(f"保存 screenshot 失败: {e}")
    return html_path, png_path

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
# 独立 profile，避免并发/锁文件干扰
options.add_argument("--user-data-dir=C:\\selenium-profile")

driver = None
artifacts_to_upload = []

try:
    print("正在启动 Chrome WebDriver...")
    driver = webdriver.Chrome(service=Service(chrome_driver), options=options)
    print("Chrome WebDriver 启动成功。")

    url = "https://2550505.com/"
    print(f"打开页面: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # 1) 尝试登录（如果存在登录按钮）
    is_logged_in = False
    try:
        login_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, 'h-button') and contains(@class, 'h-button--small') and normalize-space()='登录']")
            )
        )
        print("找到登录按钮，开始登录。")
        login_button.click()
        time.sleep(1.5)

        # 尝试定位表单并提交
        try:
            username_field = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @placeholder='昵称/UID']"))
            )
            password_field = driver.find_element(By.XPATH, "//input[@type='password' and @placeholder='密码']")

            username_field.clear()
            username_field.send_keys(your_username)
            password_field.clear()
            password_field.send_keys(your_password)
            print("已输入用户名/密码（敏感信息未打印）")

            # 尝试不同的提交按钮 XPath
            submit_xpaths = [
                "//button[contains(@class, 'h-button')]//span[normalize-space()='登录']",
                "//button[.//span[contains(text(), '登录')]]",
                "//button[contains(text(), '登录')]",
            ]
            submit_button = None
            for xp in submit_xpaths:
                try:
                    submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                    print(f"通过 XPath 找到提交按钮: {xp}")
                    break
                except TimeoutException:
                    pass

            if submit_button:
                submit_button.click()
                print("点击登录提交按钮。")
                time.sleep(3)  # 等待登录跳转
                # 简单判断是否登录成功：检查是否存在 sign 按钮或用户头像等
                try:
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sign-btn")))
                    is_logged_in = True
                    print("登录后检测到 sign-btn，判断为已登录。")
                except TimeoutException:
                    print("登录后未检测到 sign-btn，登录可能未成功。")
            else:
                print("未找到登录提交按钮，可能是页面结构变更。")

        except TimeoutException:
            print("登录表单未加载，假设已经登录或页面结构不同。")
            is_logged_in = True

    except TimeoutException:
        print("未找到登录按钮，假设已登录或不需要登录。")
        is_logged_in = True

    # 2) 尝试签到
    try:
        print("准备查找签到按钮...")
        # 更宽松的匹配策略：class 名、部分文本、tag 类型等
        xpath_list = [
            "//button[contains(@class, 'sign-btn') and (string-length(normalize-space())>0)]",
            "//button[contains(@class, 'sign-btn')]",
            "//button[contains(., '签到')]",
            "//a[contains(., '签到')]",
            "//*[contains(@class, 'sign') and (contains(., '签到') or contains(@class,'sign-btn'))]",
        ]

        sign_in_button = None
        for xp in xpath_list:
            try:
                sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                print(f"通过 XPath 找到签到按钮: {xp}")
                break
            except TimeoutException:
                print(f"未通过 XPath 找到签到按钮: {xp}")
                continue

        if sign_in_button:
            # 在点击前保存调试信息
            html_before, png_before = save_debug_artifacts(driver, "before_click")
            artifacts_to_upload.extend([html_before, png_before])

            sign_in_button.click()
            print("已点击签到按钮，等待结果...")
            time.sleep(2.5)

            # 点击后判断是否出现“已签到”或按钮变为 disabled 类等
            clicked_success = False
            # 检查页面是否包含常见的成功提示词
            page = driver.page_source
            success_keywords = ["已签到", "签到成功", "今天已签到", "已领取"]
            if any(k in page for k in success_keywords):
                clicked_success = True
                print("页面包含签到成功关键字，判断为签到成功。")
            else:
                # 尝试检查按钮是否变更为不可点击或文本变更
                try:
                    # 重新定位该元素（如果仍存在）
                    new_text = sign_in_button.text.strip()
                    print(f"点击后签到按钮文本: {new_text}")
                    if "已" in new_text or "成功" in new_text or "签到" in new_text and "已" in new_text:
                        clicked_success = True
                except Exception:
                    pass

            html_after, png_after = save_debug_artifacts(driver, "after_click")
            artifacts_to_upload.extend([html_after, png_after])

            if clicked_success:
                print("签到判定为成功。")
                send_notification("每日签到成功", "你今天已签到。")
            else:
                print("点击后未检测到签到成功的标志。")
                send_notification("签到未确认", "点击签到后未检测到成功标志，请查看页面截图和源码。")
        else:
            print("没有找到签到按钮。保存页面与截图以便排查。")
            html_f, png_f = save_debug_artifacts(driver, "no_button")
            artifacts_to_upload.extend([html_f, png_f])
            send_notification("签到失败-未找到按钮", "未找到签到按钮，请查看页面截图与源码。")

    except Exception as e:
        print(f"签到过程中出现错误: {e}")
        # 保存调试信息
        if driver:
            html_err, png_err = save_debug_artifacts(driver, "error")
            artifacts_to_upload.extend([html_err, png_err])
        send_notification("签到失败-异常", f"签到步骤发生异常: {e}")

finally:
    if driver is not None:
        print("正在关闭浏览器。")
        driver.quit()

    # 把 artifacts 列表写到文件，workflow 可以上传这些文件
    try:
        if artifacts_to_upload:
            with open("artifacts_list.txt", "w", encoding="utf-8") as f:
                for p in artifacts_to_upload:
                    f.write(p + "\n")
            print("artifacts_list.txt 已生成，包含要上传的文件名。")
    except Exception as e:
        print(f"生成 artifacts_list.txt 失败: {e}")
