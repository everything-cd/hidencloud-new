# hidencloud-new
游戏机hidencloud自动续期
# 🕹️ HidenCloud 自动续期脚本（GitHub Actions 版）

这个仓库用于自动续期 HidenCloud 免费服务器。  
它通过 Playwright 自动打开网页、加载 Cookie 或账号密码、点击 Renew 按钮，实现无人值守续期。

---

## ✨ 功能说明

- 自动登录 HidenCloud（支持 Cookie 或 邮箱+密码）
- 自动进入服务管理页面
- 自动检测是否出现 Renew 按钮
- 到期前 1 天内自动续期（HidenCloud 官方要求）
- 自动截图错误信息（Playwright）
- 支持 GitHub Actions 定时运行（cron）

---

## 📦 文件说明

本仓库包含以下内容：

- `renew_service.py`  
  主续期脚本，使用 Playwright 自动执行登录和续期动作。

- `.github/workflows/renew.yml`  
  GitHub Actions 自动化配置，定时执行脚本。

---

## 🔑 配置 Secrets（必做）

脚本需要登录信息，你必须在 GitHub 仓库配置 Secrets：

路径：  
`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下内容：

| Secret 名称 | 说明 |
|------------|------|
| `HIDENCLOUD_COOKIE` | 登录 Cookie（推荐方式） |
| `HIDENCLOUD_EMAIL` | 账号邮箱（可选） |
| `HIDENCLOUD_PASSWORD` | 账号密码（可选） |

### 🔧 注意：
如果你使用 **Cookie 登录**，可以只填写 `HIDENCLOUD_COOKIE`，并在代码里关闭账号密码登录逻辑。

如果你使用 **邮箱密码登录**，可以不填 Cookie。

---

## 🕒 默认续期时间（cron）

当前仓库的 `.github/workflows/renew.yml` 设置为：

0 2 * * *

yaml
复制代码

含义：

- **每天 UTC 时间 02:00 自动运行一次**
- 如果你的时区是 **UTC+8**（北京 / 新加坡 / 马来西亚等）
  则执行时间为 **每天早上 10 点**

HidenCloud 的续期按钮只会在：

⚠️ **到期前不到 1 天时** 才出现

所以脚本每天运行一次，就一定会覆盖续期窗口。

---

## 🔄 如何修改自动运行时间

你可以编辑 `.github/workflows/renew.yml` 中的这行：

cron: '0 2 * * *'

yaml
复制代码

示例修改：

| 想要的执行时间 | cron 写法 | 说明 |
|----------------|-----------|------|
| 每 6 小时运行一次（最稳） | `0 */6 * * *` | 推荐设置 |
| 每天凌晨 1 点 | `0 1 * * *` | 提前续期 |
| 每天中午 12 点 | `0 12 * * *` | 自定义 |
| 每小时运行一次 | `0 * * * *` | 最高频率 |

Cron 使用的是 **UTC 时间**，记得换算你的时区。

---

## 🚀 启动自动续期

你配置完 Secrets 后，GitHub Actions 会自动启用。  
你也可以手动执行：

路径：  
`Actions` → `HidenCloud Auto Renew` → `Run workflow`

运行成功后，你将看到：

Cookie 登录成功！
开始访问服务管理页面...
找到 Renew 按钮，准备点击！
续期成功！

yaml
复制代码

如果按钮没出现（还没到续期时间），脚本会自动退出并上传截图，不会出错。

---

## 🧩 常见问题

### 1. 为什么显示找不到 Renew 按钮？
因为你还没进入续期窗口。

HidenCloud 规定：

✔ **只有到期前 < 1 天，按钮才会出现**  
在此之前运行脚本会提示按钮不存在，属于正常行为。

---

### 2. 怎样查看脚本运行截图？
路径：

`Actions` → 运行记录 → Artifacts → 下载截图文件

里面会包含 Playwright 自动截图。

---

## 📌 小提示

- 建议把 cron 改成 **每 6 小时一次**，成功率最高  
- Cookie 登录比账号密码更稳定  
- Renew 按钮消失后，脚本会自动退出，不会报错

---

## 🎉 结语

只要配置好 Secrets，脚本就能天天帮你续期，不用再担心忘记续费导致服务器被删。  
如果你需要增加功能，例如自动检测 Cookie 失效、自动 Telegram 通知，我也可以帮你加！
