# Shortcut Overlay

**Shortcut Overlay** is a desktop application designed to display an on-screen keyboard that highlights application-specific keyboard shortcuts in real-time. This helps users learn and remember shortcuts for their most-used programs, boosting productivity.

The overlay intelligently detects the currently active foreground application on Windows and updates the displayed shortcuts accordingly.

[中文说明 (Chinese Version)](README_zh.md)

## Features

*   **Real-time Shortcut Display**: Shows relevant shortcuts on a virtual keyboard based on the active application.
*   **Application-Aware**: Automatically detects the foreground application (Windows-specific).
*   **Customizable Themes**: Personalize the look of the overlay with various built-in themes or create your own custom color scheme.
*   **Adjustable Opacity**: Control the transparency of the overlay window to suit your preference.
*   **Multi-language Support**: UI translated into English and Simplified Chinese. Default shortcuts also include basic translations.
*   **Configurable Shortcuts**: Shortcut definitions are managed via an editable `shortcuts.json` file, allowing users to add or modify shortcuts for any application.
*   **User Settings**: Preferences for theme, opacity, language, and custom colors are saved in `settings.json`.
*   **System Tray Integration**: Runs conveniently in the system tray with options to show/hide the overlay, access settings, and exit.
*   **Cross-Platform Potential (Core Logic)**: While foreground app monitoring is currently Windows-specific, the core UI and keyboard handling can be adapted for other platforms.

## Prerequisites

*   Python 3.10 +
*   PySide6 (for the Qt GUI)
*   `keyboard` library (for global keyboard event listening)
*   `pywin32` (for Windows-specific foreground application monitoring)

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/byronleeeee/shortcut-overlay.git
    cd shortcut-overlay
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

## Configuration

*   **Shortcuts (`config/shortcuts.json`)**:
    This JSON file defines the shortcuts. The structure is:
    ```json
    {
      "EXECUTABLE_NAME.EXE": {
        "ModifierKeys": {
          "Key": "Description (or localized object)" 
        }
      },
      "DEFAULT": { /* Global shortcuts */ }
    }
    ```
    Example:
    ```json
    {
      "NOTEPAD.EXE": {
        "Ctrl": {
          "S": {"en": "Save File", "zh": "保存文件"}
        }
      }
    }
    ```
    Executable names should be in uppercase. Modifiers can be "Ctrl", "Shift", "Alt", "Win", or combinations like "Ctrl+Shift".

*   **Settings (`config/settings.json`)**:
    Stores user preferences like theme, opacity, language, and custom colors. This file is managed by the application.

## How it Works

1.  **Foreground Monitor**: A timer periodically checks the active window and uses `pywin32` to get the process executable name.
2.  **Config Manager**: Loads shortcut definitions and user settings from JSON files.
3.  **Keyboard Handler**: Uses the `keyboard` library to listen for global key presses and modifier changes.
4.  **Overlay Window**: A Qt-based GUI that displays a virtual keyboard.
    *   It receives signals about the active app and key events.
    *   It updates the displayed shortcuts on the keys based on the current app and active modifiers.
    *   It applies visual themes and opacity as configured.
5.  **System Tray Icon**: Provides access to application functions.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request. You can also open issues for bugs or feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.