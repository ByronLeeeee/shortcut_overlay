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
# Each inner list represents a row of keys.
# Strings are standard keycap text.
# Tuples in the format (keycap_text, relative_stretch_factor) allow for custom key widths.
KEY_LAYOUT: List[List[Union[str, Tuple[str, float]]]] = [
    ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
    [
        "`",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
        "-",
        "=",
        ("Backspace", 2.0),
    ],
    [
        ("Tab", 1.5),
        "Q",
        "W",
        "E",
        "R",
        "T",
        "Y",
        "U",
        "I",
        "O",
        "P",
        "[",
        "]",
        ("\\", 1.5),
    ],
    [
        ("Caps Lock", 1.8),
        "A",
        "S",
        "D",
        "F",
        "G",
        "H",
        "J",
        "K",
        "L",
        ";",
        "'",
        ("Enter", 2.2),
    ],
    [("Shift", 2.5), "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", ("Shift", 2.5)],
    [
        ("Ctrl", 1.5),
        ("Win", 1.2),
        ("Alt", 1.2),
        ("Space", 6.0),
        ("Alt", 1.2),
        ("Win", 1.2),
        ("Menu", 1.2),
        ("Ctrl", 1.5),
    ],
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
        self.key_text_upper: str = (
            key_text.upper()
        )  # Uppercase for consistent internal key matching.
        self.display_text: str = key_text  # Text as it appears on the key.

        self._layout: QVBoxLayout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins around content.
        self._layout.setSpacing(1)  # Minimal spacing between labels.

        self.key_label: QLabel = QLabel(self.display_text)  # Displays keycap text.
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.shortcut_label: QLabel = QLabel("")  # Displays shortcut description.
        self.shortcut_label.setAlignment(Qt.AlignCenter)
        self.shortcut_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.shortcut_label.setWordWrap(True)
        self.shortcut_label.setToolTip(
            ""
        )  # Tooltip can show full shortcut text if elided.

        self._layout.addWidget(
            self.key_label, stretch=2
        )  # Key text gets more vertical space.
        self._layout.addWidget(
            self.shortcut_label, stretch=1
        )  # Shortcut text gets less.

        # Default stylesheets; these are dynamically updated by OverlayKeyboardWindow.apply_theme().
        self._default_key_label_stylesheet: str = (
            "font-weight: bold; color: white; border: 1px solid #444444; border-radius: 3px; padding: 2px; background-color: transparent;"
        )
        self._pressed_key_label_stylesheet: str = (
            "font-weight: bold; color: white; background-color: #5A98D1; border: 1px solid #77BBEF; border-radius: 3px; padding: 2px;"
        )
        self._modifier_active_key_label_stylesheet: str = (
            "font-weight: bold; color: white; background-color: #4682B4; border: 1px solid #66AACC; border-radius: 3px; padding: 2px;"
        )

        # Default palette for the KeyWidget container itself. Also updated by apply_theme().
        self._default_widget_palette: QPalette = QPalette()
        self._default_widget_palette.setColor(
            QPalette.ColorRole.Window, QColor(50, 50, 60, 180)
        )  # Default semi-transparent dark gray.

        self.setAutoFillBackground(
            True
        )  # Ensures the widget's QPalette background is drawn.
        self.set_default_style()  # Apply initial styling.

    def set_default_style(self) -> None:
        """Applies the default visual style to this key."""
        self.setPalette(
            self._default_widget_palette
        )  # Set KeyWidget container's background.
        self.key_label.setStyleSheet(
            self._default_key_label_stylesheet
        )  # Set style for the keycap text label.

    def set_pressed_style(self) -> None:
        """Applies the visual style for a physically pressed key."""
        self.key_label.setStyleSheet(self._pressed_key_label_stylesheet)

    def set_modifier_active_style(self) -> None:
        """Applies the visual style for an active (logical) modifier key."""
        self.key_label.setStyleSheet(self._modifier_active_key_label_stylesheet)

    def update_shortcut_display(self, text: str) -> None:
        """
        Updates the shortcut description text displayed on this key.

        Args:
            text: The shortcut description to display. If empty, clears the display.
        """
        if not text:
            self.shortcut_label.setText("")
            self.shortcut_label.setToolTip("")
            return
        self.shortcut_label.setText(text)
        self.shortcut_label.setToolTip(text)  # Tooltip shows full text.
        # Font size and color for shortcut_label are set via its stylesheet in apply_theme.

    def clear_shortcut_text(self) -> None:
        """Clears the shortcut description text from this key."""
        self.update_shortcut_display("")


class OverlayKeyboardWindow(QWidget):
    """
    The main window for the on-screen keyboard overlay.
    It constructs the keyboard layout from KeyWidgets, handles theming,
    opacity, dragging, resizing, and updates based on application state.
    """

    # Default theme ID used if no theme is found in settings.
    DEFAULT_THEME_ID: str = "Default Dark"
    # Definition of available themes. Each tuple defines colors for:
    # (main_background_rgba, key_widget_container_background_qcolor,
    #  key_label_foreground_color (also used for dialog text), key_label_border_color,
    #  shortcut_label_foreground_color, pressed_key_label_background_hex (OPAQUE),
    #  modifier_key_label_background_hex (OPAQUE))
    THEMES_DEFINITION: Dict[str, Tuple[str, QColor, str, str, str, str, str]] = {
        "Default Dark": (
            "rgba(20, 20, 30, 170)",
            QColor(50, 50, 60, 180),
            "white",
            "#444444",
            "#DDDD00",
            "#5A98D1",
            "#4682B4",
        ),
        "Light Steel": (
            "rgba(200, 205, 210, 190)",
            QColor(230, 235, 240, 220),
            "black",
            "#B0B0B0",
            "#0055A4",
            "#A0D8F0",
            "#7CB9E8",
        ),
        "Midnight Blue": (
            "rgba(25, 25, 112, 180)",
            QColor(40, 40, 130, 200),
            "white",
            "#6060C0",
            "#FFFF00",
            "#3A78B1",
            "#2C5F8F",
        ),
        "Nord Dark": (
            "rgba(46, 52, 64, 185)",
            QColor(67, 76, 94, 200),
            "#D8DEE9",
            "#4C566A",
            "#88C0D0",
            "#5E81AC",
            "#81A1C1",
        ),
        "Tokyo Night": (
            "rgba(26, 27, 38, 180)",
            QColor(41, 42, 58, 195),
            "#C0CAF5",
            "#565F89",
            "#7AA2F7",
            "#BB9AF7",
            "#F7768E",
        ),
        "Dracula": (
            "rgba(40, 42, 54, 175)",
            QColor(68, 71, 90, 190),
            "#F8F8F2",
            "#6272A4",
            "#50FA7B",
            "#BD93F9",
            "#FF79C6",
        ),
        "Forest Green": (
            "rgba(34, 53, 44, 170)",
            QColor(52, 73, 62, 185),
            "#E8F5E8",
            "#2D5A3D",
            "#7ED321",
            "#4CAF50",
            "#66BB6A",
        ),
        "Warm Sepia": (
            "rgba(73, 63, 50, 165)",
            QColor(95, 83, 68, 180),
            "#F5E6D3",
            "#8B7355",
            "#D4AF37",
            "#CD853F",
            "#DEB887",
        ),
        "Soft Purple": (
            "rgba(56, 47, 66, 172)",
            QColor(78, 67, 88, 187),
            "#E6E1F0",
            "#6B5B7B",
            "#9C88FF",
            "#8A7CA8",
            "#B39DDB",
        ),
        "High Contrast Dark": (
            "rgba(0, 0, 0, 200)",
            QColor(33, 33, 33, 220),
            "#FFFFFF",
            "#666666",
            "#00FF00",
            "#0099FF",
            "#FF6600",
        ),
        "High Contrast Light": (
            "rgba(255, 255, 255, 200)",
            QColor(240, 240, 240, 220),
            "#000000",
            "#CCCCCC",
            "#FF0066",
            "#0066FF",
            "#FF9900",
        ),
        "Neon Cyber": (
            "rgba(0, 5, 15, 180)",
            QColor(15, 25, 35, 195),
            "#00FFFF",
            "#003366",
            "#FF00FF",
            "#00FF88",
            "#FF6600",
        ),
        "RGB Gaming": (
            "rgba(18, 18, 18, 185)",
            QColor(35, 35, 35, 200),
            "#FFFFFF",
            "#555555",
            "#FF0080",
            "#8000FF",
            "#00FF80",
        ),
        "Retro Synthwave": (
            "rgba(20, 8, 30, 175)",
            QColor(40, 20, 50, 190),
            "#FF00FF",
            "#4A0E4E",
            "#00FFFF",
            "#FF1493",
            "#FF4500",
        ),
        "Corporate Blue": (
            "rgba(240, 248, 255, 190)",
            QColor(230, 240, 250, 210),
            "#1E3A8A",
            "#B0C4DE",
            "#2563EB",
            "#3B82F6",
            "#60A5FA",
        ),
        "Elegant Gray": (
            "rgba(248, 250, 252, 185)",
            QColor(241, 245, 249, 205),
            "#374151",
            "#D1D5DB",
            "#6366F1",
            "#8B5CF6",
            "#A855F7",
        ),
        "Professional Green": (
            "rgba(240, 253, 244, 188)",
            QColor(220, 252, 231, 208),
            "#064E3B",
            "#A7F3D0",
            "#059669",
            "#10B981",
            "#34D399",
        ),
        "Sunset Orange": (
            "rgba(45, 25, 15, 170)",
            QColor(70, 45, 30, 185),
            "#FFF7ED",
            "#7C2D12",
            "#EA580C",
            "#F97316",
            "#FB923C",
        ),
        "Cherry Blossom": (
            "rgba(60, 40, 50, 168)",
            QColor(85, 65, 75, 183),
            "#FDF2F8",
            "#881337",
            "#E11D48",
            "#F43F5E",
            "#FB7185",
        ),
        "Golden Hour": (
            "rgba(55, 45, 25, 172)",
            QColor(80, 68, 45, 187),
            "#FFFBEB",
            "#92400E",
            "#D97706",
            "#F59E0B",
            "#FBBF24",
        ),
        "Ocean Breeze": (
            "rgba(20, 40, 60, 175)",
            QColor(40, 65, 85, 190),
            "#F0F9FF",
            "#0C4A6E",
            "#0284C7",
            "#0EA5E9",
            "#38BDF8",
        ),
        "Spring Mint": (
            "rgba(30, 50, 40, 170)",
            QColor(50, 75, 65, 185),
            "#F0FDF4",
            "#14532D",
            "#16A34A",
            "#22C55E",
            "#4ADE80",
        ),
        "Lavender Dream": (
            "rgba(45, 35, 60, 173)",
            QColor(70, 60, 85, 188),
            "#FAF5FF",
            "#581C87",
            "#7C3AED",
            "#8B5CF6",
            "#A78BFA",
        ),
        "Pure White": (
            "rgba(255, 255, 255, 200)",
            QColor(248, 250, 252, 220),
            "#111827",
            "#E5E7EB",
            "#3B82F6",
            "#6366F1",
            "#8B5CF6",
        ),
        "Deep Black": (
            "rgba(0, 0, 0, 190)",
            QColor(17, 24, 39, 210),
            "#F9FAFB",
            "#374151",
            "#10B981",
            "#06B6D4",
            "#8B5CF6",
        ),
        "Monochrome": (
            "rgba(128, 128, 128, 180)",
            QColor(156, 163, 175, 195),
            "#FFFFFF",
            "#6B7280",
            "#000000",
            "#374151",
            "#111827",
        ),
        "Low Light": (
            "rgba(15, 15, 15, 185)",
            QColor(30, 30, 30, 200),
            "#DC2626",
            "#1F2937",
            "#EF4444",
            "#F87171",
            "#FCA5A5",
        ),
        "Blue Light Filter": (
            "rgba(50, 40, 30, 175)",
            QColor(70, 60, 50, 190),
            "#FEF3C7",
            "#92400E",
            "#F59E0B",
            "#FBBF24",
            "#FCD34D",
        ),
        "Accessibility": (
            "rgba(255, 255, 255, 220)",
            QColor(0, 0, 0, 255),
            "#000000",
            "#808080",
            "#0000FF",
            "#FF0000",
            "#008000",
        ),
    }

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        """
        Initializes the OverlayKeyboardWindow.

        Args:
            config_manager: Instance of ConfigManager for accessing settings.
            parent: The parent QWidget, if any.
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.active_app_name: str = "DEFAULT"  # Currently focused application.
        self.current_logical_modifiers: Set[str] = (
            set()
        )  # Active logical modifiers (e.g., "CTRL").
        self.key_widgets_map: Dict[str, List[KeyWidget]] = (
            {}
        )  # Maps key text to KeyWidget instances.
        self._drag_pos: QPoint = QPoint()  # Stores offset for window dragging.
        self._physically_pressed_key_names: Set[str] = (
            set()
        )  # Tracks physically held keys.

        # Effect for controlling the overall window opacity.
        self.opacity_effect: QGraphicsOpacityEffect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)  # Initial full opacity.
        self.setGraphicsEffect(self.opacity_effect)

        # UI element placeholders.
        self.main_layout: Optional[QVBoxLayout] = None
        self.keyboard_layout_container: Optional[QWidget] = None
        self.size_grip: Optional[QSizeGrip] = None

        self.init_ui()  # Construct UI elements.
        self.set_window_properties()  # Set window flags for overlay behavior.
        self.apply_current_settings()  # Apply initial theme and opacity.

    def init_ui(self) -> None:
        """Initializes the user interface elements of the overlay window,
        constructing the keyboard layout from KEY_LAYOUT.
        """
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(1)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        self.keyboard_layout_container = QWidget()  # Container for the grid of keys.
        keyboard_grid_layout = QVBoxLayout(self.keyboard_layout_container)
        keyboard_grid_layout.setSpacing(3)  # Spacing between key rows.
        keyboard_grid_layout.setContentsMargins(5, 5, 5, 5)

        for row_keys in KEY_LAYOUT:  # Iterate through each row definition.
            row_layout = QHBoxLayout()
            row_layout.setSpacing(3)  # Spacing between keys in a row.
            for key_spec in row_keys:
                stretch_factor: float = 1.0
                key_text_from_layout: str
                if isinstance(key_spec, tuple):  # (key_text, stretch_factor)
                    key_text_from_layout, stretch_factor = key_spec
                else:  # Just key_text
                    key_text_from_layout = key_spec

                key_widget = KeyWidget(key_text_from_layout)
                row_layout.addWidget(
                    key_widget, stretch=int(stretch_factor * 10)
                )  # Stretch relative to 10.
                # Store KeyWidget instance for later access.
                self.key_widgets_map.setdefault(key_widget.key_text_upper, []).append(
                    key_widget
                )
            keyboard_grid_layout.addLayout(row_layout)
        self.main_layout.addWidget(self.keyboard_layout_container)

        # Add QSizeGrip for window resizing.
        size_grip_layout = QHBoxLayout()
        size_grip_layout.addStretch()  # Push grip to the right.
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(16, 16)
        self.size_grip.setStyleSheet(  # Basic styling for visibility.
            "QSizeGrip { background-color: rgba(100,100,120,100); border: 1px solid rgba(150,150,180,150); }"
            "QSizeGrip:hover { background-color: rgba(120,120,150,180); }"
            "QSizeGrip:pressed { background-color: rgba(80,80,100,220); }"
        )
        size_grip_layout.addWidget(self.size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.main_layout.addLayout(size_grip_layout)

        self.setMinimumSize(600, 200)  # Default minimum size.
        self.resize(850, 280)  # Default initial size.

    def set_window_properties(self) -> None:
        """Sets Qt window flags and attributes for typical overlay behavior
        (always on top, frameless, tool window, translucent background).
        """
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(
            Qt.WA_TranslucentBackground
        )  # Enable transparency for RGBA backgrounds.

    def apply_current_settings(self) -> None:
        """Applies current settings from ConfigManager (theme and opacity) to this window."""
        opacity_percent: int = self.config_manager.get_setting("opacity", 85)
        if (
            hasattr(self, "opacity_effect") and self.opacity_effect
        ):  # Ensure effect exists.
            self.opacity_effect.setOpacity(opacity_percent / 100.0)

        self.apply_theme()  # Apply color theme.
        self.update_shortcut_display()  # Refresh shortcut text.
        self.update()  # Schedule a repaint.

    def apply_theme(self) -> None:
        """
        Applies the selected visual theme to the overlay window and all its KeyWidgets.
        This involves setting background colors, text colors, borders, etc., based on
        the theme definition.
        """
        theme_id: str = self.config_manager.get_setting(
            "theme_name", self.DEFAULT_THEME_ID
        )
        themes = self.THEMES_DEFINITION  # Use the class-level theme definitions.

        # Retrieve custom theme colors if "Custom" theme is selected.
        custom_bg_color_str: str = self.config_manager.get_setting(
            "custom_bg_color", "#AA14141E"
        )
        custom_key_color_str: str = self.config_manager.get_setting(
            "custom_key_color", "#CC32323C"
        )
        custom_text_color_str: str = self.config_manager.get_setting(
            "custom_text_color", "#FFFFFFFF"
        )
        default_shortcut_color: str = "#DDDD00"  # Fallback for shortcut text color.

        # Variables to hold the properties of the currently selected theme.
        main_bg_rgba_str: str
        key_widget_container_bg_qcolor: QColor
        key_label_fg_str: str
        key_label_border_str: str
        shortcut_fg_str: str
        pressed_label_bg_hex: str  # OPAQUE background for pressed KeyLabel.
        modifier_label_bg_hex: str  # OPAQUE background for active modifier KeyLabel.

        if theme_id == "Custom":
            main_bg_rgba_str = QColor(custom_bg_color_str).name(QColor.HexArgb)
            key_widget_container_bg_qcolor = QColor(
                custom_key_color_str
            )  # Can be semi-transparent.
            key_label_fg_str = QColor(custom_text_color_str).name(
                QColor.HexRgb
            )  # Text is opaque.
            key_label_border_str = QColor(key_label_fg_str).darker(150).name()
            shortcut_fg_str = default_shortcut_color
            # Derive pressed/active colors from custom_key_color, ensuring opacity.
            temp_opaque_key_color = QColor(custom_key_color_str)
            temp_opaque_key_color.setAlpha(255)
            pressed_label_bg_hex = temp_opaque_key_color.lighter(130).name(
                QColor.HexRgb
            )
            modifier_label_bg_hex = temp_opaque_key_color.lighter(115).name(
                QColor.HexRgb
            )
        elif theme_id in themes:
            # Unpack values from the selected predefined theme.
            (
                main_bg_rgba_str,
                key_widget_container_bg_qcolor,
                key_label_fg_str,
                key_label_border_str,
                shortcut_fg_str,
                pressed_label_bg_hex,
                modifier_label_bg_hex,
            ) = themes[theme_id]
        else:  # Fallback to default theme if configured theme_id is not found.
            (
                main_bg_rgba_str,
                key_widget_container_bg_qcolor,
                key_label_fg_str,
                key_label_border_str,
                shortcut_fg_str,
                pressed_label_bg_hex,
                modifier_label_bg_hex,
            ) = themes[self.DEFAULT_THEME_ID]

        # Apply background to the main overlay window.
        self.setStyleSheet(f"background-color: {main_bg_rgba_str};")

        # Apply theme to each KeyWidget.
        for key_list in self.key_widgets_map.values():
            for kw in key_list:
                # Set KeyWidget container's background (can be semi-transparent).
                current_palette = kw.palette()
                current_palette.setColor(
                    QPalette.ColorRole.Window, key_widget_container_bg_qcolor
                )
                kw.setPalette(current_palette)

                # Define KeyLabel's default style (keycap text label is transparent over KeyWidget's bg).
                kw._default_key_label_stylesheet = f"font-weight: bold; color: {key_label_fg_str}; border: 1px solid {key_label_border_str}; border-radius: 3px; padding: 2px; background-color: transparent;"
                # Define KeyLabel's pressed/active styles (OPAQUE background to prevent color mixing).
                kw._pressed_key_label_stylesheet = f"font-weight: bold; color: {key_label_fg_str}; background-color: {pressed_label_bg_hex}; border: 1px solid {QColor(pressed_label_bg_hex).darker(120).name()}; border-radius: 3px; padding: 2px;"
                kw._modifier_active_key_label_stylesheet = f"font-weight: bold; color: {key_label_fg_str}; background-color: {modifier_label_bg_hex}; border: 1px solid {QColor(modifier_label_bg_hex).darker(120).name()}; border-radius: 3px; padding: 2px;"
                # Set style for the shortcut description label.
                kw.shortcut_label.setStyleSheet(
                    f"font-size: {DEFAULT_ORIGINAL_SHORTCUT_FONT_SIZE}pt; color: {shortcut_fg_str}; background-color: transparent;"
                )

                kw.set_default_style()  # Apply the newly configured default style to the KeyWidget.

        self._update_all_key_visuals()  # Refresh visuals based on current key states.

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse press events for window dragging.
        Allows dragging if the press is not on the QSizeGrip.
        """
        if event.button() == Qt.LeftButton:
            # If the press is on the QSizeGrip, let it handle resizing.
            if self.size_grip and self.size_grip.geometry().contains(
                event.position().toPoint()
            ):
                super().mousePressEvent(event)
                return

            # Otherwise, initiate window dragging.
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handles mouse move events for window dragging."""
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handles mouse release events to finalize window dragging."""
        if event.button() == Qt.LeftButton and not self._drag_pos.isNull():
            self._drag_pos = QPoint()  # Reset drag state.
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        """Applies necessary Win32 API window styles when the window is shown."""
        super().showEvent(event)
        self._apply_window_styles()  # Apply styles like layered and no-activate.

    def _apply_window_styles(self) -> None:
        """
        Applies Win32 specific window styles (WS_EX_LAYERED, WS_EX_NOACTIVATE)
        for features like click-through (if alpha set by SetLayeredWindowAttributes)
        and preventing the overlay from stealing focus.
        """
        hwnd = int(self.winId())  # Get the window handle.
        if hwnd:
            try:
                current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                new_style = (
                    current_style | win32con.WS_EX_LAYERED | win32con.WS_EX_NOACTIVATE
                )
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
            except Exception as e:
                # Log error if setting Win32 styles fails.
                print(f"Error applying Win32 window styles: {e}")

    @Slot(str)
    def on_active_app_changed(self, app_name: str) -> None:
        """
        Slot to handle changes in the active foreground application.
        Updates the displayed shortcuts based on the new application.

        Args:
            app_name: The executable name of the newly active application.
        """
        self.active_app_name = app_name.upper() if app_name else "DEFAULT"
        self.update_shortcut_display()

    @Slot(str, str)
    def on_key_event(self, key_name_std: str, event_type: str) -> None:
        """
        Slot to handle physical key press/release events from KeyboardHandler.
        Updates the visual state of the corresponding KeyWidget.

        Args:
            key_name_std: The standardized (uppercase) name of the key.
            event_type: "down" for key press, "up" for key release.
        """
        normalized_key: str = key_name_std.upper() if key_name_std else ""
        if not normalized_key:
            return  # Ignore events with no key name.

        if event_type == "down":
            self._physically_pressed_key_names.add(normalized_key)
        elif event_type == "up":
            self._physically_pressed_key_names.discard(normalized_key)
        self._update_all_key_visuals()  # Refresh key appearances.

    @Slot(set)
    def on_modifiers_changed(self, modifiers_set_lower: Set[str]) -> None:
        """
        Slot to handle changes in the set of active logical modifier keys
        (Ctrl, Shift, Alt, Win) from KeyboardHandler.

        Args:
            modifiers_set_lower: A set of active modifier names in lowercase.
        """
        modifier_mapping: Dict[str, str] = {
            "ctrl": "CTRL",
            "shift": "SHIFT",
            "alt": "ALT",
            "win": "WIN",
        }
        uppercase_modifiers: Set[str] = {
            modifier_mapping[mod]
            for mod in modifiers_set_lower
            if mod in modifier_mapping
        }

        if self.current_logical_modifiers != uppercase_modifiers:
            self.current_logical_modifiers = uppercase_modifiers
            self._update_all_key_visuals()  # Update key styles based on new modifiers.
            self.update_shortcut_display()  # Shortcuts depend on active modifiers.

    def _update_all_key_visuals(self) -> None:
        """Updates the visual style (e.g., pressed, active) of all KeyWidgets
        based on the current set of physically pressed keys and active logical modifiers.
        """
        for key_widget_list in self.key_widgets_map.values():
            for widget in key_widget_list:
                is_physically_pressed = (
                    widget.key_text_upper in self._physically_pressed_key_names
                )
                is_logically_active_modifier = (
                    widget.key_text_upper in self.current_logical_modifiers
                )

                if is_logically_active_modifier:  # Modifier is logically active.
                    widget.set_modifier_active_style()
                elif is_physically_pressed:  # Non-modifier key is physically pressed.
                    widget.set_pressed_style()
                else:  # Default state.
                    widget.set_default_style()

    def _get_current_modifier_string_for_config(self) -> Optional[str]:
        """
        Generates a string representation of currently active logical modifiers
        in a format that matches keys in the shortcuts.json configuration file
        (e.g., "Ctrl", "Ctrl+Shift").

        Returns:
            A string representing the modifier combination, or None if no
            relevant modifiers are active. Order of combined modifiers is important.
        """
        s_lower = {
            mod.lower() for mod in self.current_logical_modifiers
        }  # Work with lowercase set.

        # Prioritize common multi-key combinations to match JSON structure.
        if (
            "ctrl" in s_lower
            and "shift" in s_lower
            and "alt" not in s_lower
            and "win" not in s_lower
        ):
            return "Ctrl+Shift"
        if (
            "ctrl" in s_lower
            and "alt" in s_lower
            and "shift" not in s_lower
            and "win" not in s_lower
        ):
            return "Ctrl+Alt"
        # Add other specific combinations (e.g., "Alt+Shift") if they are used as keys in shortcuts.json.

        # Handle single active modifiers.
        if len(s_lower) == 1:
            mod = s_lower.pop()
            if mod == "ctrl":
                return "Ctrl"
            if mod == "alt":
                return "Alt"
            if mod == "shift":
                return "Shift"
            if mod == "win":
                return "Win"
            return mod.title()  # Fallback for less common single modifiers.

        if not s_lower:
            return None  # No relevant modifiers active.

        # Fallback for unhandled combinations: build string in a canonical order.
        # This may not match all JSON keys if they aren't consistently ordered.
        ordered_mods: List[str] = []
        if "ctrl" in s_lower:
            ordered_mods.append("Ctrl")
        if "alt" in s_lower:
            ordered_mods.append("Alt")  # Common order after Ctrl or alone.
        if "shift" in s_lower:
            ordered_mods.append("Shift")  # Often combined.
        if "win" in s_lower:
            ordered_mods.append("Win")
        return "+".join(ordered_mods) if ordered_mods else None

    def update_shortcut_display(self) -> None:
        """
        Updates the shortcut descriptions displayed on all KeyWidgets.
        This is based on the currently active application and the set of active
        logical modifier keys. Descriptions are localized if translations are available.
        """
        # Clear existing shortcut text from all keys.
        for key_list in self.key_widgets_map.values():
            for widget in key_list:
                widget.clear_shortcut_text()

        # Get shortcuts for the current application (or defaults).
        app_shortcuts: Dict[str, Any] = self.config_manager.get_shortcuts_for_app(
            self.active_app_name
        )
        # Determine the current modifier combination string for lookup.
        mod_combo_str: Optional[str] = self._get_current_modifier_string_for_config()

        # Get current language for localized descriptions.
        current_lang_code: str = self.config_manager.get_setting(
            "language", "en_US"
        ).split("_")[0]
        fallback_lang_code: str = (
            "en" if current_lang_code != "en" else "zh"
        )  # Simple fallback logic.

        if mod_combo_str and mod_combo_str in app_shortcuts:
            shortcuts_for_combo: Dict[str, Union[str, Dict[str, str]]] = app_shortcuts[
                mod_combo_str
            ]
            for key_char_upper, desc_obj in shortcuts_for_combo.items():
                display_text: str = (
                    "N/A"  # Default if description is missing/malformed.
                )
                if isinstance(
                    desc_obj, dict
                ):  # Localized format: {"en": "Save", "zh": "保存"}
                    display_text = desc_obj.get(
                        current_lang_code,
                        desc_obj.get(
                            fallback_lang_code, next(iter(desc_obj.values()), "N/A")
                        ),
                    )
                elif isinstance(desc_obj, str):  # Non-localized string format.
                    display_text = desc_obj

                # Update the corresponding KeyWidget(s) if found.
                if key_char_upper in self.key_widgets_map:
                    for widget in self.key_widgets_map[key_char_upper]:
                        widget.update_shortcut_display(display_text)

    def retranslate_ui(self) -> None:
        """
        Handles UI re-translation tasks when the application language changes.
        This primarily involves updating shortcut descriptions (which are language-dependent)
        and re-applying the theme (as theme aspects might eventually be translatable,
        though currently KeyWidget styles are hardcoded or based on non-translatable IDs).
        """
        self.update_shortcut_display()  # Shortcut descriptions depend on language.
        self.apply_theme()  # Re-apply theme in case any aspect of it needs re-evaluation.

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles window resize events."""
        super().resizeEvent(event)
        # If KeyWidget implemented dynamic font sizing for shortcuts,
        # update_shortcut_display() might be called here to refit text.
        # Currently, font size is fixed in KeyWidget.shortcut_label.setStyleSheet.

    def changeEvent(self, event: QEvent) -> None:
        """
        Handles Qt's change events, specifically QEvent.LanguageChange to trigger UI retranslation.
        """
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)
