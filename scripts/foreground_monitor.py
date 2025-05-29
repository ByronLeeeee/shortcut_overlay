# shortcut_overlay/foreground_monitor.py
"""
Monitors the active foreground window on Windows to detect application changes.

This module periodically checks which window is in the foreground,
determines the executable name of the associated process, and emits a signal
when the active application changes. This allows the overlay to display
application-specific shortcuts. This module is Windows-specific due to its
reliance on `pywin32` for interacting with the Windows API.
"""
import win32gui  # For GetForegroundWindow
import win32process  # For GetWindowThreadProcessId, GetModuleFileNameEx
import win32api  # For OpenProcess, CloseHandle
import win32con  # For process access constants (e.g., PROCESS_QUERY_LIMITED_INFORMATION)
import os
from PySide6.QtCore import QObject, Signal, QTimer
from typing import Optional

# Type alias for Windows HWND (Handle to Window).
HWND = int
# Type alias for Windows HPROCESS (Handle to Process).
HPROCESS = int


class ForegroundMonitor(QObject):
    """
    Monitors the currently active foreground application on Windows.

    It periodically checks the foreground window, identifies the associated
    executable, and emits an `active_app_changed` signal when the focused
    application changes. This signal carries the executable name (e.g., "NOTEPAD.EXE")
    or "DEFAULT" if the application cannot be identified.
    """

    # Signal emitted when the active foreground application changes.
    # Argument: str - The executable name (e.g., "NOTEPAD.EXE") or "DEFAULT".
    active_app_changed = Signal(str)

    # Default interval in milliseconds for polling the foreground application.
    DEFAULT_POLL_INTERVAL_MS: int = 1000

    def __init__(
        self,
        parent: Optional[QObject] = None,
        interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
    ):
        """
        Initializes the ForegroundMonitor.

        Sets up a timer to periodically call `check_foreground_app`.

        Args:
            parent: The parent QObject, if any.
            interval_ms: The interval in milliseconds at which to check
                         the foreground application. Defaults to `DEFAULT_POLL_INTERVAL_MS`.
        """
        super().__init__(parent)
        self.current_app_name: Optional[str] = (
            None  # Stores the name of the currently focused app.
        )
        self._timer: QTimer = QTimer(self)  # Timer for periodic checks.
        self._timer.timeout.connect(self.check_foreground_app)
        self._timer.start(interval_ms)
        # An initial check can be deferred to allow the main application to complete its setup,
        # or called here if immediate detection is preferred.
        # self.check_foreground_app()

    def get_exe_from_hwnd(self, hwnd: HWND) -> Optional[str]:
        """
        Retrieves the base executable name (e.g., "explorer.exe") from a
        given window handle (HWND).

        This function interacts directly with the Windows API. It attempts to
        open the process associated with the window and query its module file name.
        Handles potential errors such as access denied or invalid handles.

        Args:
            hwnd: The handle of the window to get the executable name for.

        Returns:
            The base name of the executable file as a string,
            or None if the executable name cannot be determined.
        """
        try:
            if not hwnd:  # No valid window handle.
                return None

            # Get the process ID (PID) associated with the window handle.
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == 0:  # Should generally not happen for valid foreground windows.
                return None

            process_handle: Optional[HPROCESS] = None
            # Attempt to open the process with limited information query rights first.
            # This is preferred for security as it requires fewer privileges.
            try:
                process_handle = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                )
            except win32api.error:
                # If limited information query fails (e.g., access denied),
                # fallback to broader permissions. This is less common to be the
                # sole cause of failure than overall permission issues.
                pass  # Fallthrough to the next try block.

            if not process_handle:
                # Fallback to broader query rights if the limited query failed.
                # This might be necessary for some system processes or older Windows versions.
                try:
                    process_handle = win32api.OpenProcess(
                        win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                        False,
                        pid,
                    )
                except win32api.error:
                    # If opening with broader permissions also fails, cannot proceed.
                    # print(f"Debug: OpenProcess with broader permissions also failed for PID {pid}: {e}")
                    return None

            if not process_handle:  # Still no valid process handle.
                return None

            try:
                # Retrieve the full path of the executable module for the process.
                app_path: str = win32process.GetModuleFileNameEx(process_handle, 0)
            except win32api.error:
                # Failed to get module name (e.g., access denied, process terminated).
                # print(f"Debug: GetModuleFileNameEx failed for PID {pid}, Handle {process_handle}: {e}")
                return None
            finally:
                # Always ensure the process handle is closed.
                win32api.CloseHandle(process_handle)

            # Return only the base name of the executable (e.g., "notepad.exe").
            return os.path.basename(app_path)

        except Exception as e:
            # Catch any other unexpected OS or win32api errors during the process.
            print(f"Unexpected error in get_exe_from_hwnd for HWND {hwnd}: {e}")
            return None

    def check_foreground_app(self) -> None:
        """
        Periodically called by the internal QTimer.
        Checks the current foreground window, determines its application name,
        and emits the `active_app_changed` signal if the application has changed
        since the last check. If the application cannot be identified (e.g.,
        desktop, some system UI elements), it emits "DEFAULT".
        """
        try:
            current_hwnd: HWND = win32gui.GetForegroundWindow()
            new_app_name: Optional[str] = self.get_exe_from_hwnd(current_hwnd)
            # print(f"Debug: [FG_MONITOR] Detected app: {new_app_name}, Previously: {self.current_app_name}")

            if new_app_name and new_app_name != self.current_app_name:
                # A new, identifiable application has come to the foreground.
                self.current_app_name = new_app_name
                self.active_app_changed.emit(self.current_app_name)
            elif not new_app_name and self.current_app_name is not None:
                # Foreground is now an unidentifiable app/window or an error occurred.
                # Reset to "DEFAULT" state to show default shortcuts.
                self.current_app_name = (
                    None  # Represent "DEFAULT" or unidentifiable state.
                )
                self.active_app_changed.emit("DEFAULT")
            # No signal is emitted if:
            # - app_name is None and current_app_name was already None (no change from "DEFAULT").
            # - app_name is the same as current_app_name (no change in focused app).

        except Exception as e:
            # Broad exception to catch errors from GetForegroundWindow or other logic within this method.
            print(f"Error during foreground app check: {e}")
            # If an error occurs and an app was previously identified,
            # it's safer to revert to "DEFAULT" to prevent a stale overlay state.
            if self.current_app_name is not None:
                self.current_app_name = None
                self.active_app_changed.emit("DEFAULT")

    def stop_monitoring(self) -> None:
        """
        Stops the foreground application monitoring timer.
        This should be called when the application is shutting down to clean up resources.
        """
        if self._timer.isActive():
            self._timer.stop()
            print("Foreground monitor stopped.")  # Console message for status.
