# Shortcut Overlay - Usage Guide

This guide provides detailed instructions on how to use and configure the Shortcut Overlay application.

## Table of Contents

- [Shortcut Overlay - Usage Guide](#shortcut-overlay---usage-guide)
  - [Table of Contents](#table-of-contents)
  - [1. Running the Application](#1-running-the-application)
  - [2. Using the System Tray Icon](#2-using-the-system-tray-icon)
  - [3. Understanding the Overlay Keyboard](#3-understanding-the-overlay-keyboard)
  - [4. Configuring Settings](#4-configuring-settings)
    - [Theme Selection](#theme-selection)
    - [Custom Theme Colors](#custom-theme-colors)
    - [Opacity Adjustment](#opacity-adjustment)
    - [Language Selection](#language-selection)
  - [5. Customizing Shortcuts (`shortcuts.json`)](#5-customizing-shortcuts-shortcutsjson)
    - [File Structure](#file-structure)
    - [Finding Executable Names](#finding-executable-names)
    - [Defining Modifier Keys](#defining-modifier-keys)
    - [Defining "NoModifier" Keys](#defining-nomodifier-keys)
    - [Key Naming Conventions](#key-naming-conventions)
    - [Localized Descriptions](#localized-descriptions)
    - [Adding New Applications](#adding-new-applications)
    - [Example: Adding a Word Shortcut](#example-adding-a-word-shortcut)
  - [6. Troubleshooting](#6-troubleshooting)

## 1. Running the Application

Follow the [Installation & Setup instructions in the main README.md](https://github.com/byronleeeee/shortcut-overlay/blob/main/README.md#installation--setup) to run the application. Once started, the overlay keyboard should appear on your screen, and an icon will be added to your system tray.

## 2. Using the System Tray Icon

**Right-clicking** the Shortcut Overlay icon in the system tray provides the following options:

*   **Show/Hide Overlay**: Toggles the visibility of the on-screen keyboard.
*   **Settings...**: Opens the settings dialog to customize appearance and behavior.
*   **About...**: Displays information about the application.
*   **Exit**: Closes the application.

Double-clicking the tray icon also toggles the Show/Hide state of the overlay.

## 3. Understanding the Overlay Keyboard

The on-screen keyboard displays common keys. When you press modifier keys (Ctrl, Shift, Alt, Win), or when a specific application is in the foreground, the keys on the overlay will update to show relevant shortcut descriptions.

*   **Keycap Text**: The main text on the key (e.g., "A", "Ctrl", "F1").
*   **Shortcut Description**: Smaller text appearing below the keycap text, describing the shortcut function. This text is context-aware.
*   **Highlighted Shortcuts**: When a modifier combination is active (e.g., Ctrl is held down), the shortcut descriptions for that combination will have a highlighted background for better visibility.

The overlay window can be dragged to any position on your screen by clicking and dragging any part of it that isn't a key or the resize grip. You can resize the window using the grip in the bottom-right corner.

## 4. Configuring Settings

Access the settings dialog via the system tray icon (`Settings...`). Changes made here are applied instantly.

### Theme Selection

*   **Theme**: Choose from a list of pre-defined visual themes for the overlay keyboard (e.g., "Default Dark", "Light Steel"). The "Custom..." theme allows for personalized colors.

### Custom Theme Colors

If you select the "Custom..." theme, the following options become available:

*   **Background Color...**: Sets the main background color of the overlay window. Supports alpha transparency.
*   **Key Color...**: Sets the background color of individual key widgets on the overlay. Supports alpha transparency.
*   **Key Text Color...**: Sets the color of the keycap text (e.g., "Ctrl", "A") and the shortcut description text.

Click each button to open a color picker.

### Opacity Adjustment

*   **Window Opacity**: Use the slider to adjust the overall transparency of the overlay window, from 20% (very transparent) to 100% (fully opaque).

### Language Selection

*   **Interface Language**: Choose between "English" and "简体中文" (Simplified Chinese) for the application's user interface (dialogs, menus) and default shortcut descriptions.

## 5. Customizing Shortcuts (`shortcuts.json`)

The power of Shortcut Overlay lies in its customizable shortcut definitions. These are stored in the `config/shortcuts.json` file located in the application's installation directory. You can edit this file with any text editor.

**Important:** It's recommended to back up your `shortcuts.json` file before making significant changes. If the file becomes corrupted or is deleted, the application will generate a default one on the next startup.

### File Structure

The `shortcuts.json` file is a JSON object. The top-level keys are application executable names (in **UPPERCASE**) or the special key `"DEFAULT"`.

```json
{
  "APPLICATION_NAME_1.EXE": {
    // ... shortcuts for App1
  },
  "APPLICATION_NAME_2.EXE": {
    // ... shortcuts for App2
  },
  "DEFAULT": {
    // ... global shortcuts or fallbacks
  }
}
```

### Finding Executable Names

To add shortcuts for a new application, you need its exact executable name (e.g., `PHOTOSHOP.EXE`, `MY_APP.EXE`). You can usually find this by:
1.  Running the application.
2.  Opening Task Manager (Ctrl+Shift+Esc).
3.  Finding the application in the "Processes" or "Details" tab.
4.  Noting the "Image name" or "Executable name".
Use this name, **converted to uppercase**, as the key in `shortcuts.json`.

### Defining Modifier Keys

Within each application (or "DEFAULT"), keys are modifier combinations like `"Ctrl"`, `"Shift"`, `"Alt"`, `"Win"`, `"Ctrl+Shift"`, `"Ctrl+Alt"`, etc.

```json
"NOTEPAD.EXE": {
  "Ctrl": { // When Ctrl is held
    "S": {"en": "Save", "zh": "保存"}, // Ctrl+S
    "O": {"en": "Open", "zh": "打开"}  // Ctrl+O
  },
  "Ctrl+Shift": { // When Ctrl and Shift are held
    "S": {"en": "Save As", "zh": "另存为"} // Ctrl+Shift+S
  }
}
```

### Defining "NoModifier" Keys

For shortcuts that don't require Ctrl, Shift, Alt, or Win to be pressed (e.g., F1 for Help, or single-letter tool shortcuts in some apps), use the special modifier key `"NoModifier"`:

```json
"PHOTOSHOP.EXE": {
  "NoModifier": {
    "V": {"en": "Move Tool", "zh": "移动工具"},
    "B": {"en": "Brush Tool", "zh": "画笔工具"},
    "F1": {"en": "Help", "zh": "帮助"}
  }
}
```
These shortcuts will be displayed when no other relevant modifier keys are active.

### Key Naming Conventions

The keys within a modifier block (e.g., `"S"`, `"F1"`, `"SPACE"`) should match the **normalized key names** that the application's `KeyboardHandler` produces. Generally:
*   Letters: Uppercase (e.g., `"A"`, `"S"`)
*   Numbers: `"0"`-`"9"`
*   Function Keys: `"F1"` - `"F12"` (or up to `"F24"`)
*   Special Keys: Use consistent uppercase names like `"ESC"`, `"ENTER"`, `"SPACE"`, `"TAB"`, `"DELETE"`, `"HOME"`, `"END"`, `"PAGEUP"`, `"PAGEDOWN"`, `"LEFT"`, `"RIGHT"`, `"UP"`, `"DOWN"`, `"PRTSC"` (for PrintScreen), `"PAUSE"`.
*   Symbols: Use the symbol itself if it's a standard character (e.g., `"-"`, `"="`, `"["`, `"]"`, `";"`).

If unsure, you can temporarily add `print(f"Normalized key: {normalized_key}")` in `KeyboardHandler._key_event_callback` to see what name is generated for a specific key press.

### Localized Descriptions

Shortcut descriptions can be simple strings (if you only use one language) or objects for localization:
*   Simple string: `"S": "Save"`
*   Localized object: `"S": {"en": "Save File", "zh": "保存文件"}`

The application will try to display the description for the currently selected UI language. If not found, it will try the fallback language (English if current is Chinese, Chinese if current is English), then the first available description.

### Adding New Applications

1.  Find the executable name (e.g., `MYCOOLAPP.EXE`).
2.  Add a new top-level entry in `shortcuts.json`:
    ```json
    "MYCOOLAPP.EXE": {
      "Ctrl": {
        "Q": {"en": "Quick Action", "zh": "快捷动作"}
      },
      "NoModifier": {
        "H": {"en": "Show Help Panel", "zh": "显示帮助面板"}
      }
    }
    ```
3.  Save `shortcuts.json`. The overlay should automatically pick up the changes for `MYCOOLAPP.EXE` when it becomes the foreground application. (Restarting the overlay might be necessary if it doesn't pick up changes to the file immediately, or if `ConfigManager` doesn't have live reloading).

### Example: Adding a Word Shortcut

Assuming `WINWORD.EXE` is already an entry:

```json
"WINWORD.EXE": {
    "Ctrl": {
      "S": { "en": "Save", "zh": "保存" },
  }
}
```

## 6. Troubleshooting

*   **Shortcuts not appearing for an app**:
    *   Verify the executable name in `shortcuts.json` (UPPERCASE, including `.EXE`) exactly matches what the Foreground Monitor detects.
    *   Ensure the `shortcuts.json` file is valid JSON. You can use an online JSON validator.
    *   Check if the correct modifier combination is defined.
*   **Overlay not visible**:
    *   Right-click the tray icon and select "Show/Hide Overlay".
    *   Check the opacity setting; it might be too low.
*   **Application crashes or errors**:
    *   Check the console output for error messages.
    *   Ensure all prerequisites are installed correctly in your Python environment.