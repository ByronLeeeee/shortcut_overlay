# scripts/settings_dialog.py
"""
Defines dialogs for application settings and "About" information.
SettingsDialog allows users to configure themes for the main overlay, opacity,
language, and custom colors. It applies these settings immediately and uses a
fixed dark theme for its own UI. AboutDialog also uses a fixed dark theme.
"""
from typing import Dict, Any, Optional, Literal, List, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QLabel,
    QSlider,
    QPushButton,
    QDialogButtonBox,
    QGroupBox,
    QColorDialog,
    QWidget,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QColor

try:
    from . import __version__
except ImportError:
    try:
        from .__version__ import __version__
    except ImportError:
        __version__ = "0.0.0-dev"  # Fallback version.

# Type alias for custom color selection.
CustomColorType = Literal["custom_bg_color", "custom_key_color", "custom_text_color"]
# Type alias for the dictionary structure of application settings.
SettingsDict = Dict[str, Any]


class SettingsDialog(QDialog):
    """
    A dialog for configuring application settings.
    Settings for the main overlay (theme, opacity, custom colors) and application
    language are applied immediately upon user interaction. This dialog itself
    maintains a fixed dark visual theme.
    """

    # Signal emitted when any setting is changed by the user in the dialog.
    settings_changed = Signal(dict)

    # Default theme ID for the main overlay, used if no theme is configured.
    DEFAULT_THEME_ID: str = "Default Dark"
    # Available languages for the application UI, with fixed display names.
    AVAILABLE_LANGUAGES: List[Tuple[str, str]] = [
        ("en_US", "English"),
        ("zh_CN", "简体中文"),  # Simplified Chinese
    ]
    # Default language ID for the application.
    DEFAULT_LANGUAGE_ID: str = AVAILABLE_LANGUAGES[0][0]

    # --- Fixed colors for THIS dialog's UI (dark theme inspired) ---
    DIALOG_TEXT_COLOR: str = "#D8DEE9"
    DIALOG_BACKGROUND_COLOR: str = "#2E2E3A"
    BUTTON_BACKGROUND_COLOR: str = "#4A4E5A"
    BUTTON_BORDER_COLOR: str = "#5A5E6A"
    BUTTON_HOVER_BG_COLOR: str = "#5A5E6A"
    BUTTON_PRESSED_BG_COLOR: str = "#3A3E4A"
    GROUPBOX_BORDER_COLOR: str = "#4A4E5A"
    SLIDER_GROOVE_BG_COLOR: str = "#555555"
    SLIDER_GROOVE_BORDER_COLOR: str = "#444444"
    SLIDER_HANDLE_BG_COLOR: str = "#CCCCCC"
    SLIDER_HANDLE_BORDER_COLOR: str = "#BBBBBB"
    COMBOBOX_SELECTION_BG_COLOR: str = "#5A5E6A"

    def __init__(
        self, current_settings: SettingsDict, parent: Optional[QWidget] = None
    ):
        """
        Initializes the SettingsDialog.

        Args:
            current_settings: The current application settings, used to populate
                              the dialog's initial state.
            parent: The parent widget of this dialog.
        """
        super().__init__(parent)
        self.setObjectName("SettingsDialog")  # For specific QSS styling.
        # self.setAttribute(Qt.WA_TranslucentBackground) # Enable if DIALOG_BACKGROUND_COLOR uses alpha.

        self.setWindowTitle(self.tr("Settings"))  # Translatable window title.
        self._initial_settings: SettingsDict = current_settings.copy()

        # Initialize QColor objects for custom color pickers based on current settings.
        self._temp_custom_bg_color: QColor = QColor(
            self._initial_settings.get("custom_bg_color", "#AA14141E")
        )
        self._temp_custom_key_color: QColor = QColor(
            self._initial_settings.get("custom_key_color", "#CC32323C")
        )
        self._temp_custom_text_color: QColor = QColor(
            self._initial_settings.get("custom_text_color", "#FFFFFFFF")
        )

        # Declare UI element instance variables.
        self._theme_group_box: Optional[QGroupBox] = None
        self._opacity_group_box: Optional[QGroupBox] = None
        self._language_group_box: Optional[QGroupBox] = None
        self.theme_combo: Optional[QComboBox] = None
        self.lang_combo: Optional[QComboBox] = None
        self.opacity_slider: Optional[QSlider] = None
        self.opacity_label: Optional[QLabel] = None
        self.custom_bg_color_button: Optional[QPushButton] = None
        self.custom_key_color_button: Optional[QPushButton] = None
        self.custom_text_color_button: Optional[QPushButton] = None
        self.button_box: Optional[QDialogButtonBox] = None
        self._theme_form_label: Optional[QLabel] = None
        self._opacity_form_label: Optional[QLabel] = None
        self._language_form_label: Optional[QLabel] = None
        self._custom_bg_row_label: Optional[QLabel] = None
        self._custom_key_row_label: Optional[QLabel] = None
        self._custom_text_row_label: Optional[QLabel] = None

        # Setup main layout and UI groups.
        self._main_layout: QVBoxLayout = QVBoxLayout(self)
        self._setup_theme_group()
        self._setup_opacity_group()
        self._setup_language_group()
        self._setup_buttons()  # Configures OK and Cancel buttons.

        self.apply_fixed_dialog_styles()  # Apply this dialog's own fixed styling.
        self.setMinimumWidth(400)

        # Connect widget signals to trigger instant application of settings.
        if self.theme_combo:
            self.theme_combo.currentIndexChanged.connect(
                self._on_setting_changed_by_user
            )
        if self.opacity_slider:
            # Emit change when user finishes dragging the slider.
            self.opacity_slider.sliderReleased.connect(self._on_setting_changed_by_user)
        if self.lang_combo:
            self.lang_combo.currentIndexChanged.connect(
                self._on_setting_changed_by_user
            )
        # Custom color changes are handled within _select_color.

    def apply_fixed_dialog_styles(self) -> None:
        """Applies this dialog's fixed dark theme-like styles to all relevant UI elements."""
        stylesheet = f"""
            QDialog#SettingsDialog {{ background-color: {self.DIALOG_BACKGROUND_COLOR}; }}
            QLabel, QGroupBox, QCheckBox {{ color: {self.DIALOG_TEXT_COLOR}; background-color: transparent; }}
            QGroupBox {{ border: 1px solid {self.GROUPBOX_BORDER_COLOR}; border-radius: 4px; margin-top: 12px; padding: 10px 5px 5px 5px; }}
            QGroupBox::title {{ color: {self.DIALOG_TEXT_COLOR}; subcontrol-origin: margin; subcontrol-position: top center; padding-left: 5px; padding-right: 5px; background-color: transparent; }}
            QPushButton {{ color: {self.DIALOG_TEXT_COLOR}; background-color: {self.BUTTON_BACKGROUND_COLOR}; border: 1px solid {self.BUTTON_BORDER_COLOR}; padding: 5px 10px; border-radius: 3px; }}
            QPushButton:hover {{ background-color: {self.BUTTON_HOVER_BG_COLOR}; }}
            QPushButton:pressed {{ background-color: {self.BUTTON_PRESSED_BG_COLOR}; }}
            QComboBox {{ color: {self.DIALOG_TEXT_COLOR}; background-color: {self.BUTTON_BACKGROUND_COLOR}; border: 1px solid {self.BUTTON_BORDER_COLOR}; padding: 4px 5px; border-radius: 3px; selection-background-color: {self.COMBOBOX_SELECTION_BG_COLOR}; }}
            QComboBox:hover {{ border-color: {self.BUTTON_HOVER_BG_COLOR}; }}
            QComboBox::drop-down {{ border: none; width: 15px; background-color: {self.BUTTON_BACKGROUND_COLOR}; }}
            /* QComboBox::down-arrow {{ image: url(:/icons/light_arrow.svg); }} */ /* Example for custom arrow */
            QComboBox QAbstractItemView {{ color: {self.DIALOG_TEXT_COLOR}; background-color: {self.DIALOG_BACKGROUND_COLOR}; border: 1px solid {self.BUTTON_BORDER_COLOR}; selection-background-color: {self.COMBOBOX_SELECTION_BG_COLOR}; selection-color: {self.DIALOG_TEXT_COLOR}; outline: 0px; }}
            QSlider {{ background-color: transparent; }}
            QSlider::groove:horizontal {{ background: {self.SLIDER_GROOVE_BG_COLOR}; height: 8px; border-radius: 4px; border: 1px solid {self.SLIDER_GROOVE_BORDER_COLOR}; }}
            QSlider::handle:horizontal {{ background: {self.SLIDER_HANDLE_BG_COLOR}; border: 1px solid {self.SLIDER_HANDLE_BORDER_COLOR}; width: 14px; margin: -4px 0; border-radius: 7px; }}
        """
        self.setStyleSheet(stylesheet)

    def _setup_theme_group(self) -> None:
        """Creates and configures the theme selection group box for the main overlay."""
        self._theme_group_box = QGroupBox(self.tr("Appearance"))
        theme_layout = QFormLayout(self._theme_group_box)
        self.theme_combo = QComboBox()
        self.theme_id_map: Dict[str, str] = {
            "Default Dark": self.tr("Default Dark"),
            "Light Steel": self.tr("Light Steel"),
            "Midnight Blue": self.tr("Midnight Blue"),
            "Nord Dark": self.tr("Nord Dark"),
            "Tokyo Night": self.tr("Tokyo Night"),
            "Dracula": self.tr("Dracula"),
            "Forest Green": self.tr("Forest Green"),
            "Warm Sepia": self.tr("Warm Sepia"),
            "Soft Purple": self.tr("Soft Purple"),
            "High Contrast Dark": self.tr("High Contrast Dark"),
            "High Contrast Light": self.tr("High Contrast Light"),
            "Neon Cyber": self.tr("Neon Cyber"),
            "RGB Gaming": self.tr("RGB Gaming"),
            "Retro Synthwave": self.tr("Retro Synthwave"),
            "Corporate Blue": self.tr("Corporate Blue"),
            "Elegant Gray": self.tr("Elegant Gray"),
            "Professional Green": self.tr("Professional Green"),
            "Sunset Orange": self.tr("Sunset Orange"),
            "Cherry Blossom": self.tr("Cherry Blossom"),
            "Golden Hour": self.tr("Golden Hour"),
            "Ocean Breeze": self.tr("Ocean Breeze"),
            "Spring Mint": self.tr("Spring Mint"),
            "Lavender Dream": self.tr("Lavender Dream"),
            "Pure White": self.tr("Pure White"),
            "Deep Black": self.tr("Deep Black"),
            "Monochrome": self.tr("Monochrome"),
            "Low Light": self.tr("Low Light"),
            "Blue Light Filter": self.tr("Blue Light Filter"),
            "Accessibility": self.tr("Accessibility"),
            "Custom": self.tr("Custom..."),
        }
        current_theme_id: str = self._initial_settings.get(
            "theme_name", self.DEFAULT_THEME_ID
        )
        for internal_id_key, display_name_val in self.theme_id_map.items():
            self.theme_combo.addItem(
                display_name_val, userData=internal_id_key
            )  # Store internal ID

        idx = self.theme_combo.findData(current_theme_id)  # Find by internal ID
        if idx != -1:
            self.theme_combo.setCurrentIndex(idx)
        else:
            self.theme_combo.setCurrentIndex(
                self.theme_combo.findData(self.DEFAULT_THEME_ID)
            )

        self.custom_bg_color_button = QPushButton(self.tr("Background Color..."))
        self.custom_key_color_button = QPushButton(self.tr("Key Color..."))
        self.custom_text_color_button = QPushButton(self.tr("Key Text Color..."))
        self.custom_bg_color_button.clicked.connect(
            lambda: self._select_color("custom_bg_color")
        )
        self.custom_key_color_button.clicked.connect(
            lambda: self._select_color("custom_key_color")
        )
        self.custom_text_color_button.clicked.connect(
            lambda: self._select_color("custom_text_color")
        )

        # Also connect currentIndexChanged here for visibility update, as _on_setting_changed_by_user handles the emit
        self.theme_combo.currentIndexChanged.connect(
            self._update_custom_color_buttons_visibility
        )

        self._theme_form_label = QLabel(self.tr("Theme:"))
        theme_layout.addRow(self._theme_form_label, self.theme_combo)
        self._custom_bg_row_label = QLabel(self.tr("Custom BG:"))
        self._custom_key_row_label = QLabel(self.tr("Custom Key:"))
        self._custom_text_row_label = QLabel(self.tr("Custom Text:"))
        theme_layout.addRow(self._custom_bg_row_label, self.custom_bg_color_button)
        theme_layout.addRow(self._custom_key_row_label, self.custom_key_color_button)
        theme_layout.addRow(self._custom_text_row_label, self.custom_text_color_button)
        self._main_layout.addWidget(self._theme_group_box)
        self._update_custom_color_buttons_visibility()  # Initial check

    def _setup_opacity_group(self) -> None:
        """Creates and configures the opacity slider group box for the main overlay."""
        self._opacity_group_box = QGroupBox(self.tr("Opacity"))
        opacity_layout = QFormLayout(self._opacity_group_box)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(20)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self._initial_settings.get("opacity", 85)))
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(
            lambda value: self.opacity_label.setText(f"{value}%")
        )
        self._opacity_form_label = QLabel(self.tr("Window Opacity:"))
        opacity_layout.addRow(self._opacity_form_label, self.opacity_slider)
        opacity_layout.addRow(
            "", self.opacity_label
        )  # For alignment with slider value.
        self._main_layout.addWidget(self._opacity_group_box)

    def _setup_language_group(self) -> None:
        """Creates and configures the language selection group box for the application UI."""
        self._language_group_box = QGroupBox(self.tr("Language"))
        lang_layout = QFormLayout(self._language_group_box)
        self.lang_combo = QComboBox()
        current_lang_id: str = self._initial_settings.get(
            "language", self.DEFAULT_LANGUAGE_ID
        )
        for index, (lang_id, display_name) in enumerate(self.AVAILABLE_LANGUAGES):
            self.lang_combo.addItem(
                display_name, userData=lang_id
            )  # Fixed display names.
            if lang_id == current_lang_id:
                self.lang_combo.setCurrentIndex(index)
        self._language_form_label = QLabel(self.tr("Interface Language:"))
        lang_layout.addRow(self._language_form_label, self.lang_combo)
        self._main_layout.addWidget(self._language_group_box)

    def _setup_buttons(self) -> None:
        """Creates and configures the dialog's OK and Cancel buttons."""
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)  # OK simply closes the dialog.
        self.button_box.rejected.connect(self.reject)  # Cancel closes the dialog.
        self._main_layout.addWidget(self.button_box)

    @Slot()
    def _on_setting_changed_by_user(self) -> None:
        """
        Slot called when a UI setting is changed by the user.
        It emits the `settings_changed` signal with all current dialog settings
        for live application of changes.
        """
        self.settings_changed.emit(self.get_current_settings_from_dialog())
        # If the theme combo was the sender, update custom color button visibility.
        if self.sender() == self.theme_combo:
            self._update_custom_color_buttons_visibility()

    @Slot(str)
    def _select_color(self, color_type: CustomColorType) -> None:
        """
        Opens a QColorDialog for custom color selection and triggers a settings update
        if a new color is chosen.

        Args:
            color_type: Specifies which custom color is being selected.
        """
        initial_color: QColor
        dialog_title: str
        if color_type == "custom_bg_color":
            initial_color, dialog_title = self._temp_custom_bg_color, self.tr(
                "Select Background Color"
            )
        elif color_type == "custom_key_color":
            initial_color, dialog_title = self._temp_custom_key_color, self.tr(
                "Select Key Color"
            )
        elif color_type == "custom_text_color":
            initial_color, dialog_title = self._temp_custom_text_color, self.tr(
                "Select Key Text Color"
            )
        else:
            return

        color = QColorDialog.getColor(
            initial_color, self, dialog_title, QColorDialog.ShowAlphaChannel
        )
        if color.isValid():  # If a color was selected and is valid.
            changed = False
            if color_type == "custom_bg_color" and self._temp_custom_bg_color != color:
                self._temp_custom_bg_color = color
                changed = True
            elif (
                color_type == "custom_key_color"
                and self._temp_custom_key_color != color
            ):
                self._temp_custom_key_color = color
                changed = True
            elif (
                color_type == "custom_text_color"
                and self._temp_custom_text_color != color
            ):
                self._temp_custom_text_color = color
                changed = True

            if changed:  # If the color actually changed, trigger settings update.
                self._on_setting_changed_by_user()

    def _update_custom_color_buttons_visibility(self) -> None:
        """Shows or hides custom color selection UI elements based on the selected overlay theme."""
        if not self.theme_combo:
            return
        selected_theme_id = self.theme_combo.currentData()  # Get internal theme ID.
        is_custom_theme = selected_theme_id == "Custom"

        # Toggle visibility of labels and buttons for custom color pickers.
        if hasattr(self, "_custom_bg_row_label") and self._custom_bg_row_label:
            self._custom_bg_row_label.setVisible(is_custom_theme)
        if self.custom_bg_color_button:
            self.custom_bg_color_button.setVisible(is_custom_theme)
        if hasattr(self, "_custom_key_row_label") and self._custom_key_row_label:
            self._custom_key_row_label.setVisible(is_custom_theme)
        if self.custom_key_color_button:
            self.custom_key_color_button.setVisible(is_custom_theme)
        if hasattr(self, "_custom_text_row_label") and self._custom_text_row_label:
            self._custom_text_row_label.setVisible(is_custom_theme)
        if self.custom_text_color_button:
            self.custom_text_color_button.setVisible(is_custom_theme)

    def get_current_settings_from_dialog(self) -> SettingsDict:
        """
        Retrieves the currently selected settings from the dialog's UI elements.

        Returns:
            A dictionary containing all current settings.
        """
        theme_id = (
            self.theme_combo.currentData()
            if self.theme_combo and self.theme_combo.currentData() is not None
            else self.DEFAULT_THEME_ID
        )
        lang_id = (
            self.lang_combo.currentData()
            if self.lang_combo and self.lang_combo.currentData() is not None
            else self.DEFAULT_LANGUAGE_ID
        )
        opacity_value = self.opacity_slider.value() if self.opacity_slider else 85
        return {
            "theme_name": theme_id,
            "opacity": opacity_value,
            "custom_bg_color": self._temp_custom_bg_color.name(
                QColor.HexArgb
            ),  # Save with alpha.
            "custom_key_color": self._temp_custom_key_color.name(QColor.HexArgb),
            "custom_text_color": self._temp_custom_text_color.name(QColor.HexArgb),
            "language": lang_id,
        }

    def changeEvent(self, event: QEvent) -> None:
        """
        Handles Qt's change events, specifically LanguageChange for retranslating UI text.
        """
        if event.type() == QEvent.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self) -> None:
        """Retranslates the UI text elements of the dialog when the application language changes."""
        self.setWindowTitle(self.tr("Settings"))
        if self._theme_group_box:
            self._theme_group_box.setTitle(self.tr("Appearance"))
        if self._opacity_group_box:
            self._opacity_group_box.setTitle(self.tr("Opacity"))
        if self._language_group_box:
            self._language_group_box.setTitle(self.tr("Language"))
        if self._theme_form_label:
            self._theme_form_label.setText(self.tr("Theme:"))
        if self._opacity_form_label:
            self._opacity_form_label.setText(self.tr("Window Opacity:"))
        if self._language_form_label:
            self._language_form_label.setText(self.tr("Interface Language:"))

        if hasattr(self, "_custom_bg_row_label") and self._custom_bg_row_label:
            self._custom_bg_row_label.setText(self.tr("Custom BG:"))
        if hasattr(self, "_custom_key_row_label") and self._custom_key_row_label:
            self._custom_key_row_label.setText(self.tr("Custom Key:"))
        if hasattr(self, "_custom_text_row_label") and self._custom_text_row_label:
            self._custom_text_row_label.setText(self.tr("Custom Text:"))

        if self.custom_bg_color_button:
            self.custom_bg_color_button.setText(self.tr("Background Color..."))
        if self.custom_key_color_button:
            self.custom_key_color_button.setText(self.tr("Key Color..."))
        if self.custom_text_color_button:
            self.custom_text_color_button.setText(self.tr("Key Text Color..."))

        # Retranslate theme combo box display names while preserving selection.
        if self.theme_combo:
            current_theme_id_data = (
                self.theme_combo.currentData()
            )  # Store current internal ID
            self.theme_id_map = {  # Rebuild map with new translations for display names
                "Default Dark": self.tr("Default Dark"),
                "Light Steel": self.tr("Light Steel"),
                "Midnight Blue": self.tr("Midnight Blue"),
                "Nord Dark": self.tr("Nord Dark"),
                "Tokyo Night": self.tr("Tokyo Night"),
                "Dracula": self.tr("Dracula"),
                "Forest Green": self.tr("Forest Green"),
                "Warm Sepia": self.tr("Warm Sepia"),
                "Soft Purple": self.tr("Soft Purple"),
                "High Contrast Dark": self.tr("High Contrast Dark"),
                "High Contrast Light": self.tr("High Contrast Light"),
                "Neon Cyber": self.tr("Neon Cyber"),
                "RGB Gaming": self.tr("RGB Gaming"),
                "Retro Synthwave": self.tr("Retro Synthwave"),
                "Corporate Blue": self.tr("Corporate Blue"),
                "Elegant Gray": self.tr("Elegant Gray"),
                "Professional Green": self.tr("Professional Green"),
                "Sunset Orange": self.tr("Sunset Orange"),
                "Cherry Blossom": self.tr("Cherry Blossom"),
                "Golden Hour": self.tr("Golden Hour"),
                "Ocean Breeze": self.tr("Ocean Breeze"),
                "Spring Mint": self.tr("Spring Mint"),
                "Lavender Dream": self.tr("Lavender Dream"),
                "Pure White": self.tr("Pure White"),
                "Deep Black": self.tr("Deep Black"),
                "Monochrome": self.tr("Monochrome"),
                "Low Light": self.tr("Low Light"),
                "Blue Light Filter": self.tr("Blue Light Filter"),
                "Accessibility": self.tr("Accessibility"),
                "Custom": self.tr("Custom..."),
            }
            self.theme_combo.clear()
            for internal_id, display_name in self.theme_id_map.items():
                self.theme_combo.addItem(display_name, userData=internal_id)
            # Restore selection based on the previously stored internal ID.
            idx = self.theme_combo.findData(current_theme_id_data)
            if idx != -1:
                self.theme_combo.setCurrentIndex(idx)
            else:
                self.theme_combo.setCurrentIndex(
                    self.theme_combo.findData(self.DEFAULT_THEME_ID)
                )  # Fallback

        # Language combo display names are fixed; ensure selection is correct.
        if self.lang_combo:
            current_lang_id_data = self.lang_combo.currentData()
            idx = self.lang_combo.findData(
                current_lang_id_data
                if current_lang_id_data is not None
                else self.DEFAULT_LANGUAGE_ID
            )
            if idx != -1:
                self.lang_combo.setCurrentIndex(idx)

        self.apply_fixed_dialog_styles()  # Re-apply fixed styles as text changes might affect layout/appearance.


class AboutDialog(QDialog):
    """
    Displays application information (version, author, etc.).
    This dialog uses a fixed dark theme styling consistent with SettingsDialog.
    """

    # Inherit color constants from SettingsDialog for consistency.
    DIALOG_TEXT_COLOR: str = SettingsDialog.DIALOG_TEXT_COLOR
    DIALOG_BACKGROUND_COLOR: str = SettingsDialog.DIALOG_BACKGROUND_COLOR
    BUTTON_BACKGROUND_COLOR: str = SettingsDialog.BUTTON_BACKGROUND_COLOR
    BUTTON_BORDER_COLOR: str = SettingsDialog.BUTTON_BORDER_COLOR
    BUTTON_HOVER_BG_COLOR: str = SettingsDialog.BUTTON_HOVER_BG_COLOR
    BUTTON_PRESSED_BG_COLOR: str = SettingsDialog.BUTTON_PRESSED_BG_COLOR
    LINK_COLOR: str = QColor(DIALOG_TEXT_COLOR).lighter(130).name()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initializes the AboutDialog.

        Args:
            parent: The parent widget of this dialog.
        """
        super().__init__(parent)
        self.setObjectName("AboutDialog")
        # self.setAttribute(Qt.WA_TranslucentBackground) # Enable if DIALOG_BACKGROUND_COLOR uses alpha.

        self.setWindowTitle(self.tr("About Shortcut Overlay"))
        self._main_layout: QVBoxLayout = QVBoxLayout(self)

        # --- Title ---
        self._title_label: QLabel = QLabel(self.tr("Shortcut Overlay"))
        title_font = self._title_label.font(); title_font.setPointSize(16); title_font.setBold(True)
        self._title_label.setFont(title_font); self._title_label.setAlignment(Qt.AlignCenter)
        self._main_layout.addWidget(self._title_label)

        # --- Version ---
        self._version_label: QLabel = QLabel(f"{self.tr('Version:')} {__version__}")
        self._version_label.setAlignment(Qt.AlignCenter)
        self._main_layout.addWidget(self._version_label)

        self._main_layout.addSpacing(10)

        # --- Description ---
        self._description_label: QLabel = QLabel(self.tr("An on-screen keyboard overlay to display application-specific shortcuts."))
        self._description_label.setWordWrap(True); self._description_label.setAlignment(Qt.AlignCenter)
        self._main_layout.addWidget(self._description_label)

        self._main_layout.addSpacing(10)

        # --- Author ---
        author_name = "ByronLeeeee"
        github_link = f"https://github.com/{author_name}"
        author_display_text = f"{self.tr('Author:')} {author_name}"
        self._author_label: QLabel = QLabel(f'<a href="{github_link}">{author_display_text}</a>')
        self._author_label.setOpenExternalLinks(True); self._author_label.setAlignment(Qt.AlignCenter)
        self._main_layout.addWidget(self._author_label)

        # --- Icon Credit ---
        icons8_link = "https://icons8.com"
        icon_credit_text = self.tr("Icons by:") # Make "Icons by:" translatable
        # The link text itself ("Icons8") is not translated to keep the brand name.
        self._icon_credit_label: QLabel = QLabel(f'{icon_credit_text} <a href="{icons8_link}">Icons8</a>')
        self._icon_credit_label.setOpenExternalLinks(True)
        self._icon_credit_label.setAlignment(Qt.AlignCenter)
        self._main_layout.addWidget(self._icon_credit_label) # Add the new label

        self._main_layout.addSpacing(20)

        # --- OK Button ---
        self._ok_button: QPushButton = QPushButton(self.tr("OK"))
        self._ok_button.clicked.connect(self.accept)
        
        button_container_layout = QHBoxLayout(); button_container_layout.addStretch()
        button_container_layout.addWidget(self._ok_button); button_container_layout.addStretch()
        self._main_layout.addLayout(button_container_layout)
        
        self.apply_fixed_styles()
        self.setMinimumWidth(380) # Adjusted width slightly if needed for new text
        self.setModal(True)

    def apply_fixed_styles(self) -> None:
        """Applies this dialog's fixed dark theme-like styles to its UI elements."""
        stylesheet = f"""
            QDialog#AboutDialog {{ background-color: {self.DIALOG_BACKGROUND_COLOR}; }}
            QLabel {{ color: {self.DIALOG_TEXT_COLOR}; background-color: transparent; }}
            QLabel a {{ color: {self.LINK_COLOR}; text-decoration: underline; }}
            QPushButton {{ 
                color: {self.DIALOG_TEXT_COLOR}; 
                background-color: {self.BUTTON_BACKGROUND_COLOR}; 
                border: 1px solid {self.BUTTON_BORDER_COLOR}; 
                padding: 5px 15px; 
                border-radius: 3px; 
            }}
            QPushButton:hover {{ background-color: {self.BUTTON_HOVER_BG_COLOR}; }}
            QPushButton:pressed {{ background-color: {self.BUTTON_PRESSED_BG_COLOR}; }}
        """
        self.setStyleSheet(stylesheet)

    def changeEvent(self, event: QEvent) -> None:
        """Handles Qt's change events, e.g., LanguageChange for retranslating UI text."""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self) -> None:
        """Retranslates the UI text elements of this dialog when the application language changes."""
        self.setWindowTitle(self.tr("About Shortcut Overlay"))
        if hasattr(self, '_title_label') and self._title_label: self._title_label.setText(self.tr("Shortcut Overlay"))
        if hasattr(self, '_version_label') and self._version_label: self._version_label.setText(f"{self.tr('Version:')} {__version__}")
        if hasattr(self, '_description_label') and self._description_label: self._description_label.setText(self.tr("An on-screen keyboard overlay to display application-specific shortcuts."))
        
        if hasattr(self, '_author_label') and self._author_label:
            author_name = "ByronLeeeee"; github_link = f"https://github.com/{author_name}"
            author_display_text = f"{self.tr('Author:')} {author_name}"
            self._author_label.setText(f'<a href="{github_link}">{author_display_text}</a>')
        
        # Retranslate icon credit label
        if hasattr(self, '_icon_credit_label') and self._icon_credit_label:
            icons8_link = "https://icons8.com"
            icon_credit_text = self.tr("Icons by:")
            self._icon_credit_label.setText(f'{icon_credit_text} <a href="{icons8_link}">Icons8</a>')
            
        if hasattr(self, '_ok_button') and self._ok_button: self._ok_button.setText(self.tr("OK"))
        
        self.apply_fixed_styles() # Re-apply styles as text changes might affect appearance or link color.
