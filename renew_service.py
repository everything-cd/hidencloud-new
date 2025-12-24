import os
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- 全局配置 ---
HIDENCLOUD_COOKIE = os.environ.get('HIDENCLOUD_COOKIE')
HIDENCLOUD_EMAIL = os.environ.get('HIDENCLOUD_EMAIL')
HIDENCLOUD_PASSWORD = os.environ.get('HIDENCLOUD_PASSWORD')

BASE_URL = "https://dash.hidencloud.com"
LOGIN_URL = f"{BASE_URL}/auth/login"
SERVICE_URL = f"{BASE_URL}/service/85242/manage"

COOKIE_NAME = "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d"


def log(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def login(page):
    log("开始登录流程...")

    # --- Cookie 登录 ---
    if HIDENCLOUD_COOKIE:
        log("检测到 HIDENCLOUD_COOKIE，尝试使用 Cookie 登录。")
        try:
            page.context.add_cookies([{
                "name": COOKIE_NAME,
                "value": HIDENCLOUD_COOKIE,
                "domain": "dash.hidencloud.com",
                "path": "/",
                "expires": int(time.time()) + 3600 * 24 * 365,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }])

            page.goto(SERVICE_URL, wait_until="networkidle", timeout=60000)

            if "auth/login" in page.url:
                log("Cookie 登录失败，回退账号密码登录。")
                page.context.clear_cookies()
            else:
                log("✅ Cookie 登录成功！")
                return True
        except Exception as e:
            log(f"Cookie 登录异常: {e}")
            page.context.clear_cookies()

    # --- 账号密码登录 ---
    if not HIDENCLOUD_EMAIL or not HIDENCLOUD_PASSWORD:
        log("❌ 未提供登录凭据。")
        return False

    try:
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
        page.fill('input[name="email"]', HIDENCLOUD_EMAIL)
        page.fill('input[name="password"]', HIDENCLOUD_PASSWORD)

        log("处理 Cloudflare Turnstile...")
        turnstile_frame = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
        checkbox = turnstile_frame.locator('input[type="checkbox"]')
        checkbox.wait_for(state="visible", timeout=30000)
        checkbox.click()

        page.wait_for_function(
            "() => document.querySelector('[name=\"cf-turnstile-response\"]')?.value",
            timeout=60000
        )

        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=60000)

        log("✅ 账号密码登录成功！")
        return True

    except Exception as e:
        log(f"❌ 登录失败: {e}")
        page.screenshot(path="login_error.png")
        return False


def renew_service(page):
    try:
        log("开始执行续费任务...")

        if page.url != SERVICE_URL:
            page.goto(SERVICE_URL, wait_until="networkidle", timeout=60000)

        log("服务管理页面已加载。")

        # --- Step 1: Renew ---
        log("步骤 1: 点击 Renew")
        renew_button = page.locator('button:has-text("Renew")')
        renew_button.wait_for(state="visible", timeout=30000)
        renew_button.click()

        # --- Step 2: Create Invoice + 等待跳转 ---
        log("步骤 2: 点击 Create Invoice 并等待跳转到发票页面")

        create_invoice_button = page.locator('button:has-text("Create Invoice")')
        create_invoice_button.wait_for(state="visible", timeout=30000)

        with page.expect_navigation(wait_until="networkidle", timeout=60000):
            create_invoice_button.click()

        log(f"已跳转至发票页面: {page.url}")

        # --- Step 3: Pay ---
        log("步骤 3: 查找并点击 Pay")

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # 防止支付 SDK 慢加载

        pay_button = page.locator('button:has-text("Pay")')
        pay_button.wait_for(state="visible", timeout=30000)
        pay_button.wait_for(state="enabled", timeout=30000)
        pay_button.click()

        log("✅ Pay 按钮已点击")
        page.screenshot(path="renew_success.png")
        return True

    except PlaywrightTimeoutError as e:
        log(f"❌ 续费流程超时: {e}")
        page.screenshot(path="renew_timeout.png")
        return False

    except Exception as e:
        log(f"❌ 续费流程异常: {e}")
        page.screenshot(path="renew_error.png")
        return False


def main():
    if not HIDENCLOUD_COOKIE and not (HIDENCLOUD_EMAIL and HIDENCLOUD_PASSWORD):
        log("❌ 缺少登录凭据，退出。")
        sys.exit(1)

    with sync_playwright() as p:
        browser = None
        try:
            log("启动浏览器...")
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )

            page = context.new_page()

            if not login(page):
                sys.exit(1)

            if not renew_service(page):
                sys.exit(1)

            log("🎉 自动化续费任务完成")

        finally:
            log("关闭浏览器")
            if browser:
                browser.close()


if __name__ == "__main__":
    main()
