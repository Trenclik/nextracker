import os
import configparser
from os.path import join, dirname
from dotenv import load_dotenv

# define paths
dotenv_path = join(dirname(__file__), '.env')
conf_path = join(dirname(__file__), 'nextracker.conf')

# select only enabled settings
config = configparser.ConfigParser()
config.read(conf_path)

enabled_settings :dict[str,list[str]] = {}

for section in config.sections():
    try:
        enabled_settings[section] = [
            key for key in config[section] 
            if config.getboolean(section, key)
        ]
    except (ValueError, configparser.Error) as e:
        print(f"Warning: Error processing section '{section}': {str(e)}")
        continue

enabled_settings = {
    section: keys for section, keys in enabled_settings.items() 
    if keys
}

# dotenv shenanigans
load_dotenv(dotenv_path)
NC_INSTANCE :str = str(os.environ.get("NC_INSTANCE"))
NC_PASS :str = str(os.environ.get("NC_PASS"))
NC_USER :str = str(os.environ.get("NC_USER"))
