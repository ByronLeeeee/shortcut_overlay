# scripts/shortcut_manager_dialog.py
"""
Dialog for managing, editing, and importing shortcut configurations.
"""
import json
import os
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem, QLineEdit,
    QInputDialog, QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QDialogButtonBox, QLabel, QWidget
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor

from .config_manager import ConfigManager, ShortcutData # Import necessary types

class ShortcutManagerDialog(QDialog):
    """
    A dialog to view, edit, add, delete, and import shortcut definitions.
    """
    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle(self.tr("Shortcut Manager"))
        self.setObjectName("ShortcutManagerDialog")
        self.setMinimumSize(700, 500)

        self._current_shortcuts: ShortcutData = self.config_manager.get_all_shortcuts() # Get a mutable copy

        self._main_layout: QVBoxLayout = QVBoxLayout(self)

        # UI Elements
        self._app_list_widget: QListWidget # List of application names (e.g., NOTEPAD.EXE, DEFAULT)
        self._shortcut_tree_widget: QTreeWidget # Tree view for modifiers, keys, and descriptions
        
        self._add_app_button: QPushButton
        self._remove_app_button: QPushButton
        self._add_modifier_button: QPushButton
        self._add_shortcut_button: QPushButton
        self._edit_shortcut_button: QPushButton
        self._remove_shortcut_button: QPushButton
        
        self._import_button: QPushButton
        self._save_button: QPushButton # Or apply changes immediately
        self._button_box: QDialogButtonBox # OK/Cancel

        self._setup_ui()
        self._populate_app_list()
        self.apply_dialog_styles() # Apply fixed dark styling

    def apply_dialog_styles(self) -> None:
        """Applies a refined dark styling to this dialog for better aesthetics."""
        
        # Define a color palette for the dialog (can be class constants)
        dialog_bg = "#2B2B2B"  # Slightly darker main background
        text_color = "#E0E0E0" # Light gray text, good contrast on dark bg
        
        item_view_bg = "#3C3C3C" # Background for list, tree, text edit areas
        item_view_border = "#555555"
        
        selection_bg = "#5A98D1" # A distinct selection color (e.g., a muted blue)
        selection_text_color = "#FFFFFF" # Text color for selected items

        button_bg = "#4A4A4A"
        button_border = "#606060"
        button_hover_bg = "#5A5A5A"
        button_pressed_bg = "#404040"

        groupbox_border = "#454545"

        stylesheet = f"""
            QDialog#ShortcutManagerDialog {{ /* Target this dialog specifically if objectName is set */
                background-color: {dialog_bg};
            }}

            /* General Labels (like titles for sections) */
            QLabel {{
                color: {text_color};
                background-color: transparent; /* Should be transparent over parent bg */
                padding: 2px; /* Add a little padding */
            }}

            QGroupBox {{
                color: {text_color}; /* Default text color for content within GBox */
                background-color: transparent; /* Transparent over dialog background */
                border: 1px solid {groupbox_border};
                border-radius: 4px;
                margin-top: 15px; /* Space for the title */
                padding: 10px 8px 8px 8px; /* top, right, bottom, left for content inside */
            }}
            QGroupBox::title {{
                color: {text_color};
                subcontrol-origin: margin;
                subcontrol-position: top left; /* Align title to the left */
                padding: 0 5px 0 5px; /* Padding around the title text */
                left: 10px; /* Offset from the left edge of the groupbox */
                background-color: {dialog_bg}; /* Make title background same as dialog to "cut" the border */
            }}

            /* List and Tree Widgets */
            QListWidget, QTreeWidget {{
                color: {text_color};
                background-color: {item_view_bg};
                border: 1px solid {item_view_border};
                border-radius: 3px;
                alternate-background-color: {QColor(item_view_bg).lighter(105).name()}; /* Subtle striping for rows */
            }}
            QListWidget::item, QTreeWidget::item {{
                padding: 4px; /* Padding for each item */
            }}
            QListWidget::item:selected, QTreeWidget::item:selected {{
                background-color: {selection_bg};
                color: {selection_text_color};
            }}
            QTreeWidget::branch {{ /* Style for expand/collapse arrows if needed */
                /* background-color: transparent; */
            }}
            QHeaderView::section {{ /* For QTreeWidget header */
                background-color: {QColor(item_view_bg).darker(110).name()};
                color: {text_color};
                padding: 4px;
                border: 1px solid {item_view_border};
                border-bottom: 2px solid {selection_bg}; /* Accent for header bottom */
            }}

            /* Text Input Fields */
            QLineEdit, QTextEdit {{
                color: {text_color};
                background-color: {item_view_bg};
                border: 1px solid {item_view_border};
                border-radius: 3px;
                padding: 4px;
                selection-background-color: {selection_bg};
                selection-color: {selection_text_color};
            }}
            QTextEdit {{
                 /* Specific padding for QTextEdit if different from QLineEdit */
            }}

            /* Buttons */
            QPushButton {{
                color: {text_color};
                background-color: {button_bg};
                border: 1px solid {button_border};
                padding: 6px 12px; /* More padding for buttons */
                border-radius: 3px;
                min-height: 1.5em; /* Ensure a decent minimum height */
            }}
            QPushButton:hover {{
                background-color: {button_hover_bg};
                border-color: {QColor(button_border).lighter(120).name()};
            }}
            QPushButton:pressed {{
                background-color: {button_pressed_bg};
            }}
            QPushButton:disabled {{ /* Style for disabled buttons */
                color: #888888;
                background-color: {QColor(button_bg).darker(110).name()};
            }}

            /* QDialogButtonBox styling can be tricky as it contains QPushButtons.
               The QPushButton style above should generally apply.
               If you need to style the box itself: */
            QDialogButtonBox {{
                /* button-layout: 0; /* To control button order if needed */ */
            }}
        """
        self.setStyleSheet(stylesheet)


    def _setup_ui(self) -> None:
        """Creates and arranges UI elements for the dialog."""
        # Top part: App list and shortcut tree
        top_splitter = QHBoxLayout()

        # Left: Application List
        app_list_layout = QVBoxLayout()
        app_list_label = QLabel(self.tr("Applications:"))
        self._app_list_widget = QListWidget()
        self._app_list_widget.setSortingEnabled(True)
        self._app_list_widget.currentItemChanged.connect(self._on_app_selected)
        app_list_buttons_layout = QHBoxLayout()
        self._add_app_button = QPushButton(self.tr("Add App"))
        self._add_app_button.clicked.connect(self._add_application)
        self._remove_app_button = QPushButton(self.tr("Remove App"))
        self._remove_app_button.clicked.connect(self._remove_application)
        app_list_buttons_layout.addWidget(self._add_app_button)
        app_list_buttons_layout.addWidget(self._remove_app_button)
        app_list_layout.addWidget(app_list_label)
        app_list_layout.addWidget(self._app_list_widget)
        app_list_layout.addLayout(app_list_buttons_layout)
        top_splitter.addLayout(app_list_layout, 1) # Ratio 1

        # Right: Shortcut Tree for selected app
        shortcut_view_layout = QVBoxLayout()
        shortcut_label = QLabel(self.tr("Shortcuts for selected application:"))
        self._shortcut_tree_widget = QTreeWidget()
        self._shortcut_tree_widget.setColumnCount(2)
        self._shortcut_tree_widget.setHeaderLabels([self.tr("Key/Modifier"), self.tr("Description")])
        self._shortcut_tree_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        # self._shortcut_tree_widget.itemDoubleClicked.connect(self._edit_selected_shortcut_item)
        
        shortcut_buttons_layout = QHBoxLayout()
        self._add_modifier_button = QPushButton(self.tr("Add Modifier Group"))
        self._add_modifier_button.clicked.connect(self._add_modifier_group)
        self._add_shortcut_button = QPushButton(self.tr("Add Shortcut"))
        self._add_shortcut_button.clicked.connect(self._add_shortcut_to_selected_modifier)
        self._edit_shortcut_button = QPushButton(self.tr("Edit"))
        self._edit_shortcut_button.clicked.connect(self._edit_selected_shortcut_item)
        self._remove_shortcut_button = QPushButton(self.tr("Remove"))
        self._remove_shortcut_button.clicked.connect(self._remove_selected_item)
        
        shortcut_buttons_layout.addWidget(self._add_modifier_button)
        shortcut_buttons_layout.addWidget(self._add_shortcut_button)
        shortcut_buttons_layout.addWidget(self._edit_shortcut_button)
        shortcut_buttons_layout.addWidget(self._remove_shortcut_button)

        shortcut_view_layout.addWidget(shortcut_label)
        shortcut_view_layout.addWidget(self._shortcut_tree_widget)
        shortcut_view_layout.addLayout(shortcut_buttons_layout)
        top_splitter.addLayout(shortcut_view_layout, 3) # Ratio 3

        self._main_layout.addLayout(top_splitter)

        # Bottom part: Import, Save, OK/Cancel
        bottom_buttons_layout = QHBoxLayout()
        self._import_button = QPushButton(self.tr("Import Shortcuts..."))
        self._import_button.clicked.connect(self._import_shortcuts)
        bottom_buttons_layout.addWidget(self._import_button)
        bottom_buttons_layout.addStretch()

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._save_and_accept)
        self._button_box.rejected.connect(self.reject)
        bottom_buttons_layout.addWidget(self._button_box)
        
        self._main_layout.addLayout(bottom_buttons_layout)

    def _populate_app_list(self) -> None:
        """Fills the application list widget with app names from current shortcuts."""
        self._app_list_widget.clear()
        for app_name in sorted(self._current_shortcuts.keys()):
            self._app_list_widget.addItem(QListWidgetItem(app_name))
        if self._app_list_widget.count() > 0:
            self._app_list_widget.setCurrentRow(0)

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_app_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """Called when a new application is selected in the list. Populates the shortcut tree."""
        self._shortcut_tree_widget.clear()
        if not current:
            return
        
        app_name = current.text()
        app_data = self._current_shortcuts.get(app_name, {})

        for modifier_combo, shortcuts in app_data.items():
            modifier_item = QTreeWidgetItem(self._shortcut_tree_widget, [modifier_combo])
            if isinstance(shortcuts, dict):
                for key, description_obj in shortcuts.items():
                    desc_text = ""
                    if isinstance(description_obj, dict): # Localized {"en": "Save", "zh": "保存"}
                        # Display a primary language or join them for editing
                        desc_text = description_obj.get("en", next(iter(description_obj.values()), ""))
                        if "zh" in description_obj and description_obj["zh"] != desc_text:
                            desc_text += f" / {description_obj['zh']}"
                    elif isinstance(description_obj, str): # Simple string
                        desc_text = description_obj
                    
                    QTreeWidgetItem(modifier_item, [key, desc_text])
            self._shortcut_tree_widget.expandItem(modifier_item) # Expand by default

    def _add_application(self) -> None:
        """Prompts for a new application name (e.g., MYAPP.EXE) and adds it."""
        app_name, ok = QInputDialog.getText(self, self.tr("Add Application"), self.tr("Enter application executable name (e.g., MYAPP.EXE):"))
        if ok and app_name:
            app_name_upper = app_name.upper()
            if app_name_upper not in self._current_shortcuts:
                self._current_shortcuts[app_name_upper] = {}
                self._populate_app_list()
                # Select the newly added app
                items = self._app_list_widget.findItems(app_name_upper, Qt.MatchExactly)
                if items:
                    self._app_list_widget.setCurrentItem(items[0])
            else:
                QMessageBox.warning(self, self.tr("Warning"), self.tr("Application already exists."))

    def _remove_application(self) -> None:
        """Removes the selected application and its shortcuts after confirmation."""
        current_item = self._app_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No application selected."))
            return
        
        app_name = current_item.text()

        message_template = self.tr("Are you sure you want to remove '{app_name}' and all its shortcuts?")
        message = message_template.format(app_name=app_name)
        
        reply = QMessageBox.question(self, self.tr("Confirm Removal"), message)
        if reply == QMessageBox.Yes:
            if app_name in self._current_shortcuts:
                del self._current_shortcuts[app_name]
                self._populate_app_list()
                self._shortcut_tree_widget.clear()


    def _add_modifier_group(self) -> None:
        """Adds a new modifier group (e.g., "Ctrl", "Ctrl+Shift") to the selected application."""
        current_app_item = self._app_list_widget.currentItem()
        if not current_app_item:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select an application first."))
            return
        app_name = current_app_item.text()

        modifier_combo, ok = QInputDialog.getText(self, self.tr("Add Modifier Group"),
                                                 self.tr("Enter modifier combination (e.g., Ctrl, Ctrl+Shift, Alt):"))
        if ok and modifier_combo:
            if modifier_combo not in self._current_shortcuts[app_name]:
                self._current_shortcuts[app_name][modifier_combo] = {}
                self._on_app_selected(current_app_item, None) # Refresh tree
            else:
                QMessageBox.warning(self, self.tr("Warning"), self.tr("Modifier group already exists."))


    def _add_shortcut_to_selected_modifier(self) -> None:
        """Adds a new shortcut (key and description) under the selected modifier group."""
        selected_item = self._shortcut_tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a modifier group or an existing shortcut to add under."))
            return

        current_app_item = self._app_list_widget.currentItem()
        if not current_app_item: return # Should not happen if modifier is selected
        app_name = current_app_item.text()

        modifier_combo = ""
        if selected_item.parent() is None: # Selected item is a modifier group
            modifier_combo = selected_item.text(0)
        else: # Selected item is a shortcut, get its parent modifier group
            modifier_combo = selected_item.parent().text(0)
        
        if not modifier_combo: return

        key_name, ok_key = QInputDialog.getText(self, self.tr("Add Shortcut Key"), self.tr("Enter key (e.g., S, F4, Enter):"))
        if not (ok_key and key_name): return

        # For simplicity, ask for English description first. Could be a more complex dialog for multiple languages.
        description_en, ok_desc_en = QInputDialog.getText(self, self.tr("Add Shortcut Description (English)"), self.tr("Enter English description:"))
        if not ok_desc_en: description_en = key_name # Default to key name if empty

        description_zh, ok_desc_zh = QInputDialog.getText(self, self.tr("Add Shortcut Description (Chinese)"), self.tr("Enter Chinese description (optional):"))
        if not ok_desc_zh: description_zh = ""

        new_shortcut_data: Dict[str, str] = {"en": description_en}
        if description_zh:
            new_shortcut_data["zh"] = description_zh
        
        # Normalize key_name (e.g. "s" -> "S") - you might want more robust normalization
        key_name_normalized = key_name.upper() if len(key_name) == 1 and key_name.isalpha() else key_name

        if key_name_normalized not in self._current_shortcuts[app_name][modifier_combo]:
            self._current_shortcuts[app_name][modifier_combo][key_name_normalized] = new_shortcut_data
            self._on_app_selected(current_app_item, None) # Refresh tree
        else:
            QMessageBox.warning(self, self.tr("Warning"), self.tr(f"Shortcut for key '{key_name_normalized}' already exists in this group."))

    def _edit_selected_shortcut_item(self) -> None:
        """Allows editing the selected shortcut's key or description, or modifier group name."""
        selected_item = self._shortcut_tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No item selected to edit."))
            return

        current_app_item = self._app_list_widget.currentItem()
        if not current_app_item: return
        app_name = current_app_item.text()

        if selected_item.parent() is None: # It's a modifier group
            old_modifier_combo = selected_item.text(0)
            new_modifier_combo, ok = QInputDialog.getText(self, self.tr("Edit Modifier Group"),
                                                         self.tr("Modifier group name:"), QLineEdit.Normal, old_modifier_combo)
            if ok and new_modifier_combo and new_modifier_combo != old_modifier_combo:
                if new_modifier_combo not in self._current_shortcuts[app_name]:
                    self._current_shortcuts[app_name][new_modifier_combo] = self._current_shortcuts[app_name].pop(old_modifier_combo)
                    self._on_app_selected(current_app_item, None)
                else:
                    QMessageBox.warning(self, self.tr("Warning"), self.tr("Another modifier group with this name already exists."))
        else: # It's a shortcut (key-description pair)
            modifier_item = selected_item.parent()
            modifier_combo = modifier_item.text(0)
            old_key = selected_item.text(0)
            current_desc_obj = self._current_shortcuts[app_name][modifier_combo][old_key]
            
            old_desc_en = current_desc_obj.get("en", "") if isinstance(current_desc_obj, dict) else str(current_desc_obj)
            old_desc_zh = current_desc_obj.get("zh", "") if isinstance(current_desc_obj, dict) else ""

            # For simplicity, using QInputDialog. Could create a custom dialog for better editing experience.
            new_key, ok_key = QInputDialog.getText(self, self.tr("Edit Shortcut Key"), self.tr("Key:"), QLineEdit.Normal, old_key)
            if not (ok_key and new_key): return

            new_desc_en, ok_desc_en = QInputDialog.getText(self, self.tr("Edit Description (English)"), self.tr("English:"), QLineEdit.Normal, old_desc_en)
            if not ok_desc_en: return # User cancelled

            new_desc_zh, _ = QInputDialog.getText(self, self.tr("Edit Description (Chinese)"), self.tr("Chinese (optional):"), QLineEdit.Normal, old_desc_zh)

            updated_desc_obj: Dict[str, str] = {"en": new_desc_en}
            if new_desc_zh:
                updated_desc_obj["zh"] = new_desc_zh
            
            # Normalize new_key
            new_key_normalized = new_key.upper() if len(new_key) == 1 and new_key.isalpha() else new_key

            # Remove old key if key name changed, then add new/updated
            if new_key_normalized != old_key:
                if new_key_normalized in self._current_shortcuts[app_name][modifier_combo]:
                    QMessageBox.warning(self, self.tr("Warning"), self.tr(f"Another shortcut for key '{new_key_normalized}' already exists."))
                    return
                del self._current_shortcuts[app_name][modifier_combo][old_key]
            
            self._current_shortcuts[app_name][modifier_combo][new_key_normalized] = updated_desc_obj
            self._on_app_selected(current_app_item, None)


    def _remove_selected_item(self) -> None:
        """Removes the selected modifier group or shortcut from the tree and data."""
        selected_item = self._shortcut_tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No item selected to remove."))
            return

        current_app_item = self._app_list_widget.currentItem()
        if not current_app_item: 
            return
        app_name = current_app_item.text()

        confirm_msg = ""
        if selected_item.parent() is None:  # Modifier group
            modifier_combo = selected_item.text(0)
            template = self.tr("Are you sure you want to remove the modifier group '{modifier_combo}' and all its shortcuts?")
            confirm_msg = template.format(modifier_combo=modifier_combo)
        else:  # Shortcut
            modifier_combo = selected_item.parent().text(0)
            key = selected_item.text(0)
            template = self.tr("Are you sure you want to remove the shortcut '{modifier_combo} + {key}'?")
            confirm_msg = template.format(modifier_combo=modifier_combo, key=key)
        
        reply = QMessageBox.question(self, self.tr("Confirm Removal"), confirm_msg)
        if reply == QMessageBox.Yes:
            if selected_item.parent() is None:
                del self._current_shortcuts[app_name][selected_item.text(0)]
            else:
                del self._current_shortcuts[app_name][selected_item.parent().text(0)][selected_item.text(0)]
            self._on_app_selected(current_app_item, None)  # Refresh tree


    def _import_shortcuts(self) -> None:
        """Allows importing shortcuts from a JSON file, merging with or replacing existing ones."""
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Import Shortcuts JSON"), "", self.tr("JSON Files (*.json)"))
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
            if not isinstance(imported_data, dict):
                raise ValueError(self.tr("Imported file is not a valid shortcut JSON object."))

            # Ask user how to merge: Overwrite all, Merge (app-level), Merge (shortcut-level)
            # For simplicity here, let's do a simple merge: update existing apps, add new ones.
            # More sophisticated merging might be needed for conflicts.
            
            # Example: Simple merge - imported data overwrites existing keys at the app level.
            # For a safer merge, you might iterate and merge deeper.
            for app_name, app_shortcuts in imported_data.items():
                app_name_upper = app_name.upper() # Normalize app name from imported file
                if app_name_upper not in self._current_shortcuts:
                    self._current_shortcuts[app_name_upper] = {}
                # This is a deep update for the app's shortcuts
                self._deep_update(self._current_shortcuts[app_name_upper], app_shortcuts)


            self._populate_app_list() # Refresh UI
            QMessageBox.information(self, self.tr("Import Successful"), self.tr("Shortcuts imported successfully."))

        except Exception as e:
            QMessageBox.critical(self, self.tr("Import Error"), self.tr(f"Failed to import shortcuts: {e}"))

    def _deep_update(self, target_dict: Dict, source_dict: Dict) -> None:
        """Recursively updates a target dictionary with items from a source dictionary."""
        for key, value in source_dict.items():
            if isinstance(value, dict) and key in target_dict and isinstance(target_dict[key], dict):
                self._deep_update(target_dict[key], value)
            else:
                target_dict[key] = value

    def _save_and_accept(self) -> None:
        """Saves the current state of shortcuts to the config file and closes the dialog."""
        try:
            # Overwrite the entire shortcuts_data in ConfigManager
            self.config_manager.shortcuts_data = self._current_shortcuts.copy() # Ensure it's a copy
            self.config_manager.save_shortcuts() # Create this method in ConfigManager
            QMessageBox.information(self, self.tr("Save Successful"), self.tr("Shortcuts saved successfully."))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Save Error"), self.tr(f"Failed to save shortcuts: {e}"))

    # You need to add `save_shortcuts` to ConfigManager
    # class ConfigManager:
    #     ...
    #     def save_shortcuts(self) -> None:
    #         """Saves the current shortcut_data to the shortcuts_file_path."""
    #         try:
    #             os.makedirs(os.path.dirname(self._shortcuts_file_path), exist_ok=True)
    #             with open(self._shortcuts_file_path, "w", encoding="utf-8") as f:
    #                 json.dump(self.shortcuts_data, f, indent=2, ensure_ascii=False)
    #             print(f"Info: Shortcuts saved to '{self._shortcuts_file_path}'.")
    #         except Exception as e:
    #             print(f"Error: Could not save shortcuts to '{self._shortcuts_file_path}': {e}")
    #             raise # Re-raise so the dialog can catch it

    def reject(self) -> None:
        # Ask for confirmation if changes were made (self._current_shortcuts vs original)
        # For simplicity, just reject.
        # If you want to check for unsaved changes:
        # original_shortcuts_on_open = self.config_manager.get_all_shortcuts()
        # if self._current_shortcuts != original_shortcuts_on_open:
        #     reply = QMessageBox.question(self, "Unsaved Changes", "You have unsaved changes. Close anyway?")
        #     if reply == QMessageBox.No:
        #         return
        super().reject()