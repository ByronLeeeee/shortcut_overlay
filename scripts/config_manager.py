# scripts/config_manager.py
"""
Manages application configuration, including shortcut definitions and user settings.

This module is responsible for loading configurations from JSON files and saving
them back. It handles cases where configuration files might be missing or
corrupted by providing default configurations. It expects absolute paths to
the shortcuts and settings JSON files during instantiation.
"""
import json
import os
from typing import Dict, Any, Optional

# Type aliases for better readability and type hinting, representing
# the expected structure of the JSON configuration data.
# Example: {"NOTEPAD.EXE": {"Ctrl": {"S": {"en": "Save", "zh": "保存"}}}}
ShortcutData = Dict[str, Any]
# Example: {"theme_name": "Default Dark", "opacity": 85, "language": "en_US"}
AppSettingsData = Dict[str, Any]


class ConfigManager:
    """
    Handles the loading, saving, and accessing of application configurations.
    It manages two primary pieces of configuration:
    1. Shortcut definitions for various applications.
    2. User preferences for application behavior and UI (e.g., theme, opacity).
    Configurations are stored in and retrieved from JSON files.
    """

    def __init__(self, shortcuts_file_path: str, settings_file_path: str) -> None:
        """
        Initializes the ConfigManager with paths to the configuration files.

        The actual loading or creation of these configuration files is deferred
        to the `initialize_configs()` method, which should be called explicitly
        after the ConfigManager object has been created.

        Args:
            shortcuts_file_path: The absolute path to the JSON file storing shortcut definitions.
            settings_file_path: The absolute path to the JSON file storing user application settings.
        """
        self.shortcuts_data: ShortcutData = {}  # Holds loaded shortcut definitions.
        self.app_settings: AppSettingsData = {}  # Holds loaded application settings.

        self._shortcuts_file_path: str = shortcuts_file_path
        self._settings_file_path: str = settings_file_path

    def initialize_configs(self) -> None:
        """
        Loads configurations from their respective files. If a file does not exist
        or is invalid, default configurations are generated and used (and saved if new).
        This method should be called once after ConfigManager instantiation to populate
        `shortcuts_data` and `app_settings`.
        """
        self._load_or_create_shortcuts()
        self._load_or_create_settings()

    def _get_default_shortcuts_config(self) -> ShortcutData:
        """
        Provides the default structure and content for the shortcuts configuration.
        This configuration is used if the shortcuts file is missing or unreadable.
        Shortcut descriptions include basic English ('en') and Chinese ('zh') localizations.

        Returns:
            A dictionary representing the default shortcut configuration.
        """
        return {
            "NOTEPAD.EXE": {  # Example application-specific shortcuts
                "Ctrl": {
                    "S": {"en": "Save File", "zh": "保存文件"},
                    "O": {"en": "Open File", "zh": "打开文件"},
                    "N": {"en": "New File", "zh": "新建文件"},
                }
            },
            "DEFAULT": {  # Fallback shortcuts for applications not explicitly defined
                "Ctrl": {
                    "C": {"en": "Copy (Global)", "zh": "复制 (全局)"},
                    "V": {"en": "Paste (Global)", "zh": "粘贴 (全局)"},
                    "X": {"en": "Cut (Global)", "zh": "剪切 (全局)"},
                },
                "Alt": {"F4": {"en": "Close Window", "zh": "关闭窗口"}},
                # Additional global default shortcuts can be added here.
            },
        }

    def _load_or_create_shortcuts(self) -> None:
        """
        Loads shortcut definitions from the file specified by `_shortcuts_file_path`.
        If the file does not exist or contains invalid JSON, a default shortcuts
        configuration (from `_get_default_shortcuts_config`) is created in memory
        and an attempt is made to save it to the file path.
        """
        if not os.path.exists(self._shortcuts_file_path):
            # File not found, create and use default configuration.
            self._create_default_shortcuts_config()
            return

        try:
            # Attempt to open and parse the existing shortcuts file.
            with open(self._shortcuts_file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                if not isinstance(
                    loaded_data, dict
                ):  # Basic validation of JSON structure.
                    raise json.JSONDecodeError(
                        "Shortcuts file content is not a valid JSON object.", "", 0
                    )
                self.shortcuts_data = loaded_data
        except (json.JSONDecodeError, IOError, Exception) as e:
            # Handle JSON parsing errors, I/O errors, or other unexpected issues.
            print(
                f"Warning: Error loading shortcuts from '{self._shortcuts_file_path}': {e}. Using default shortcuts."
            )
            self.shortcuts_data = self._get_default_shortcuts_config()
            # Optionally, backup the corrupted file before overwriting or just use defaults in memory.

    def _create_default_shortcuts_config(self) -> None:
        """
        Creates a default shortcuts configuration file at `_shortcuts_file_path`
        and sets `self.shortcuts_data` to this default configuration.
        This is called if the shortcuts file is missing.
        """
        default_config = self._get_default_shortcuts_config()
        try:
            # Ensure the target directory exists before writing.
            os.makedirs(os.path.dirname(self._shortcuts_file_path), exist_ok=True)
            with open(self._shortcuts_file_path, "w", encoding="utf-8") as f:
                json.dump(
                    default_config, f, indent=2, ensure_ascii=False
                )  # Save with pretty print.
            self.shortcuts_data = default_config
        except (IOError, Exception) as e:
            # If saving the default config fails, still use it in memory.
            print(
                f"Error: Could not create default shortcuts config at '{self._shortcuts_file_path}': {e}."
            )
            self.shortcuts_data = default_config  # Ensure app can run with defaults.
    
    def save_shortcuts(self) -> None:
        """
        Saves the current `self.shortcuts_data` to the `_shortcuts_file_path`.
        This method should be called after modifications to `self.shortcuts_data`
        that need to be persisted.
        """
        try:
            os.makedirs(os.path.dirname(self._shortcuts_file_path), exist_ok=True)
            with open(self._shortcuts_file_path, "w", encoding="utf-8") as f:
                json.dump(self.shortcuts_data, f, indent=2, ensure_ascii=False)
            # print(f"Info: Shortcuts explicitly saved to '{self._shortcuts_file_path}'.")
        except Exception as e:
            print(f"Error: Could not save shortcuts to '{self._shortcuts_file_path}': {e}")
            raise  # Re-raise the exception to be caught by the caller (e.g., ShortcutManagerDialog)

    def get_shortcuts_for_app(self, app_name: Optional[str]) -> ShortcutData:
        """
        Retrieves shortcut definitions for a specified application name.
        If application-specific shortcuts are not found, it returns the "DEFAULT"
        set of shortcuts. If `app_name` is None or empty, it directly considers
        "DEFAULT" shortcuts.

        Args:
            app_name: The executable name of the application (e.g., "NOTEPAD.EXE"),
                      case-insensitive.

        Returns:
            A dictionary of shortcuts for the given application. Returns an empty
            dictionary if no "DEFAULT" shortcuts are defined and no app-specific
            shortcuts are found.
        """
        # Normalize app_name to uppercase for case-insensitive matching.
        app_key = app_name.upper() if app_name else "DEFAULT"

        app_specific_shortcuts = self.shortcuts_data.get(app_key)
        if app_specific_shortcuts is not None:  # Found app-specific or "DEFAULT" entry.
            return app_specific_shortcuts
        elif (
            app_key != "DEFAULT"
        ):  # App-specific not found, try "DEFAULT" explicitly if not already tried.
            return self.shortcuts_data.get("DEFAULT", {})
        return {}  # No specific or "DEFAULT" shortcuts found.

    def _get_default_settings(self) -> AppSettingsData:
        """
        Provides the default structure and content for user application settings.
        This configuration is used if the settings file is missing, unreadable,
        or if certain keys are missing from an existing file.

        Returns:
            A dictionary representing the default application settings.
        """
        return {
            "theme_name": "Default Dark",  # Internal ID for theme selection (non-translated).
            "opacity": 85,  # Overlay window opacity (percentage, e.g., 20-100).
            "custom_bg_color": "#AA14141E",  # Default custom background color (Hex ARGB).
            "custom_key_color": "#CC32323C",  # Default custom key color (Hex ARGB).
            "custom_text_color": "#FFFFFFFF",  # Default custom key text color (Hex ARGB).
            "language": "en_US",  # Default UI language (locale string, e.g., "en_US", "zh_CN").
            "window_x": None,  # No specific default position, let OS decide initially
            "window_y": None,
            "window_width": 850, # Default width
            "window_height": 280 # Default height
            # Other settings like window position/size can be added here.
        }

    def _load_or_create_settings(self) -> None:
        """
        Loads user application settings from the file specified by `_settings_file_path`.
        If the file does not exist, is invalid, or is missing expected keys,
        default settings are used and merged. The resulting configuration is
        saved back to the file if the original was missing, invalid, or updated
        with new default keys.
        """
        default_settings = self._get_default_settings()
        loaded_settings: AppSettingsData = {}  # To store settings read from file.
        file_existed_and_was_valid = False

        if os.path.exists(self._settings_file_path):
            try:
                with open(self._settings_file_path, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    if not isinstance(loaded_settings, dict):  # Basic validation.
                        loaded_settings = {}  # Invalidate to use defaults.
                    else:
                        file_existed_and_was_valid = True
            except (json.JSONDecodeError, IOError, Exception) as e:
                print(
                    f"Warning: Error loading settings from '{self._settings_file_path}': {e}. Using default settings."
                )
                # loaded_settings remains {}
        # else: (File not found, handled by merging with defaults later)

        # Merge loaded settings with defaults: defaults provide missing keys.
        # Start with a copy of default_settings, then update with loaded_settings.
        self.app_settings = default_settings.copy()
        self.app_settings.update(
            loaded_settings
        )  # Overwrites defaults with loaded values if keys match.

        # Ensure all keys from default_settings are present in self.app_settings.
        # This handles cases where new default settings are added to the application
        # but are missing from an existing user's settings file.
        made_changes_due_to_missing_keys = False
        for key, default_value in default_settings.items():
            if key not in self.app_settings:
                self.app_settings[key] = default_value
                made_changes_due_to_missing_keys = True

        # Save settings if:
        # 1. The file didn't exist.
        # 2. The file existed but was invalid (so defaults were heavily used).
        # 3. The file was valid, but new default keys were added.
        if not file_existed_and_was_valid or made_changes_due_to_missing_keys:
            self.save_settings()

    def save_settings(self) -> None:
        """Saves the current application settings (`self.app_settings`)
        to the file specified by `_settings_file_path` in JSON format.
        """
        try:
            os.makedirs(os.path.dirname(self._settings_file_path), exist_ok=True)
            with open(self._settings_file_path, "w", encoding="utf-8") as f:
                json.dump(self.app_settings, f, indent=2, ensure_ascii=False)
        except (IOError, Exception) as e:
            print(
                f"Error: Could not save app settings to '{self._settings_file_path}': {e}."
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a specific setting value by its key from `app_settings`.

        Args:
            key: The key of the setting to retrieve.
            default: The value to return if the key is not found.

        Returns:
            The value of the setting, or the `default` value if the key is not present.
        """
        return self.app_settings.get(key, default)

    def update_settings(self, new_settings_dict: AppSettingsData) -> None:
        """
        Updates multiple application settings from a given dictionary and
        persists the changes by calling `save_settings()`.

        Args:
            new_settings_dict: A dictionary containing settings to update.
                               Existing settings with the same keys will be overwritten.
                               New key-value pairs will be added.
        """
        self.app_settings.update(new_settings_dict)
        self.save_settings()

    def get_all_settings(self) -> AppSettingsData:
        """
        Returns a copy of all current application settings.
        Modifying the returned dictionary will not affect the ConfigManager's
        internal settings state unless explicitly saved back using `update_settings`.

        Returns:
            A copy of the `app_settings` dictionary.
        """
        return self.app_settings.copy()

    def get_all_shortcuts(self) -> ShortcutData:
        """
        Returns a copy of all loaded shortcut data.
        Modifying the returned dictionary will not affect the ConfigManager's
        internal shortcuts state.

        Returns:
            A copy of the `shortcuts_data` dictionary.
        """
        return self.shortcuts_data.copy()
