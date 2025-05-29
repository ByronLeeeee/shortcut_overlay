# 显键

**显键** 是一款桌面应用程序，旨在通过一个屏幕上的虚拟键盘实时高亮显示特定于当前活动应用程序的键盘快捷键。这可以帮助用户学习和记住他们最常用程序的快捷键，从而提高工作效率。

该悬浮窗能够智能检测 Windows 系统上当前处于前台的活动应用程序，并相应地更新显示的快捷键。

[English Version (英文说明)](README.md)

## 功能特性

*   **实时快捷键显示**: 根据活动应用程序，在虚拟键盘上显示相关的快捷键。
*   **应用程序感知**: 自动检测前台应用程序 (特定于 Windows 系统)。
*   **可自定义主题**: 通过内置的多种主题或创建自定义配色方案来个性化悬浮窗的外观。
*   **可调节不透明度**: 控制悬浮窗口的透明度以适应个人偏好。
*   **多语言支持**: 用户界面已翻译成英文和简体中文。默认快捷键也包含基础翻译。
*   **可配置快捷键**: 快捷键定义通过一个可编辑的 `shortcuts.json` 文件管理，允许用户为任何应用程序添加或修改快捷键。
*   **用户设置**: 主题、不透明度、语言和自定义颜色等偏好设置保存在 `settings.json` 文件中。
*   **系统托盘集成**: 方便地在系统托盘中运行，并提供显示/隐藏悬浮窗、访问设置和退出应用程序的选项。
*   **跨平台潜力 (核心逻辑)**: 虽然前台应用程序监控目前特定于 Windows，但核心的用户界面和键盘处理逻辑可以适配其他平台。

## 系统需求

*   Python 3.10 +
*   `PySide6` (用于 Qt GUI)
*   `keyboard` 库 (用于全局键盘事件监听)
*   `pywin32` (用于 Windows 特定的前台应用程序监控)

## 安装与设置

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/byronleeeee/shortcut-overlay.git
    cd shortcut-overlay
    ```

2.  **创建并激活虚拟环境 (推荐):**
    ```bash
    python -m venv .venv
    # Windows 系统
    .venv\Scripts\activate
    # macOS/Linux 系统
    source .venv/bin/activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **运行应用程序:**
    ```bash
    python main.py
    ```

## 配置

*   **快捷键 (`config/shortcuts.json`)**:
    此 JSON 文件定义了快捷键。其结构如下：
    ```json
    {
      "可执行文件名.EXE": {
        "修饰键": {
          "按键": "描述 (或本地化对象)" 
        }
      },
      "DEFAULT": { /* 全局快捷键 */ }
    }
    ```
    示例:
    ```json
    {
      "NOTEPAD.EXE": {
        "Ctrl": {
          "S": {"en": "Save File", "zh": "保存文件"}
        }
      }
    }
    ```
    可执行文件名应为大写。修饰键可以是 "Ctrl", "Shift", "Alt", "Win", 或组合如 "Ctrl+Shift"。

*   **设置 (`config/settings.json`)**:
    存储用户偏好，如主题、不透明度、语言和自定义颜色。此文件由应用程序管理。

## 工作原理

1.  **前台监控器 (Foreground Monitor)**: 定时器周期性检查活动窗口，并使用 `pywin32` 获取进程的可执行文件名。
2.  **配置管理器 (Config Manager)**: 从 JSON 文件加载快捷键定义和用户设置。
3.  **键盘处理器 (Keyboard Handler)**: 使用 `keyboard` 库监听全局按键按下和修饰键更改。
4.  **悬浮窗口 (Overlay Window)**: 基于 Qt 的 GUI，显示一个虚拟键盘。
    *   接收关于活动应用和按键事件的信号。
    *   根据当前应用和活动的修饰键更新按键上显示的快捷键。
    *   应用配置的视觉主题和不透明度。
5.  **系统托盘图标 (System Tray Icon)**: 提供对应用程序功能的访问。

## 贡献

欢迎贡献！请随意 fork 本仓库，进行更改，并提交拉取请求。你也可以为 bug 或功能请求创建 issue。

## 许可证

本项目采用 MIT 许可证授权 - 详情请参阅 [LICENSE](LICENSE) 文件。