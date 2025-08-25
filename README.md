# Joy2Win - XInput Support
This project adds a XInput support to Joy2Win project made by Logan Gaillard and others (Both Joy-Cons only).
By default it uses N's buttons layout - but you can customize it via config.ini! 

For more information about original project please visit: https://github.com/Logan-Gaillard/Joy2Win.

## Installation

1. Clone this repository :
   ```bash
   git clone https://github.com/IvanSereginGitHub/Joy2WinXInput.git
   cd Joy2Win
   ```

2. Install Python dependencies :
    ```
    pip install bleak pyvjoy pynput vgamepad
    ```

4.  Install vJoy :
    https://sourceforge.net/projects/vjoystick/

5. Configure vJoy :  
        - Open "Configure vJoy"  
        - Select controller n°1  
        - Set 24 buttons or higher  
        - Restart your computer  

6. Copy the `config-exemple.ini` file, rename it to `config.ini`, and edit it according to your needs.

7. Run the script :
    ```bash
    python main.py
    ```

8. Follow the instructions displayed when the script starts.