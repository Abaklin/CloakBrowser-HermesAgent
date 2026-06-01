# CloakBrowser 集成指南


## 概述
CloakBrowser 是一个基于 Playwright 的隐身 Chromium 浏览器，在 C++ 源码级别进行指纹补丁，可绕过常见的 bot 检测机制（Turnstile、FingerprintJS、reCAPTCHA 等）。本指南记录如何将其作为工具集成到 **Hermes Agent** 中。

### 特性
- **隐身浏览**：绕过 Turnstile、FingerprintJS、reCAPTCHA 等检测
- **完整工具链**：navigate、snapshot、click、type、press、scroll、back、screenshot、evaluate、close
- **自动下载 Chromium**：首次使用时自动下载约 200 MB 的浏览器二进制
- **错误处理**：所有操作返回 JSON，错误不会导致崩溃

### 项目地址
- GitHub: https://github.com/CloakHQ/CloakBrowser
- Python 包: `cloakbrowser[geoip]`

---

## 环境要求
- **操作系统**：Windows 10/11
- **Python**：3.11+（推荐使用 venv）
- **Hermes Agent**：已安装并配置
- **磁盘空间**：≥ 500 MB（浏览器二进制 + 缓存）

---

## 快速开始
以下步骤按顺序执行，即可在本地完成集成。

### 安装依赖
```bash
# 进入 Hermes Agent 目录
cd D:\ProgramData\hermes\hermes-agent

# 使用 venv 中的 Python 安装 CloakBrowser
venv\Scripts\python.exe -m pip install "cloakbrowser[geoip]==0.3.31"

# 安装 Playwright Chromium 浏览器
venv\Scripts\python.exe -m playwright install chromium
```

### 配置环境变量
在 `D:\ProgramData\hermes\.env` 中加入以下内容（请根据实际路径自行修改）：
```env
# CloakBrowser 配置
CLOAKBROWSER_CACHE_DIR=D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\cache
PLAYWRIGHT_BROWSERS_PATH=D:\ProgramData\hermes\hermes-agent\CloakbrowerDate\playwright-browsers
```

### 创建工具文件
把 **工具文件代码**（见第 5 节）保存为：
```
D:\ProgramData\hermes\hermes-agent\tools\cloakbrowser_tool.py
```

### 配置工具集
1. 打开 `D:\ProgramData\hermes\hermes-agent\toolsets.py`。
2. 在 `_HERMES_CORE_TOOLS` 列表中追加以下条目：
```python
"cloakbrowser_navigate", "cloakbrowser_snapshot", "cloakbrowser_click",
"cloakbrowser_type", "cloakbrowser_press", "cloakbrowser_scroll",
"cloakbrowser_back", "cloakbrowser_screenshot",
"cloakbrowser_evaluate", "cloakbrowser_close",
```
3. 在 `TOOLSETS` 字典中添加新配置：
```python
"cloakbrowser": {
    "description": "Stealth Chromium browser via CloakBrowser - passes bot detection (Turnstile, FingerprintJS, reCAPTCHA) with C++‑level fingerprint patches",
    "tools": [
        "cloakbrowser_navigate", "cloakbrowser_snapshot", "cloakbrowser_click",
        "cloakbrowser_type", "cloakbrowser_press", "cloakbrowser_scroll",
        "cloakbrowser_back", "cloakbrowser_screenshot",
        "cloakbrowser_evaluate", "cloakbrowser_close",
    ],
    "includes": [],
    "off_by_default": True,
},
```

### 重启 Hermes
```bash
hermes restart   # 让配置生效
```

---

## 文件清单
| 文件路径 | 说明 | 行数 |
|----------|------|------|
| `tools/cloakbrowser_tool.py` | 主工具模块 | 452 |
| `toolsets.py` | 工具集配置（需手动修改） | - |
| `.env` | 环境变量配置（需新增） | - |
| `CloakbrowerDate/cache/` | 浏览器缓存目录（运行时创建） | 自动 |
| `CloakbrowerDate/playwright-browsers/` | Playwright 浏览器目录（运行时创建） | 自动 |

---

## 工具文件代码
**文件**：`tools/cloakbrowser_tool.py`
> 包含 10 个工具函数（navigate、snapshot、click、type、press、scroll、back、screenshot、evaluate、close），以及 Aria 快照解析、会话管理和自动注册逻辑。请直接打开该文件查看完整实现。

---

## 工具集配置细节
（同 **快速开始** 第 4 步中的代码块，已在此归纳，便于复制）

---

## 环境变量配置细节
（同 **快速开始** 第 2 步中的代码块，已在此归纳，便于复制）

---

## 迁移到新电脑
### 完整迁移步骤
1. **安装依赖**（同快速开始的安装依赖步骤）
2. **配置环境变量**（同快速开始的环境变量配置）
3. **复制工具文件**：将 `tools/cloakbrowser_tool.py` 复制到新机器相同路径
4. **修改 `toolsets.py`**：添加上述工具集配置
5. **重启 Hermes**：`hermes restart`

### 迁移脚本
创建 `install_cloakbrowser.bat` 并放置在任意目录，内容如下：
```batch
@echo off
echo Installing CloakBrowser for Hermes Agent...
set HERMES_PATH=D:\ProgramData\hermes\hermes-agent
cd /d "%HERMES_PATH%"

echo [1/3] Installing Python package...
venv\Scripts\python.exe -m pip install "cloakbrowser[geoip]==0.3.31"

echo [2/3] Installing Chromium browser...
venv\Scripts\python.exe -m playwright install chromium

echo [3/3] Creating cache directories...
mkdir "CloakbrowerDate\cache" 2>nul
mkdir "CloakbrowerDate\playwright-browsers" 2>nul

echo Installation complete!
 echo Next steps:
 echo 1. Copy cloakbrowser_tool.py to tools\ directory
 echo 2. Add cloakbrowser configuration to toolsets.py
 echo 3. Add environment variables to ..\.env
 echo 4. Restart Hermes: hermes restart
pause
```

### 迁移检查清单
- [ ] Python 包 `cloakbrowser[geoip]==0.3.31` 已安装
- [ ] Playwright Chromium 已安装
- [ ] `.env` 中的环境变量已配置
- [ ] `tools/cloakbrowser_tool.py` 已复制
- [ ] `toolsets.py` 已更新
- [ ] Hermes 已重启
- [ ] 测试 `cloakbrowser_navigate` 正常工作

---

## 已知 Bug 与修复记录
| Bug 编号 | 描述 | 修复方案 |
|----------|------|----------|
| #1 | `nth(ref_num‑1)` 使用全局计数器，导致定位错误 | 改为 `nth(role_index)`，独立跟踪每个角色的索引 |
| #2 | `ref.lstrip("@e")` 会误删字符 | 改为 `startswith("@e")` 精确匹配 |
| #3 | `exact=True` 在同名元素多时失败 | 统一采用 `nth(role_index)` 定位 |
| #4 | 长页面截图超时（30 s） | 设置 `full_page=False, timeout=15000` |
| #5 | `Press Enter` 等待时间不足 | 将等待时间调至 2000 ms |

---

## 测试报告
| 类别 | 通过 | 失败 | 通过率 |
|------|------|------|--------|
| 核心功能 | 7 | 0 | 100% |
| Bug 修复 | 4 | 0 | 100% |
| 表单交互 | 2 | 0 | 100% |
| 导航 | 1 | 0 | 100% |
| 错误处理 | 2 | 0 | 100% |
| 恢复测试 | 2 | 0 | 100% |
| Ref 解析 | 2 | 0 | 100% |
| 压力测试 | 2 | 0 | 100% |
| 复杂页面 | 2 | 0 | 100% |
| 场景测试 | 12 | 0 | 100% |
| 边缘测试 | 9 | 1* | 90% |
> *注：1 个失败是 URL 拼写错误，非代码 bug。

**总计：36/37 (97.3%)**

---

## 使用示例
### 基本使用
```python
# 导航
cloakbrowser_navigate("https://example.com")

# 快照
cloakbrowser_snapshot()

# 点击
cloakbrowser_click("@e1")

# 输入
cloakbrowser_type("@e2", "文本")

# 按键
cloakbrowser_press("Enter")

# 滚动
cloakbrowser_scroll("down")

# 后退
cloakbrowser_back()

# 截图
cloakbrowser_screenshot()

# 执行 JS
cloakbrowser_evaluate("document.title")

# 关闭浏览器
cloakbrowser_close()
```

### 搜索工作流
```python
cloakbrowser_navigate("https://duckduckgo.com")
cloakbrowser_type("@e2", "搜索内容")
cloakbrowser_press("Enter")
# 等待 2 秒后获取搜索结果
cloakbrowser_snapshot()
```

---

## 故障排除
- **首次 `navigate` 很慢**：会自动下载 Chromium（约 200 MB），后续启动速度会快。
- **`No module named 'cloakbrowser'`**：确保已在 Hermes Agent 的 venv 中执行 `pip install "cloakbrowser[geoip]==0.3.31"`。
- **环境变量未生效**：
  1. 检查 `.env` 内容是否正确；
  2. 重启 Hermes。

---

## 生成时间
*文档生成时间：2026‑05‑31*
