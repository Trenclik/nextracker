import requests
import settings
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
)
from PyQt6.QtCore import QTimer

class NextcloudMonitor():
    def __init__(self) -> None:
        self.parsed_data: Dict[str, Any] = {}
        self.request: Optional[Dict[str, Any]] = None
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
                'used_memory': ('ocs', 'data', 'nextcloud', 'system', 'mem_free'),  # Note: This is actually free memory in the response
                'free_memory': ('ocs', 'data', 'nextcloud', 'system', 'mem_free'),
                'total_swap': ('ocs', 'data', 'nextcloud', 'system', 'swap_total'),
                'used_swap': ('ocs', 'data', 'nextcloud', 'system', 'swap_total'),  # Note: Response doesn't have used_swap directly
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
        self.request = requests.get(
            settings.NC_INSTANCE,
            headers={"OCS-APIRequest": "true"},
            auth=(settings.NC_USER, settings.NC_PASS)
        ).json()
        return

    def select_data(self) -> Dict[str, Dict[str, Any]]:
        selected_data: Dict[str, Dict[str, Any]] = {}
        
        for section, keys in settings.enabled_settings.items():
            selected_data[section] = {}
            for key in keys:
                # Get the path from our mapping
                path = self.response_map[section][key]
                
                # Navigate through the response
                value = self.request
                try:
                    for step in path:
                        value = value[step]
                    selected_data[section][key] = value
                except (KeyError, TypeError):
                    selected_data[section][key] = None  # or "N/A" if you prefer
        print(selected_data)
        return selected_data
class SettingsPanel():
    def __init__(self) -> None:
        
        pass
class StatusWindow(QMainWindow):
    def __init__(self, monitor: NextcloudMonitor) -> None:
        super().__init__()
        self.monitor = monitor
        self.setWindowTitle("Nextracker")
        self.setGeometry(100, 100, 300, 200)

        # Widgets
        self.status_label = QLabel("Status: Unknown")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_status)

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
        """Updates the GUI with the latest status."""
        self.monitor.pull_metrics()
        status = self.monitor.select_data()
        if "error" in status:
            self.status_label.setText(f"Error: {status['error']}")
        else:
            formatted_status = self.format_status_data(status)
            self.status_label.setText(formatted_status)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    monitor = NextcloudMonitor()
    
    # Initialize and show GUI
    window = StatusWindow(monitor)
    window.show()
    window.update_status()
    
    sys.exit(app.exec())