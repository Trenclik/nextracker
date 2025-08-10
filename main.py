import requests
import settings
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont


class MonitorWorker(QObject):
    """
    Worker class that runs in a separate thread to handle monitoring tasks
    """
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    update_started = pyqtSignal()  # New signal to indicate update started

    def __init__(self, instance, user, passw):
        super().__init__()
        self.instance = instance
        self.user = user
        self.passw = passw
        self.running = True
        
        # Map config sections/keys to JSON paths
        self.response_map: Dict[str, Dict[str, Tuple[str, ...]]] = {
            'status': {
                'status': ('ocs', 'meta', 'status'),
                'message': ('ocs', 'meta', 'message'),
                'status_code': ('ocs', 'meta', 'statuscode')
            },
            'nextcloud_info': {
                'version': ('ocs', 'data', 'nextcloud', 'system', 'version'),
                'free_space': ('ocs', 'data', 'nextcloud', 'system', 'freespace'),
                'users': ('ocs', 'data', 'activeUsers', 'last5minutes')
            },
            'system_info': {
                'cpu_load': ('ocs', 'data', 'nextcloud', 'system', 'cpuload'),
                'total_memory': ('ocs', 'data', 'nextcloud', 'system', 'mem_total'),
                'free_memory': ('ocs', 'data', 'nextcloud', 'system', 'mem_free'),
                'total_swap': ('ocs', 'data', 'nextcloud', 'system', 'swap_total'),
                'free_swap': ('ocs', 'data', 'nextcloud', 'system', 'swap_free')
            },
            'database': {
                'type': ('ocs', 'data', 'server', 'database', 'type'),
                'version': ('ocs', 'data', 'server', 'database', 'version'),
                'size': ('ocs', 'data', 'server', 'database', 'size')
            },
            'php': {
                'webserver': ('ocs', 'data', 'server', 'webserver'),
                'version': ('ocs', 'data', 'server', 'php', 'version'),
                'opcache': ('ocs', 'data', 'server', 'php', 'opcache'),
                'extensions': ('ocs', 'data', 'server', 'php', 'extensions')
            }
        }

    def pull_metrics(self) -> None:
        """Pull metrics from Nextcloud instance in a thread-safe way"""
        self.update_started.emit()  # Notify UI that update has started
        try:
            request = requests.get(
                self.instance,
                headers={"OCS-APIRequest": "true"},
                auth=(self.user, self.passw),
                timeout=10  # Add timeout to prevent hanging
            ).json()
            selected_data = self.select_data(request)
            self.data_ready.emit(selected_data)
        except requests.exceptions.JSONDecodeError:
            try:
                request = requests.get(settings.NC_ROOT, timeout=10).json()
                selected_data = self.select_data(request)
                self.data_ready.emit(selected_data)
            except Exception as err:
                self.error_occurred.emit(f"JSON Decode Error: {err}")
        except Exception as err:
            self.error_occurred.emit(f"Request Error: {err}")

    def select_data(self, request_data: dict) -> Dict[str, Dict[str, Any]]:
        """Process the request data and select relevant information"""
        selected_data: Dict[str, Dict[str, Any]] = {}
        
        for section, keys in settings.enabled_settings.items():
            selected_data[section] = {}
            for key in keys:
                # Get the path from our mapping
                path = self.response_map[section][key]
                
                # Navigate through the response
                value = request_data
                try:
                    for step in path:
                        value = value[step]
                    selected_data[section][key] = value
                except (KeyError, TypeError):
                    selected_data[section][key] = None
        return selected_data


class NextcloudMonitor(QObject):
    """
    Main monitor class that manages worker threads
    """
    def __init__(self, instance, user, passw):
        super().__init__()
        self.instance = instance
        self.user = user
        self.passw = passw
        
        # Create worker and thread
        self.worker = MonitorWorker(instance, user, passw)
        self.thread = QThread()
        
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.pull_metrics)
        
        # Start the thread
        self.thread.start()

    def refresh(self):
        """Trigger a refresh of the data"""
        if self.thread.isRunning():
            # Use QTimer.singleShot to ensure this runs in the worker's thread
            QTimer.singleShot(0, self.worker.pull_metrics)

    def stop(self):
        """Clean up threads"""
        self.thread.quit()
        self.thread.wait()


class StatusWindow(QMainWindow):
    def __init__(self, monitor: NextcloudMonitor) -> None:
        super().__init__()
        self.monitor = monitor
        self.setWindowTitle("Nextracker")
        self.setGeometry(100, 100, 400, 300)  # Slightly larger window

        # Widgets
        self.status_label = QLabel("Status: Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setFont(QFont("Monospace", 10))  # Monospaced font for better formatting
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_status)
        
        # Add a status bar message
        self.statusBar().showMessage("Ready")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.refresh_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Auto-refresh every 15 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(15000)

        # Connect monitor signals
        self.monitor.worker.data_ready.connect(self.update_status_display)
        self.monitor.worker.error_occurred.connect(self.show_error)

    def show_loading(self):
        """Show loading state while data is being fetched"""
        self.statusBar().showMessage("Fetching data...")
        self.refresh_button.setEnabled(False)  # Disable button during refresh

    def format_status_data(self, status_data: Union[Dict[str, Any], List[Any], str], indent: int = 0) -> str:
        """Recursively format status data into a readable string."""
        lines: List[str] = []
        indent_str = " " * indent
        
        if isinstance(status_data, dict):
            for key, value in status_data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent_str}{key}:")
                    lines.append(self.format_status_data(value, indent + 2))
                else:
                    lines.append(f"{indent_str}{key}: {value}")
        elif isinstance(status_data, list):
            for i, item in enumerate(status_data):
                lines.append(f"{indent_str}[{i}]:")
                lines.append(self.format_status_data(item, indent + 2))
        else:
            lines.append(f"{indent_str}{status_data}")
        
        return "\n".join(lines)
    
    def update_status(self) -> None:
        """Trigger a status update in the monitor thread"""
        self.show_loading()
        self.timer.stop()
        self.timer.start(15000)
        self.monitor.refresh()

    def update_status_display(self, status: dict) -> None:
        """Update the GUI with the latest status (called from worker thread)"""
        if "error" in status:
            self.status_label.setText(f"Error: {status['error']}")
        else:
            formatted_status = self.format_status_data(status)
            self.status_label.setText(formatted_status)
        
        self.statusBar().showMessage("")
        self.refresh_button.setEnabled(True)  # Re-enable button after refresh

    def show_error(self, error: str) -> None:
        """Display error messages in the GUI"""
        self.status_label.setText(f"Error: {error}")
        self.statusBar().showMessage("Error occurred")
        self.refresh_button.setEnabled(True)  # Re-enable button on error

    def closeEvent(self, event):
        """Clean up threads when window closes"""
        self.monitor.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    instances = settings.NC_INSTANCE.split()
    users = settings.NC_USER.split()
    passes = settings.NC_PASS.split()

    monitor = NextcloudMonitor(instances[0], users[0], passes[0])
    
    # Initialize and show GUI
    window = StatusWindow(monitor)
    window.show()
    window.update_status()  # Initial update
    
    sys.exit(app.exec())