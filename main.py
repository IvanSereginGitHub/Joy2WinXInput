import asyncio, os
from bleak import BleakClient, BleakScanner
from config import Config
from controller_command import ControllerCommand, UUID_NOTIFY, UUID_CMD_RESPONSE
from dsu_server import main_dsu

# Check if the operating system is Windows
if(os.name != 'nt'):
    print("This application is only supported on Windows.")
    exit(1)

# Read the configuration from config.ini
config = Config().getConfig()

manufact = {
    "id": 0x0553,  # Nintendo Co., Ltd. (https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
    "data-prefix": bytes([0x01, 0x00, 0x03, 0x7e, 0x05])  # Manufacturer data prefix for Joy-Con (I hope this prefix is correct, and it same for everyone)
}

clients = []  # List to hold connected clients

# Function to scan for controllers
async def scan_joycons():
    device_controller = None

    def callback(device, advertisement_data):
        nonlocal device_controller
        data = advertisement_data.manufacturer_data.get(manufact["id"])
        if not data:
            return

        if data.startswith(manufact["data-prefix"]):
            if not device_controller:
                print(f"Controller with address: {device.address} found.")
                device_controller = device

    scanner = BleakScanner(callback)
    await scanner.start()

    while True:
        if device_controller:
            break
        await asyncio.sleep(0.5)
    await scanner.stop()

    return device_controller

# Connect the controller and attribute to a notification handler
async def connect(device_controller):
    client = BleakClient(device_controller)
    try:
        await client.connect()
        if client.is_connected:
            return client
        else:
            print("Failed to connect.")
            return None
    except Exception as e:
        print(f"Failed to connect to {device_controller}: {e}")
        return None


async def init_controller(name, side, orientation, controller=0, enable_xinput=0):
    print(f"Scanning for {name} {side}, press the sync button...")
    device = await scan_joycons()

    if device:
        client = await connect(device)
        if client is not None:
            clients.append(client)

            print(f"{name} {side} connected successfully.")

            if controller == 0:
                if enable_xinput == 1:
                    # Notify controller to handle both Joy-Cons, because the controller is connected
                    await handle_duo_joycons_xinput(client, side)
                else:
                    # Notify controller to handle both Joy-Cons, because the controller is connected
                    await handle_duo_joycons(client, side)

            elif controller == 1:
                await handle_single_joycon(client, side, orientation)

            elif controller == 2:
                await handle_single_joycon(client, side, orientation)

        else:
            print(f"Failed to connect {name} {side}.")
    else:
        print(f"Joy-Con {name} {side} not found.")

async def handle_duo_joycons_xinput(client, side):
    from control_type.duo_joycon_xinput import notify_duo_joycons

    async def notification_handler(sender, data): #Notification des données du controller
        asyncio.create_task(notify_duo_joycons(client, side, data))

    def response_handler(sender, data): #Notification des réponses aux commandes du controller
        ControllerCommand().receive_response(client, data)

    await client.start_notify(UUID_CMD_RESPONSE, response_handler) #Commencer à écouter les réponses aux commandes

    await initSendControllerCmd(client, "Joy-Con") #Envoie des commandes d'initialisation au controller

    await client.stop_notify(UUID_CMD_RESPONSE) # Nous avons plus besoin d'écouter les réponses aux commandes
    await client.start_notify(UUID_NOTIFY, notification_handler) # Commencer à écouter les notifications des données du controller

async def handle_duo_joycons(client, side):
    from control_type.duo_joycon import notify_duo_joycons

    async def notification_handler(sender, data): #Notification des données du controller
        asyncio.create_task(notify_duo_joycons(client, side, data))

    def response_handler(sender, data): #Notification des réponses aux commandes du controller
        ControllerCommand().receive_response(client, data)

    await client.start_notify(UUID_CMD_RESPONSE, response_handler) #Commencer à écouter les réponses aux commandes

    await initSendControllerCmd(client, "Joy-Con") #Envoie des commandes d'initialisation au controller

    await client.stop_notify(UUID_CMD_RESPONSE) # Nous avons plus besoin d'écouter les réponses aux commandes
    await client.start_notify(UUID_NOTIFY, notification_handler) # Commencer à écouter les notifications des données du controller

# Se référé aux commentaire qui sont dans la fonction au dessus (handle_duo_joycons)
async def handle_single_joycon(client, side, orientation):
    from control_type.single_joycon import notify_single_joycons

    async def notification_handler(sender, data):
        asyncio.create_task(notify_single_joycons(client, side, orientation, data))

    def response_handler(sender, data):
        ControllerCommand().receive_response(client, data)

    await client.start_notify(UUID_CMD_RESPONSE, response_handler)

    await initSendControllerCmd(client, "Joy-Con")

    await client.stop_notify(UUID_CMD_RESPONSE)
    await client.start_notify(UUID_NOTIFY, notification_handler)


async def initSendControllerCmd(client, controllerName):
    controllerCommand = ControllerCommand()
    if(controllerName == "Joy-Con"):
        
        if(config['save_mac_address'] == True):
            mac_address = config['mac_address']

            mac_addr1 = mac_address
            mac_addr2 = (mac_address[0] - 1).to_bytes(1, 'big') + mac_address[1:]

            await controllerCommand.send_command(client, "JOY2_SAVE_MC_ADDR_STEP1", {"mac-addr1": mac_addr1.hex(), "mac-addr2": mac_addr2.hex()})
            await controllerCommand.send_command(client, "JOY2_SAVE_MC_ADDR_STEP2")
            await controllerCommand.send_command(client, "JOY2_SAVE_MC_ADDR_STEP3")
            await controllerCommand.send_command(client, "JOY2_SAVE_MC_ADDR_STEP4")

            print(f"MAC address {mac_addr1.hex()} + {mac_addr2.hex()} saved successfully.")


        await controllerCommand.send_command(client, "JOY2_CONNECTED_VIBRATION")
        # Convert binary string (e.g., "0101") to hexadecimal string (e.g., "5")

        if len(config['led_player']) != 4 or not all(c in '01' for c in config['led_player']): #Length is 4 and only contains '0' and '1'
            print("LED player incorrectly set in config.ini, defaulting to 0001.")
            config['led_player'] = "0001"

        await controllerCommand.send_command(client, "JOY2_SET_PLAYER_LED", {"led_player": format(int(config['led_player'], 2), 'x')}) # Convert binary string to hex string
        await controllerCommand.send_command(client, "JOY2_INIT_SENSOR_DATA")
        await controllerCommand.send_command(client, "JOY2_START_SENSOR_DATA")


async def main():
    try:
        if(not config['orientation'] == 0 and not config['orientation'] == 1):
            print("Invalid orientation in config.ini. Please set 'orientation' to 0 (Vertical) or 1 (Horizontal).\nDefaulting to vertical.")
            config['orientation'] = 0  # Default to vertical if invalid

        if config['controller'] == 0:
            if config['enable_xinput'] == 1:
                print("XInput enabled")
            await init_controller("Joy-Con", "Left", config['orientation'], 0, config['enable_xinput'])
            await init_controller("Joy-Con", "Right", config['orientation'], 0, config['enable_xinput'])
        elif config['controller'] == 1:
            await init_controller("Joy-Con", "Left", config['orientation'], 1)
        elif config['controller'] == 2:
            await init_controller("Joy-Con", "Right", config['orientation'], 2)
        else:
            print("Invalid controller in config.ini. Please set 'controller' to 0, 1, or 2.\nDefaulting to both Joy-Cons.")
            await init_controller("Joy-Con", "Left", config['orientation'], 0)
            await init_controller("Joy-Con", "Right", config['orientation'], 0)

        if config['enable_dsu'] == True :
            main_dsu()

        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Interrupting...")

    finally:
        print("Disconnecting controllers...")
        for client in clients:
            await client.disconnect()
        print("All controllers disconnected.")


#Used to get the manufacturer data from joycons
#async def scan_all():
    #devices = await BleakScanner.discover()
    #for d in devices:
    #    md = d.metadata.get("manufacturer_data", {})
    #    if md:
    #        for manu_id, data_bytes in md.items():
    #            print(f"Device: {d.name}, ID: {manu_id}, Data: {data_bytes.hex()}")


if __name__ == "__main__":
    asyncio.run(main())