# shortcut_overlay/overlay_keyboard.py
"""
Defines the on-screen keyboard overlay window and individual key widgets.

This module is responsible for rendering the visual keyboard, displaying
shortcut information on keys, handling user interactions like dragging and resizing,
and updating its appearance based on active application, pressed keys,
and theme settings from the configuration.
"""
from typing import List, Tuple, Union, Dict, Set, Optional, Any

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QSizeGrip,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Slot, QPoint, QEvent
from PySide6.QtGui import QColor, QPalette, QMouseEvent, QResizeEvent, QShowEvent

import win32gui
import win32con

from .config_manager import ConfigManager

# Defines the visual layout of the on-screen keyboard.
KEY_LAYOUT: List[List[Union[str, Tuple[str, float]]]] = [
    ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
    ["`","1","2","3","4","5","6","7","8","9","0","-","=",("Backspace", 2.0)],
    [("Tab", 1.5),"Q","W","E","R","T","Y","U","I","O","P","[","]",("\\", 1.5)],
    [("Caps Lock", 1.8),"A","S","D","F","G","H","J","K","L",";","'",("Enter", 2.2)],
    [("Shift", 2.5),"Z","X","C","V","B","N","M",",",".","/",("Shift", 2.5)],
    [("Ctrl", 1.5),("Win", 1.2),("Alt", 1.2),("Space", 6.0),("Alt", 1.2),("Win", 1.2),("Menu", 1.2),("Ctrl", 1.5)]
]

# Default font size for shortcut descriptions displayed on keys.
DEFAULT_ORIGINAL_SHORTCUT_FONT_SIZE: int = 7


class KeyWidget(QWidget):
    """
    Represents a single, individual key on the on-screen keyboard overlay.
    It displays the keycap text and any associated shortcut description,
    and its appearance changes based on press state or if it's an active modifier.
    """

    def __init__(self, key_text: str, parent: Optional[QWidget] = None):
        """
        Initializes a KeyWidget.

        Args:
            key_text: The text to display on the keycap (e.g., "Ctrl", "A").
            parent: The parent QWidget, if any.
        """
        super().__init__(parent)
        self.key_text_upper: str = key_text.upper()
        self.display_text: str = key_text

        self._layout: QVBoxLayout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(1)

        self.key_label: QLabel = QLabel(self.display_text)
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.shortcut_label: QLabel = QLabel("")
        self.shortcut_label.setAlignment(Qt.AlignCenter)
        self.shortcut_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.shortcut_label.setWordWrap(True)
        self.shortcut_label.setToolTip("")

        self._layout.addWidget(self.key_label, stretch=2)
        self._layout.addWidget(self.shortcut_label, stretch=1)

        # Stylesheet strings are populated by OverlayKeyboardWindow.apply_theme().
        self._default_key_label_stylesheet: str = ""
        self._pressed_key_label_stylesheet: str = ""
        self._modifier_active_key_label_stylesheet: str = ""
        
        # Palette for the KeyWidget container, configured by apply_theme().
        self._default_widget_palette: QPalette = QPalette()
        
        self.setAutoFillBackground(True) # Ensures QPalette background is drawn.
        # Initial style is effectively set after apply_theme is called from OverlayKeyboardWindow.

    def set_default_style(self) -> None:
        """Applies the default visual style to this key."""
        self.setStyleSheet("") # Clear any direct stylesheet on KeyWidget itself.
        self.setPalette(self._default_widget_palette) # Apply the base palette.
        self.key_label.setStyleSheet(self._default_key_label_stylesheet) # Style the keycap label.

    def set_pressed_style(self) -> None:
        """Applies the visual style for a physically pressed key."""
        self.setStyleSheet("")
        self.key_label.setStyleSheet(self._pressed_key_label_stylesheet)

    def set_modifier_active_style(self) -> None:
        """Applies the visual style for an active (logical) modifier key."""
        self.setStyleSheet("")
        self.key_label.setStyleSheet(self._modifier_active_key_label_stylesheet)

    def update_shortcut_display(self, text: str) -> None:
        """
        Updates the shortcut description text displayed on this key.

        Args:
            text: The shortcut description to display. Clears if empty.
        """
        if not text:
            self.shortcut_label.setText("")
            self.shortcut_label.setToolTip("")
            return
        self.shortcut_label.setText(text)
        self.shortcut_label.setToolTip(text)

    def clear_shortcut_text(self) -> None:
        """Clears the shortcut description text from this key."""
        self.update_shortcut_display("")


class OverlayKeyboardWindow(QWidget):
    """
    The main window for the on-screen keyboard overlay.
    Manages KeyWidgets, theming, opacity, interaction, and state updates.
    """
    DEFAULT_THEME_ID: str = "Default Dark"
    THEMES_DEFINITION: Dict[str, Tuple[str, QColor, str, str, str, str, str]] = {
        "Default Dark": ("rgb(20,20,30)", QColor(50,50,60,180), "white", "#444444", "#DDDD00", "#5A98D1", "#4682B4"),
        "Light Steel": ("rgb(200,205,210)", QColor(230,235,240,220), "black", "#B0B0B0", "#0055A4", "#A0D8F0", "#7CB9E8"),
        "Midnight Blue": ("rgb(25,25,112)", QColor(40,40,130,200), "white", "#6060C0", "#FFFF00", "#3A78B1", "#2C5F8F"),
        "Nord Dark": ("rgb(46,52,64)", QColor(67,76,94,200), "#D8DEE9", "#4C566A", "#88C0D0", "#5E81AC", "#81A1C1"),
        "Tokyo Night": ("rgb(26,27,38)", QColor(41,42,58,195), "#C0CAF5", "#565F89", "#7AA2F7", "#BB9AF7", "#F7768E"),
        "Dracula": ("rgb(40,42,54)", QColor(68,71,90,190), "#F8F8F2", "#6272A4", "#50FA7B", "#BD93F9", "#FF79C6"),
        "Forest Green": ("rgb(34,53,44)", QColor(52,73,62,185), "#E8F5E8", "#2D5A3D", "#7ED321", "#4CAF50", "#66BB6A"),
        "Warm Sepia": ("rgb(73,63,50)", QColor(95,83,68,180), "#F5E6D3", "#8B7355", "#D4AF37", "#CD853F", "#DEB887"),
        "Soft Purple": ("rgb(56,47,66)", QColor(78,67,88,187), "#E6E1F0", "#6B5B7B", "#9C88FF", "#8A7CA8", "#B39DDB"),
        "High Contrast Dark": ("rgb(0,0,0)", QColor(33,33,33,220), "#FFFFFF", "#666666", "#00FF00", "#0099FF", "#FF6600"),
        "High Contrast Light": ("rgb(255,255,255)", QColor(240,240,240,220), "#000000", "#CCCCCC", "#FF0066", "#0066FF", "#FF9900"),
        "Neon Cyber": ("rgb(0,5,15)", QColor(15,25,35,195), "#00FFFF", "#003366", "#FF00FF", "#00FF88", "#FF6600"),
        "RGB Gaming": ("rgb(18,18,18)", QColor(35,35,35,200), "#FFFFFF", "#555555", "#FF0080", "#8000FF", "#00FF80"),
        "Retro Synthwave": ("rgb(20,8,30)", QColor(40,20,50,190), "#FF00FF", "#4A0E4E", "#00FFFF", "#FF1493", "#FF4500"),
        "Corporate Blue": ("rgb(240,248,255)", QColor(230,240,250,210), "#1E3A8A", "#B0C4DE", "#2563EB", "#3B82F6", "#60A5FA"),
        "Elegant Gray": ("rgb(248,250,252)", QColor(241,245,249,205), "#374151", "#D1D5DB", "#6366F1", "#8B5CF6", "#A855F7"),
        "Professional Green": ("rgb(240,253,244)", QColor(220,252,231,208), "#064E3B", "#A7F3D0", "#059669", "#10B981", "#34D399"),
        "Sunset Orange": ("rgb(45,25,15)", QColor(70,45,30,185), "#FFF7ED", "#7C2D12", "#EA580C", "#F97316", "#FB923C"),
        "Cherry Blossom": ("rgb(60,40,50)", QColor(85,65,75,183), "#FDF2F8", "#881337", "#E11D48", "#F43F5E", "#FB7185"),
        "Golden Hour": ("rgb(55,45,25)", QColor(80,68,45,187), "#FFFBEB", "#92400E", "#D97706", "#F59E0B", "#FBBF24"),
        "Ocean Breeze": ("rgb(20,40,60)", QColor(40,65,85,190), "#F0F9FF", "#0C4A6E", "#0284C7", "#0EA5E9", "#38BDF8"),
        "Spring Mint": ("rgb(30,50,40)", QColor(50,75,65,185), "#F0FDF4", "#14532D", "#16A34A", "#22C55E", "#4ADE80"),
        "Lavender Dream": ("rgb(45,35,60)", QColor(70,60,85,188), "#FAF5FF", "#581C87", "#7C3AED", "#8B5CF6", "#A78BFA"),
        "Pure White": ("rgb(255,255,255)", QColor(248,250,252,220), "#111827", "#E5E7EB", "#3B82F6", "#6366F1", "#8B5CF6"),
        "Deep Black": ("rgb(0,0,0)", QColor(17,24,39,210), "#F9FAFB", "#374151", "#10B981", "#06B6D4", "#8B5CF6"),
        "Monochrome": ("rgb(128,128,128)", QColor(156,163,175,195), "#FFFFFF", "#6B7280", "#000000", "#374151", "#111827"),
        "Low Light": ("rgb(15,15,15)", QColor(30,30,30,200), "#DC2626", "#1F2937", "#EF4444", "#F87171", "#FCA5A5"),
        "Blue Light Filter": ("rgb(50,40,30)", QColor(70,60,50,190), "#FEF3C7", "#92400E", "#F59E0B", "#FBBF24", "#FCD34D"),
        "Accessibility": ("rgb(255,255,255)", QColor(150,150,150,220), "#000000", "#808080", "#0000FF", "#FF0000", "#008000"),
    }

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.active_app_name: str = "DEFAULT"
        self.current_logical_modifiers: Set[str] = set()
        self.key_widgets_map: Dict[str, List[KeyWidget]] = {}
        self._drag_pos: QPoint = QPoint()
        self._physically_pressed_key_names: Set[str] = set()

        self.main_opacity_effect: QGraphicsOpacityEffect = QGraphicsOpacityEffect(self)
        self.main_opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.main_opacity_effect)

        self.main_layout: Optional[QVBoxLayout] = None
        self.keyboard_layout_container: Optional[QWidget] = None
        self.size_grip: Optional[QSizeGrip] = None

        self.init_ui()
        self.set_window_properties()
        self.apply_current_settings()

    def init_ui(self) -> None:
        """Initializes the UI elements, creating the keyboard layout."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(1); self.main_layout.setContentsMargins(2,2,2,2)
        self.keyboard_layout_container = QWidget()
        keyboard_grid_layout = QVBoxLayout(self.keyboard_layout_container)
        keyboard_grid_layout.setSpacing(3); keyboard_grid_layout.setContentsMargins(5,5,5,5)

        for row_keys in KEY_LAYOUT:
            row_layout = QHBoxLayout(); row_layout.setSpacing(3)
            for key_spec in row_keys:
                stretch_factor: float = 1.0; key_text_from_layout: str
                if isinstance(key_spec, tuple): key_text_from_layout, stretch_factor = key_spec
                else: key_text_from_layout = key_spec
                key_widget = KeyWidget(key_text_from_layout)
                row_layout.addWidget(key_widget, stretch=int(stretch_factor * 10))
                self.key_widgets_map.setdefault(key_widget.key_text_upper, []).append(key_widget)
            keyboard_grid_layout.addLayout(row_layout)
        self.main_layout.addWidget(self.keyboard_layout_container)

        size_grip_layout = QHBoxLayout(); size_grip_layout.addStretch()
        self.size_grip = QSizeGrip(self); self.size_grip.setFixedSize(16, 16)
        self.size_grip.setStyleSheet("QSizeGrip {background-color:rgba(100,100,120,100); border:1px solid rgba(150,150,180,150);} QSizeGrip:hover {background-color:rgba(120,120,150,180);} QSizeGrip:pressed {background-color:rgba(80,80,100,220);}")
        size_grip_layout.addWidget(self.size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.main_layout.addLayout(size_grip_layout)
        self.setMinimumSize(600, 200); self.resize(850, 280)

    def set_window_properties(self) -> None:
        """Sets Qt window flags for overlay behavior (frameless, on-top, tool)."""
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def apply_current_settings(self) -> None:
        """Applies current theme and opacity settings from ConfigManager."""
        opacity_percent: int = self.config_manager.get_setting("opacity", 85)
        if self.main_opacity_effect:
            self.main_opacity_effect.setOpacity(opacity_percent / 100.0)
        
        self.apply_theme()
        self.update() # Schedule repaint.

    def apply_theme(self) -> None:
        """Applies the selected visual theme to the overlay window and all KeyWidgets."""
        theme_id: str = self.config_manager.get_setting("theme_name", self.DEFAULT_THEME_ID)
        themes = self.THEMES_DEFINITION
        
        custom_bg_color_str: str = self.config_manager.get_setting("custom_bg_color", "#FF14141E")
        custom_key_color_str: str = self.config_manager.get_setting("custom_key_color", "#FF32323C")
        custom_text_color_str: str = self.config_manager.get_setting("custom_text_color", "#FFFFFFFF")
        default_shortcut_color: str = "#DDDD00"

        main_bg_rgba_str: str; key_widget_container_bg_qcolor: QColor; key_label_fg_str: str
        key_label_border_str: str; shortcut_fg_str: str; pressed_label_bg_hex: str; modifier_label_bg_hex: str

        if theme_id == "Custom":
            main_bg_rgba_str = QColor(custom_bg_color_str).name(QColor.HexArgb)
            key_widget_container_bg_qcolor = QColor(custom_key_color_str)
            key_label_fg_str = QColor(custom_text_color_str).name(QColor.HexRgb)
            key_label_border_str = QColor(key_label_fg_str).darker(150).name()
            shortcut_fg_str = default_shortcut_color
            temp_opaque_key_color = QColor(custom_key_color_str); temp_opaque_key_color.setAlpha(255)
            pressed_label_bg_hex = temp_opaque_key_color.lighter(130).name(QColor.HexRgb)
            modifier_label_bg_hex = temp_opaque_key_color.lighter(115).name(QColor.HexRgb)
        elif theme_id in themes:
            (main_bg_rgba_str, key_widget_container_bg_qcolor, key_label_fg_str, key_label_border_str,
            shortcut_fg_str, pressed_label_bg_hex, modifier_label_bg_hex) = themes[theme_id]
        else:
            (main_bg_rgba_str, key_widget_container_bg_qcolor, key_label_fg_str, key_label_border_str,
            shortcut_fg_str, pressed_label_bg_hex, modifier_label_bg_hex) = themes[self.DEFAULT_THEME_ID]

        self.setStyleSheet(f"background-color: {main_bg_rgba_str};")

        for key_list in self.key_widgets_map.values():
            for kw in key_list:
                kw._default_widget_palette.setColor(QPalette.ColorRole.Window, key_widget_container_bg_qcolor)
                kw._default_key_label_stylesheet = (f"font-weight: bold; color: {key_label_fg_str}; border: 1px solid {key_label_border_str}; border-radius: 3px; padding: 1px; background-color: transparent;")
                kw._pressed_key_label_stylesheet = (f"font-weight: bold; color: {key_label_fg_str}; background-color: {pressed_label_bg_hex}; border: 1px solid {QColor(key_label_border_str).lighter(110).name()}; border-radius: 3px; padding: 1px;")
                kw._modifier_active_key_label_stylesheet = (f"font-weight: bold; color: {key_label_fg_str}; background-color: {modifier_label_bg_hex}; border: 1px solid {key_label_border_str}; border-radius: 3px; padding: 1px;")
                kw.shortcut_label.setStyleSheet(f"font-size: {DEFAULT_ORIGINAL_SHORTCUT_FONT_SIZE}pt; color: {shortcut_fg_str}; background-color: transparent; padding: 1px;")
                kw.set_default_style()
        
        self._update_all_key_visuals()
        self.update_shortcut_display()

    def _get_theme_shortcut_fg_color(self) -> str:
        """Helper to retrieve the shortcut foreground color for the current theme."""
        theme_id: str = self.config_manager.get_setting("theme_name", self.DEFAULT_THEME_ID)
        if theme_id == "Custom":
            return self.config_manager.get_setting("custom_text_color", "#DDDD00")
        elif theme_id in self.THEMES_DEFINITION:
            return self.THEMES_DEFINITION[theme_id][4] # Index 4 is shortcut_fg_str.
        return self.THEMES_DEFINITION[self.DEFAULT_THEME_ID][4]

    def _get_shortcut_highlight_bg_color(self) -> str:
        """Determines the background color for highlighting active shortcut labels,
           derived from the current theme for consistency.
        """
        theme_id: str = self.config_manager.get_setting("theme_name", self.DEFAULT_THEME_ID)
        base_highlight_qcolor: QColor
        if theme_id == "Custom":
            base_highlight_qcolor = QColor(self.config_manager.get_setting("custom_key_color", "#AA7700"))
        elif theme_id in self.THEMES_DEFINITION:
            base_highlight_qcolor = self.THEMES_DEFINITION[theme_id][1] # Use key_widget_container_bg_qcolor.
        else:
            base_highlight_qcolor = self.THEMES_DEFINITION[self.DEFAULT_THEME_ID][1]
        
        highlight_qcolor = base_highlight_qcolor.lighter(130)
        if highlight_qcolor.alpha() < 150: # Ensure decent visibility.
            highlight_qcolor.setAlpha(max(150, highlight_qcolor.alpha()))
        return highlight_qcolor.name(QColor.HexArgb)

    def update_shortcut_display(self) -> None:
        """
        Updates shortcut descriptions on keys. If a shortcut is active due to
        current modifiers, its `shortcut_label` background is highlighted.
        """
        shortcut_fg_color = self._get_theme_shortcut_fg_color()
        highlight_bg_color = self._get_shortcut_highlight_bg_color()
        
        base_shortcut_label_style = (f"font-size: {DEFAULT_ORIGINAL_SHORTCUT_FONT_SIZE}pt; color: {shortcut_fg_color}; background-color: transparent; padding: 1px;")
        highlight_shortcut_label_style = (f"font-size: {DEFAULT_ORIGINAL_SHORTCUT_FONT_SIZE}pt; color: {shortcut_fg_color}; background-color: {highlight_bg_color}; border-radius: 2px; padding: 1px;")

        # Reset all shortcut labels to their default (non-highlighted) style first.
        for key_list in self.key_widgets_map.values():
            for widget in key_list:
                widget.clear_shortcut_text()
                widget.shortcut_label.setStyleSheet(base_shortcut_label_style)

        app_shortcuts: Dict[str, Any] = self.config_manager.get_shortcuts_for_app(self.active_app_name)
        mod_combo_str: Optional[str] = self._get_current_modifier_string_for_config()
        current_lang_code: str = self.config_manager.get_setting("language", "en_US").split('_')[0]
        fallback_lang_code: str = "en" if current_lang_code != "en" else "zh"

        # Helper to get the string description from a potentially localized object.
        def get_final_string_description(description_object: Any) -> str:
            if isinstance(description_object, str): return description_object
            if isinstance(description_object, dict):
                text = description_object.get(current_lang_code)
                if isinstance(text, str): return text
                text = description_object.get(fallback_lang_code)
                if isinstance(text, str): return text
                try: # Fallback to the first value in the dict if it's a string
                    first_value = next(iter(description_object.values()))
                    if isinstance(first_value, str): return first_value
                except StopIteration: pass # Empty dictionary
            return "N/A" # Default if no suitable string found

        # Process and highlight shortcuts active with current modifiers.
        if mod_combo_str and mod_combo_str in app_shortcuts:
            shortcuts_for_combo: Dict[str, Union[str, Dict[str, str]]] = app_shortcuts[mod_combo_str]
            if shortcuts_for_combo: # Check if there are any shortcuts for this combo
                for key_char_upper, desc_obj in shortcuts_for_combo.items():
                    display_text = get_final_string_description(desc_obj)
                    if key_char_upper in self.key_widgets_map:
                        for widget in self.key_widgets_map[key_char_upper]:
                            widget.update_shortcut_display(display_text)
                            # Apply highlight style as these are active due to modifiers.
                            widget.shortcut_label.setStyleSheet(highlight_shortcut_label_style)
        
        # Process "NoModifier" shortcuts, display them only if the key has no other shortcut shown.
        no_modifier_key_name = "NoModifier"
        if no_modifier_key_name in app_shortcuts:
            shortcuts_no_modifier = app_shortcuts[no_modifier_key_name]
            if shortcuts_no_modifier:
                for key_char_upper, desc_obj in shortcuts_no_modifier.items():
                    display_text = get_final_string_description(desc_obj)
                    if key_char_upper in self.key_widgets_map:
                        for widget in self.key_widgets_map[key_char_upper]:
                            if not widget.shortcut_label.text(): 
                                widget.update_shortcut_display(display_text)

    
    @Slot(str)
    def on_active_app_changed(self, app_name: str) -> None:
        """Slot for active application change. Updates displayed shortcuts."""
        self.active_app_name = app_name.upper() if app_name else "DEFAULT"
        self.update_shortcut_display()

    @Slot(str, str)
    def on_key_event(self, key_name_std: str, event_type: str) -> None:
        """Slot for physical key events. Updates key visuals and shortcut display if needed."""
        normalized_key: str = key_name_std.upper() if key_name_std else ""
        if not normalized_key: return

        if event_type == "down": self._physically_pressed_key_names.add(normalized_key)
        elif event_type == "up": self._physically_pressed_key_names.discard(normalized_key)
        
        self._update_all_key_visuals()
        # If all keys are up (physical and logical), reset shortcut highlights.
        if not self._physically_pressed_key_names and not self.current_logical_modifiers:
            self.update_shortcut_display() # This will clear highlights.

    @Slot(set)
    def on_modifiers_changed(self, modifiers_set_lower: Set[str]) -> None:
        """Slot for logical modifier key state changes. Updates visuals and shortcuts."""
        modifier_mapping: Dict[str, str] = {"ctrl":"CTRL", "shift":"SHIFT", "alt":"ALT", "win":"WIN"}
        new_logical_modifiers: Set[str] = {modifier_mapping[mod] for mod in modifiers_set_lower if mod in modifier_mapping}
        
        if self.current_logical_modifiers != new_logical_modifiers:
            self.current_logical_modifiers = new_logical_modifiers
            self._update_all_key_visuals()
            self.update_shortcut_display() # Re-evaluate shortcuts and their highlights.
        
        if not self.current_logical_modifiers and not self._physically_pressed_key_names:
            self.update_shortcut_display() # Clear highlights if no modifiers active.

    def _update_all_key_visuals(self) -> None:
        """Updates the visual style of KeyWidget's key_label based on press state."""
        for key_widget_list in self.key_widgets_map.values():
            for widget in key_widget_list:
                # The setStyleSheet("") on widget itself was removed as KeyWidget's internal
                # methods already call it before applying key_label styles.
                is_physically_pressed = widget.key_text_upper in self._physically_pressed_key_names
                is_logically_active_modifier = widget.key_text_upper in self.current_logical_modifiers
                if is_logically_active_modifier: widget.set_modifier_active_style()
                elif is_physically_pressed: widget.set_pressed_style()
                else: widget.set_default_style()

    def _get_current_modifier_string_for_config(self) -> Optional[str]:
        """Generates a string for the current modifier combination for config lookup."""
        s_lower = {mod.lower() for mod in self.current_logical_modifiers}
        if "ctrl" in s_lower and "shift" in s_lower and not ("alt" in s_lower or "win" in s_lower): return "Ctrl+Shift"
        if "ctrl" in s_lower and "alt" in s_lower and not ("shift" in s_lower or "win" in s_lower): return "Ctrl+Alt"
        if len(s_lower) == 1:
            mod = s_lower.pop()
            if mod == "ctrl": return "Ctrl"
            if mod == "alt": return "Alt"
            if mod == "shift": return "Shift"
            if mod == "win": return "Win"
            return mod.title()
        if not s_lower: return None
        ordered_mods: List[str] = []
        if "ctrl" in s_lower: ordered_mods.append("Ctrl")
        if "alt" in s_lower: ordered_mods.append("Alt")
        if "shift" in s_lower: ordered_mods.append("Shift")
        if "win" in s_lower: ordered_mods.append("Win")
        return "+".join(ordered_mods) if ordered_mods else None
    
    def retranslate_ui(self) -> None:
        """Handles UI re-translation when application language changes."""
        self.update_shortcut_display()
        self.apply_theme()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles window resize events."""
        super().resizeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        """Handles Qt's change events, specifically LanguageChange."""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handles mouse press for window dragging, excluding QSizeGrip."""
        if event.button() == Qt.LeftButton:
            if self.size_grip and self.size_grip.geometry().contains(event.position().toPoint()):
                super().mousePressEvent(event); return
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handles mouse move for window dragging."""
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos); event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handles mouse release to finalize window dragging."""
        if event.button() == Qt.LeftButton and not self._drag_pos.isNull():
            self._drag_pos = QPoint(); event.accept()
        else: super().mouseReleaseEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        """Applies Win32 styles when the window is shown."""
        super().showEvent(event); self._apply_window_styles()

    def _apply_window_styles(self) -> None:
        """Applies Win32 specific window styles for overlay behavior."""
        hwnd = int(self.winId())
        if hwnd:
            try:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED | win32con.WS_EX_NOACTIVATE)
            except Exception as e: print(f"Error setting Win32 window styles: {e}")