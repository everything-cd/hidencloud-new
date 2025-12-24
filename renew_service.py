import os
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================= 全局配置 =================
HIDENCLOUD_COOKIE = os.environ.get("HIDENCLOUD_COOKIE")
HIDENCLOUD_EMAIL = os.environ.get("HIDENCLOUD_EMAIL")
HIDENCLOUD_PASSWORD = os.environ.get("HIDENCLOUD_PASSWORD")

BASE_URL = "https://dash.hidencloud.com"
LOGIN_URL = f"{BASE_URL}/auth/login"
SERVICE_URL = f"{BASE_URL}/service/85242/manage"

COOKIE_NAME = "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d"


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ================= 登录逻辑 =================
def login(page):
    log("开始登录流程...")

    # ---------- Cookie 登录 ----------
    if HIDENCLOUD_COOKIE:
        try:
            log("检测到 HIDENCLOUD_COOKIE，尝试 Cookie 登录")
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

            if "auth/login" not in page.url:
                log("✅ Cookie 登录成功")
                return True

            log("Cookie 失效，回退账号密码登录")
            page.context.clear_cookies()

        except Exception as e:
            log(f"Cookie 登录异常: {e}")
            page.context.clear_cookies()

    # ---------- 账号密码 ----------
    if not HIDENCLOUD_EMAIL or not HIDENCLOUD_PASSWORD:
        log("❌ 无可用登录方式")
        return False

    try:
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)

        page.fill('input[name="email"]', HIDENCLOUD_EMAIL)
        page.fill('input[name="password"]', HIDENCLOUD_PASSWORD)

        log("处理 Cloudflare Turnstile")
        frame = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
        checkbox = frame.locator('input[type="checkbox"]')
        checkbox.wait_for(state="visible", timeout=30000)
        checkbox.click()

        page.wait_for_function(
            "() => document.querySelector('[name=\"cf-turnstile-response\"]')?.value",
            timeout=60000
        )

        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        if "auth/login" in page.url:
            raise RuntimeError("登录失败")

        log("✅ 账号密码登录成功")
        return True

    except Exception as e:
        log(f"❌ 登录失败: {e}")
        page.screenshot(path="login_error.png")
        return False


# ================= 续费逻辑（SPA 稳定版） =================
def renew_service(page):
    try:
        log("开始执行续费任务...")

        if page.url != SERVICE_URL:
            page.goto(SERVICE_URL, wait_until="networkidle", timeout=60000)

        log("服务管理页面已加载")

        # -------- Step 1: Renew --------
        log("步骤 1: 点击 Renew")
        renew_btn = page.locator('button:has-text("Renew")')
        renew_btn.wait_for(state="visible", timeout=30000)
        renew_btn.click()

        # -------- Step 2: Create Invoice --------
        log("步骤 2: 点击 Create Invoice")
        create_btn = page.locator('button:has-text("Create Invoice")')
        create_btn.wait_for(state="visible", timeout=30000)
        create_btn.click()

        # -------- Step 3: 等待 SPA 路由完成（Pay 出现）--------
        log("步骤 3: 等待发票页面 Pay 按钮出现")

        pay_btn = page.locator('button:has-text("Pay")')

        pay_btn.wait_for(state="attached", timeout=60000)
        pay_btn.wait_for(state="visible", timeout=60000)
        pay_btn.wait_for(state="enabled", timeout=60000)

        log("✅ Pay 按钮已出现")

        pay_btn.click()
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


# ================= 主入口 =================
def main():
    if not HIDENCLOUD_COOKIE and not (HIDENCLOUD_EMAIL and HIDENCLOUD_PASSWORD):
        log("❌ 缺少登录凭据")
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
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/114.0.0.0 Safari/537.36"
                )
            )

            page = context.new_page()

            if not login(page):
                sys.exit(1)

            if not renew_service(page):
                sys.exit(1)

            log("🎉 自动化续费流程完成")

        finally:
            log("关闭浏览器")
            if browser:
                browser.close()


if __name__ == "__main__":
    main()
