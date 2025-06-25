import requests
import settings

class DataHandler():
    def __init__(self) -> None:
        self.parsed_data:dict[str,list[str]] = {}
        self.request = 
    def pull_metrics(self):
        request = requests.get(
                    settings.NC_INSTANCE,
                    headers={"OCS-APIRequest": "true"},
                    auth=(settings.NC_USER,settings.NC_PASS)
                    )
        return request.content
    def select_data(self):
        if 'status' in settings.enabled_settings:
            self.parsed_data["status"] = []
            if 'status' in settings.enabled_settings['status']:
                
            pass
        elif 'nextcloud_info' in settings.enabled_settings:
            pass
        elif 'system_info' in settings.enabled_settings:
            pass
        elif 'database' in settings.enabled_settings:
            pass
        elif 'php' in settings.enabled_settings:
            pass
hand = DataHandler()
hand.select_data()
print(hand.parsed_data)