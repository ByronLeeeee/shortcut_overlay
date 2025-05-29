# shortcut_overlay/keyboard_handler.py
"""
Handles global keyboard event listening and processing.

This module uses the 'keyboard' library to capture system-wide key presses
and releases. It normalizes key names, tracks modifier states (Ctrl, Shift, Alt, Win),
and emits signals for key events and modifier changes. It also includes a
mechanism to detect "stuck" keys if the 'keyboard' library misses an 'up' event.
"""
import keyboard  # type: ignore # 'keyboard' library might not have type stubs.
from PySide6.QtCore import QObject, Signal, QTimer
import time
from typing import Set, Dict, Optional, Any

# Type alias for the event object from the 'keyboard' library.
# Using 'Any' as the 'keyboard' library lacks official type stubs.
KeyboardEvent = Any


class KeyboardHandler(QObject):
    """
    Listens for global keyboard events, normalizes them, and signals them
    to other application components for UI updates or other actions.
    Tracks active modifiers and handles potentially "stuck" keys.
    """

    # Signal emitted on any key press or release.
    # Args: (normalized_key_name: str, event_type: str ("up" or "down")).
    key_event_signal = Signal(str, str)

    # Signal emitted when the set of active logical modifiers (Ctrl, Shift, Alt, Win) changes.
    # Args: (active_modifiers_set: set of lowercase modifier names, e.g., {"ctrl", "shift"}).
    modifiers_changed = Signal(set)

    # Signal for exiting the application (currently not used as exit is via tray menu).
    # exit_signal = Signal() # Kept if future use is intended, otherwise can be removed.

    # Timeout in milliseconds to consider a key "stuck" if no 'up' event is received.
    DEFAULT_KEY_TIMEOUT_MS: int = 250
    # Interval in milliseconds for the timer that checks for stuck key states.
    STATE_CHECK_INTERVAL_MS: int = 50

    def __init__(self, parent: Optional[QObject] = None):
        """
        Initializes the KeyboardHandler.

        Sets up internal state for tracking pressed keys, active modifiers,
        and a timer for checking stuck keys.

        Args:
            parent: The parent QObject, if any.
        """
        super().__init__(parent)
        # Stores lowercase base names of active modifiers: "ctrl", "shift", "alt", "win".
        self._active_modifiers: Set[str] = set()
        self._hooked: bool = (
            False  # Flag indicating if the global keyboard hook is active.
        )
        # Stores normalized key names and their press timestamps (milliseconds since epoch).
        self._pressed_keys: Dict[str, float] = {}
        self._key_timeout_ms: int = self.DEFAULT_KEY_TIMEOUT_MS

        # Timer to periodically check for keys that might have missed their 'up' event.
        self._state_check_timer: QTimer = QTimer(self)
        self._state_check_timer.timeout.connect(self._check_key_states)
        self._state_check_timer.setInterval(self.STATE_CHECK_INTERVAL_MS)

    def _normalize_key_name(self, name_from_lib: Optional[str]) -> Optional[str]:
        """
        Normalizes key names received from the 'keyboard' library into a
        standardized format used throughout the application.
        For example, "left ctrl" becomes "Ctrl", "a" becomes "A", "esc" becomes "Esc".

        Args:
            name_from_lib: The raw key name string from the 'keyboard' library.

        Returns:
            The normalized key name string, or None if the input is invalid or cannot be normalized.
        """
        if not name_from_lib:
            return None
        name_lower = (
            name_from_lib.lower()
        )  # Normalize to lowercase for easier matching.

        # Check for modifier keys first, as they can have side variations (e.g., "left shift").
        if "ctrl" in name_lower:
            return "Ctrl"
        if "shift" in name_lower:
            return "Shift"
        if "alt" in name_lower:
            return "Alt"  # Catches "alt" and "alt gr".
        if "win" in name_lower or "cmd" in name_lower or name_lower == "meta":
            return "Win"  # Windows/Command/Meta key.

        # Normalize function keys (F1-F24).
        if (
            name_lower.startswith("f")
            and len(name_lower) > 1
            and name_lower[1:].isdigit()
        ):
            num = int(name_lower[1:])
            if 1 <= num <= 24:
                return f"F{num}"

        # Map common special key names to their normalized forms.
        special_keys_map: Dict[str, str] = {
            "escape": "Esc",
            "esc": "Esc",
            "space": "Space",
            "space bar": "Space",
            "enter": "Enter",
            "return": "Enter",
            "backspace": "Backspace",
            "caps lock": "Caps Lock",
            "capslock": "Caps Lock",
            "tab": "Tab",
            "delete": "Del",
            "del": "Del",
            "home": "Home",
            "end": "End",
            "page up": "PgUp",
            "pgup": "PgUp",
            "page down": "PgDn",
            "pgdn": "PgDn",
            "insert": "Ins",
            "ins": "Ins",
            "print screen": "PrtSc",
            "printscr": "PrtSc",
            "scroll lock": "ScrLk",
            "scrolllock": "ScrLk",
            "pause": "Pause",
            "pause break": "Pause",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",  # Arrow keys.
            "menu": "Menu",
            "apps": "Menu",
            "application": "Menu",  # Context menu key.
            "decimal": ".",
            "numpad decimal": ".",
            "separator": ",",
        }
        if name_lower in special_keys_map:
            return special_keys_map[name_lower]

        # Map common symbol names and their character representations.
        symbol_map: Dict[str, str] = {
            ";": ";",
            ":": ":",
            "semicolon": ";",
            "=": "=",
            "equals": "=",
            ",": ",",
            "comma": ",",
            "-": "-",
            "minus": "-",
            "subtract": "-",
            "hyphen": "-",
            ".": ".",
            "period": ".",
            "dot": ".",
            "/": "/",
            "slash": "/",
            "forward slash": "/",
            "divide": "/",
            "`": "`",
            "backtick": "`",
            "grave accent": "`",
            "[": "[",
            "open bracket": "[",
            "left bracket": "[",
            "]": "]",
            "close bracket": "]",
            "right bracket": "]",
            "\\": "\\",
            "backslash": "\\",
            "back slash": "\\",
            "'": "'",
            "apostrophe": "'",
            "single quote": "'",
            "*": "*",
            "multiply": "*",
            "asterisk": "*",
            "numpad multiply": "*",
            "+": "+",
            "add": "+",
            "plus": "+",
            "numpad plus": "+",
        }
        if name_lower in symbol_map:
            return symbol_map[name_lower]

        # Handle single character keys (letters are uppercased, digits/symbols as is).
        if len(name_lower) == 1:
            if name_lower.isalpha():
                return name_lower.upper()
            return name_lower  # For digits and symbols not caught by symbol_map.

        # Fallback: Uppercase the original name if no specific rule matched.
        # This might lead to inconsistent names for unmapped special keys.
        return name_from_lib.upper()

    def _get_modifier_base_name(self, normalized_key: str) -> Optional[str]:
        """
        Converts a normalized modifier key name (e.g., "Ctrl") to its lowercase base
        name (e.g., "ctrl") for internal state tracking.

        Args:
            normalized_key: The normalized key name.

        Returns:
            The lowercase base modifier name ("ctrl", "shift", "alt", "win"),
            or None if the key is not a recognized modifier.
        """
        if normalized_key == "Ctrl":
            return "ctrl"
        if normalized_key == "Shift":
            return "shift"
        if normalized_key == "Alt":
            return "alt"
        if normalized_key == "Win":
            return "win"
        return None

    def _map_normalized_to_keyboard_lib_name(self, normalized_key_name: str) -> str:
        """
        Maps an application-normalized key name back to a name format that the
        'keyboard' library's `is_pressed()` function is likely to recognize.
        This is primarily for checking key states with `keyboard.is_pressed()`.

        Args:
            normalized_key_name: The application's internal normalized key name.

        Returns:
            A key name string suitable for `keyboard.is_pressed()`.
        """
        # Map specific normalized names back to common library names.
        if normalized_key_name == "Ctrl":
            return "ctrl"
        if normalized_key_name == "Shift":
            return "shift"
        if normalized_key_name == "Alt":
            return "alt"
        if normalized_key_name == "Win":
            return "windows"  # 'keyboard' often uses "windows".
        if normalized_key_name == "Caps Lock":
            return "caps lock"
        if normalized_key_name == "PrtSc":
            return "print screen"
        if normalized_key_name == "ScrLk":
            return "scroll lock"
        if normalized_key_name == "PgUp":
            return "page up"
        if normalized_key_name == "PgDn":
            return "page down"
        # For most other keys, their lowercase version is usually sufficient for the library.
        return normalized_key_name.lower()

    def _check_key_states(self) -> None:
        """
        Periodically called by `_state_check_timer`.
        Checks if keys recorded as pressed are still physically pressed according
        to the 'keyboard' library. If a key is no longer pressed but its 'up'
        event was missed, this method simulates a release event.
        """
        current_time_ms = time.time() * 1000
        keys_to_release_simulated: Set[str] = set()

        # Iterate over a copy of _pressed_keys items as the dictionary might be modified.
        for key_name, press_time_ms in list(self._pressed_keys.items()):
            try:
                lib_key_name = self._map_normalized_to_keyboard_lib_name(key_name)
                if not keyboard.is_pressed(lib_key_name):
                    # Key is no longer pressed according to the library.
                    keys_to_release_simulated.add(key_name)
            except Exception:  # Catch errors from keyboard.is_pressed()
                # If checking state fails, fall back to timeout logic for this key.
                if current_time_ms - press_time_ms > self._key_timeout_ms:
                    keys_to_release_simulated.add(key_name)

        for key_name_to_release in keys_to_release_simulated:
            self._simulate_key_release(key_name_to_release)

    def _simulate_key_release(self, key_name: str) -> None:
        """
        Simulates a key release event for a key presumed to be "stuck".
        Updates internal state and emits `key_event_signal` and potentially
        `modifiers_changed` if it was a modifier.

        Args:
            key_name: The normalized name of the key to simulate a release for.
        """
        if key_name in self._pressed_keys:
            del self._pressed_keys[key_name]  # Remove from tracked pressed keys.
            self.key_event_signal.emit(key_name, "up")  # Emit the 'up' event.

            modifier_base = self._get_modifier_base_name(key_name)
            if modifier_base and modifier_base in self._active_modifiers:
                # If it was an active modifier, re-check if any other physical key for it is pressed.
                # This simplified version just removes it; a more robust check would query keyboard.is_pressed().
                self._active_modifiers.discard(modifier_base)
                self.modifiers_changed.emit(self._active_modifiers.copy())

    def _key_event_callback(self, event: KeyboardEvent) -> None:
        """
        Callback function invoked by the 'keyboard' library for each key event.
        It normalizes the key name, updates internal state tracking pressed keys
        and active modifiers, and emits signals.

        Args:
            event: The event object from the 'keyboard' library, containing
                   attributes like 'name' and 'event_type'.
        """
        if not hasattr(event, "name") or event.name is None:
            return  # Ignore malformed events.

        normalized_key = self._normalize_key_name(event.name)
        if not normalized_key:
            return  # Ignore keys that could not be normalized.

        event_type_str = "down" if event.event_type == keyboard.KEY_DOWN else "up"

        # Update tracking of physically pressed keys.
        if event_type_str == "down":
            if normalized_key not in self._pressed_keys:
                self._pressed_keys[normalized_key] = time.time() * 1000
        elif event_type_str == "up":
            if normalized_key in self._pressed_keys:  # Remove on 'up' event.
                del self._pressed_keys[normalized_key]

        # Emit the processed key event.
        self.key_event_signal.emit(normalized_key, event_type_str)

        # Update the set of active logical modifiers.
        modifier_base = self._get_modifier_base_name(normalized_key)
        if modifier_base:  # If the event key is a modifier.
            modifiers_changed_flag = False
            if event_type_str == "down":
                if modifier_base not in self._active_modifiers:
                    self._active_modifiers.add(modifier_base)
                    modifiers_changed_flag = True
            elif event_type_str == "up":
                if modifier_base in self._active_modifiers:
                    # Check if any physical key for this modifier is still pressed.
                    # e.g., left shift up, but right shift still down.
                    is_still_pressed = False
                    if modifier_base == "ctrl" and (
                        keyboard.is_pressed("left ctrl")
                        or keyboard.is_pressed("right ctrl")
                    ):
                        is_still_pressed = True
                    elif modifier_base == "shift" and (
                        keyboard.is_pressed("left shift")
                        or keyboard.is_pressed("right shift")
                    ):
                        is_still_pressed = True
                    elif modifier_base == "alt" and (
                        keyboard.is_pressed("left alt")
                        or keyboard.is_pressed("alt gr")
                        or keyboard.is_pressed("right alt")
                    ):
                        is_still_pressed = True
                    elif modifier_base == "win" and (
                        keyboard.is_pressed("left windows")
                        or keyboard.is_pressed("right windows")
                    ):
                        is_still_pressed = True

                    if (
                        not is_still_pressed
                    ):  # Only remove if no other physical key for this modifier is held.
                        self._active_modifiers.discard(modifier_base)
                        modifiers_changed_flag = True

            if modifiers_changed_flag:
                self.modifiers_changed.emit(self._active_modifiers.copy())

    def start_listening(self) -> None:
        """
        Starts the global keyboard listener by hooking into system keyboard events
        using the 'keyboard' library. Also starts the timer for checking stuck key states.
        Requires appropriate permissions (e.g., administrator rights on some systems).
        """
        if not self._hooked:
            try:
                # `suppress=False` ensures events are passed to other applications as well.
                keyboard.hook(self._key_event_callback, suppress=False)
                self._hooked = True
                self._state_check_timer.start()  # Start timer for stuck key detection.
                print("Keyboard listener started.")  # Console message for status.
            except Exception as e:
                # Catch common errors like permission issues.
                print(f"Error starting keyboard listener: {e}")
                print(
                    "This may be due to insufficient permissions (e.g., run as administrator) "
                    "or conflicts with other global keyboard hooks."
                )

    def stop_listening(self) -> None:
        """
        Stops the global keyboard listener, unhooks from system events,
        stops the state-checking timer, and clears internal state.
        """
        if self._hooked:
            try:
                keyboard.unhook_all()  # Remove all keyboard hooks set by this instance.
            except Exception as e:
                print(f"Error during keyboard.unhook_all(): {e}")
            self._hooked = False

        if self._state_check_timer.isActive():
            self._state_check_timer.stop()

        # Clear tracked keys and modifiers.
        self._pressed_keys.clear()
        self._active_modifiers.clear()
        # Emit a final modifiers_changed to reset any UI elements.
        self.modifiers_changed.emit(self._active_modifiers.copy())
        print("Keyboard listener stopped.")  # Console message for status.
