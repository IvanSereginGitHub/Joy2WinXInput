import configparser
import os
import json

class Config:
    _instance = None
    _defaults = {
        "controller": 0,
        "orientation": 0,
        "led_player": 0b0001,
        "save_mac_address": False,
        "enable_dsu": False,
        "mouse_mode": 0,
        "mac_address": "FFFFFFFFFFFF",
        "enable_xinput": 1,
        "joysticks_deadzone": 4000,
        "custom_controls_left": {},
        "custom_controls_right": {}
    }

    def __new__(cls, config_path="config.ini"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = config_path
            cls._instance._init_defaults()
            cls._instance.load_config()
        return cls._instance

    def _init_defaults(self):
        for key, value in self._defaults.items():
            setattr(self, key, value)

    def load_config(self):
        config_parser = configparser.ConfigParser()
        if not os.path.exists(self._config_path):
            print(f"{self._config_path} not found. Using default values.")
            return

        config_parser.read(self._config_path)
        if "Controller" in config_parser:
            section = config_parser["Controller"]
            self.controller = int(section.get("controller", self.controller))
            self.orientation = int(section.get("orientation", self.orientation))
            self.led_player = str(section.get("led_player", self.led_player))
            self.save_mac_address = section.get("save_mac_address", str(self.save_mac_address)).lower() == '1'
            self.enable_dsu = section.get("enable_dsu", str(self.enable_dsu)).lower() == '1'
            self.mouse_mode = int(section.get("mouse_mode", self.mouse_mode if self.mouse_mode == 0 or self.mouse_mode == 1 or self.mouse_mode == 2 else 0))
            self.enable_xinput = int(section.get("enable_xinput", self.enable_xinput))
            self.joysticks_deadzone = int(section.get("joysticks_deadzone", self.joysticks_deadzone))
            self.custom_controls_left = json.loads(section.get("custom_controls_left", self.custom_controls_left) or '{}')
            self.custom_controls_right = json.loads(section.get("custom_controls_right", self.custom_controls_right) or '{}')
            
            if "Bluetooth" in config_parser:
                section = config_parser["Bluetooth"]
                configMacAddress =  section.get("mac_address", self.mac_address)
                if(configMacAddress and len(configMacAddress) == 12 and all(c in "0123456789ABCDEF" for c in configMacAddress.upper())): # Valid MAC address format like AABBCCDDEEFF
                    self.mac_address = bytes.fromhex(configMacAddress)[::-1] # Convert mac to little-endian format
                else:
                    print(f"Invalid MAC address in {self._config_path}. Using default: {self.mac_address}")
                    self.mac_address = self._defaults["mac_address"]
            else:
                print(f"Section 'Bluetooth' not found in {self._config_path}. disabling save_mac_address.")
                self.save_mac_address = False
        else:
            print(f"Section 'Controller' not found in {self._config_path}. Using default values.")
            self._init_defaults()

    def getConfig(self):
        return {
            "controller": self.controller,
            "orientation": self.orientation,
            "led_player": self.led_player,
            "save_mac_address": self.save_mac_address,
            "enable_dsu": self.enable_dsu,
            "mouse_mode": self.mouse_mode,
            "mac_address": self.mac_address,
            "enable_xinput": self.enable_xinput,
            "joysticks_deadzone": self.joysticks_deadzone,
            "custom_controls_left": self.custom_controls_left,
            "custom_controls_right": self.custom_controls_right
        }