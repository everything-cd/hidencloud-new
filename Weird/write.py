import os
import time
import sys
import random
from playwright.sync_api import sync_playwright

BASE_URL = "https://hub.weirdhost.xyz"
LOGIN_URL = f"{BASE_URL}/auth/login"
SERVER_URL = f"{BASE_URL}/server/6c087e9b/"
BUTTON_TEXT = "시간추가"

# 仅使用这三个环境变量（已改为 WEIRD_*）
WEIRD_COOKIE = os.environ.get('WEIRD_COOKIE', '').strip()
WEIRD_EMAIL = os.environ.get('WEIRD_EMAIL', '').strip()
WEIRD_PASSWORD = os.environ.get('WEIRD_PASSWORD', '').strip()

def log(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en'] });
"""

def parse_cookie_name_value(raw_value: str):
    """
    支持两种方式:
    1) WEIRD_COOKIE="name=value"
    2) WEIRD_COOKIE="value"（将猜测 name 为 remember_web_）
    """
    if "=" in raw_value:
        name, value = raw_value.split("=", 1)
        return name.strip(), value.strip()
    return "remember_web_", raw_value  # 猜测 Laravel remember_web_ 前缀

def handle_cloudflare(page):
    cf_iframe_sel = 'iframe[src*="challenges.cloudflare"]'
    def present():
        return page.locator(cf_iframe_sel).count() > 0 or \
               page.locator('.cf-challenge, .cf-turnstile').count() > 0

    if not present():
        return True

    log("⚠️ 检测到 Cloudflare 验证，开始处理...")
    start = time.time()
    while time.time() - start < 120:
        if not present():
            log("✅ Cloudflare 验证通过！")
            return True
        try:
            frame = None
            for f in page.frames:
                try:
                    if "challenges.cloudflare" in (f.url or ""):
                        frame = f
                        break
                except:
                    pass
            if frame:
                cb = frame.locator('input[type="checkbox"]').first
                if cb.count() and cb.is_visible():
                    log("🔍 找到验证复选框（iframe），尝试点击...")
                    time.sleep(random.uniform(0.5, 1.2))
                    cb.click(force=True)
                    log("🕒 已点击，等待验证完成...")
                    time.sleep(random.uniform(3, 6))
        except Exception as e:
            log(f"⚠️ 验证处理中遇到小问题: {e}")
        time.sleep(2)
    log("❌ Cloudflare 验证等待超时")
    return False

def try_cookie_login(page):
    if not WEIRD_COOKIE:
        return False

    name, value = parse_cookie_name_value(WEIRD_COOKIE)
    log(f"🍪 尝试使用 Cookie 登录（name={name}）...")

    try:
        page.context.add_cookies([{
            "name": name,
            "value": value,
            "domain": "hub.weirdhost.xyz",
            "path": "/",
            "expires": int(time.time()) + 3600 * 24 * 180,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }])

        page.goto(SERVER_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)

        if "/auth/login" not in page.url:
            log("✅ Cookie 登录成功！")
            return True

        log("⚠️ Cookie 失效或权限不足，被重定向至登录页。")
        return False
    except Exception as e:
        log(f"❌ Cookie 登录异常: {e}")
        try: page.screenshot(path="cookie_login_error.png")
        except: pass
        return False

def login_with_password(page):
    if not WEIRD_EMAIL or not WEIRD_PASSWORD:
        log("❌ 未提供账号密码，无法回退登录。")
        return False

    log("🚀 尝试账号密码登录...")
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)

        log("✉️ 输入邮箱...")
        email_input = page.locator('input[name="email"], input[type="email"]').first
        email_input.wait_for(state="visible", timeout=15000)
        email_input.fill(WEIRD_EMAIL)

        log("🔑 输入密码...")
        pwd_input = page.locator('input[name="password"], input[type="password"]').first
        pwd_input.wait_for(state="visible", timeout=15000)
        pwd_input.fill(WEIRD_PASSWORD)

        time.sleep(random.uniform(0.5, 1.2))
        handle_cloudflare(page)

        log("✅ 点击登录按钮...")
        login_btn = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("로그인")').first
        login_btn.wait_for(state="visible", timeout=15000)
        login_btn.scroll_into_view_if_needed()
        login_btn.click()

        log("⏳ 等待跳转...")
        page.wait_for_url(f"{BASE_URL}/**", timeout=45000)

        if not handle_cloudflare(page):
            return False

        if "/auth/login" in page.url:
            log("❌ 登录失败：仍在登录页")
            page.screenshot(path="login_failed.png")
            return False

        log("🎉 账号密码登录成功！")
        return True

    except Exception as e:
        log(f"💥 登录异常: {e}")
        try: page.screenshot(path="login_error.png")
        except: pass
        return False

def add_time(page):
    log("🎯 进入续期流程（点击 '시간추가'）...")
    try:
        if page.url != SERVER_URL:
            log(f"📍 跳转到服务器页面: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded", timeout=60000)

        if not handle_cloudflare(page):
            return False

        log(f"🔍 寻找 '{BUTTON_TEXT}' 按钮...")
        candidate_selectors = [
            f'button:has-text("{BUTTON_TEXT}")',
            f'span:has-text("{BUTTON_TEXT}")',
            'button.Button__ButtonStyle-sc-1qu1gou-0',
            'button[class*="Button__ButtonStyle"]',
            f'button:has(span:has-text("{BUTTON_TEXT}"))'
        ]

        time_add_btn = None
        for sel in candidate_selectors:
            loc = page.locator(sel).first
            try:
                if loc.count() > 0:
                    if "span" in sel:
                        btn = loc.locator('xpath=ancestor::button[1]')
                        if btn.count() > 0:
                            time_add_btn = btn.first
                            break
                    else:
                        time_add_btn = loc
                        break
            except:
                pass

        if not time_add_btn:
            log("❌ 未找到 '时间增加' 按钮（时间追加/시간추가）")
            page.screenshot(path="time_add_not_found.png")
            return False

        for attempt in range(5):
            try:
                time_add_btn.wait_for(state="visible", timeout=15000)
                time_add_btn.scroll_into_view_if_needed()
                log(f"🖱️ 第 {attempt+1} 次尝试点击 '{BUTTON_TEXT}'...")
                time_add_btn.click()
                log("✅ 已点击，等待页面响应/验证...")

                if not handle_cloudflare(page):
                    log("⚠️ Cloudflare 未通过，本次点击可能未生效，准备重试...")
                    time.sleep(3)
                    continue

                time.sleep(random.uniform(2.5, 4.5))
                log("🎉 续期流程已执行！如需更严格成功校验，可告诉我页面的成功提示标识。")
                return True

            except Exception as e:
                log(f"⚠️ 点击尝试失败（第 {attempt+1} 次）: {e}")
                time.sleep(3)

        log("❌ 多次尝试后仍无法完成续期流程")
        page.screenshot(path="time_add_failed.png")
        return False

    except Exception as e:
        log(f"💥 续期异常: {e}")
        try: page.screenshot(path="renew_error.png")
        except: pass
        return False

def main():
    with sync_playwright() as p:
        browser = None
        try:
            log("🌐 启动 Chrome（可见模式）...")
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="ko-KR"
            )
            page = context.new_page()
            page.add_init_script(STEALTH_JS)

            # 1) Cookie 优先
            if not try_cookie_login(page):
                # 2) 回退账号密码
                if not login_with_password(page):
                    log("💥 登录失败，退出")
                    sys.exit(1)

            if not add_time(page):
                log("💥 续期失败，退出")
                sys.exit(1)

            log("🎊 任务完成：自动续期成功！")

        except Exception as e:
            log(f"💥 严重错误: {e}")
            sys.exit(1)
        finally:
            if browser:
                log("🔒 关闭浏览器...")
                browser.close()

if __name__ == "__main__":
    main()
