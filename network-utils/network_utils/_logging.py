import network
import sys


class Logger:
    """Logging messages class.
    
    Methods:
        enable: Enable logging messages.

        disable: Disable logging messages.

        debug_message: Print a debug message.

        debug_network_status: Print WLAN status debug messages.
    
    Properties:
        enabled: Enable messages flag.

        stream: Message stream - `sys.stdout`
    """
    def __init__(self) -> None:
        """Initialise Logger class."""
        self.enabled = False
        self.stream = sys.stdout


    def enable(self) -> None:
        """Enable logging messages."""
        self.enabled = True


    def disable(self) -> None:
        """Disable logging messages."""
        self.enabled = False


    def debug_message(self, message: str) -> None:
        """Print a debug message.

        Args:
            message (str): Message to print.
        """
        # `"{:^30}".format("CENTRED STRING")`
        if not self.enabled:
            return
        self.stream.write("\n".join([i.strip() for i in message.split("\n")]))


    def debug_network_status(self, WLAN: network.WLAN, mode: int) -> None:
        """Print WLAN status debug messages.

        Args:
            WLAN (network.WLAN): WLAN instance.

            mode (str): WLAN instance mode.
        """
        WLAN_MODE_STR = ("STA", "AP")[mode]
        status = WLAN.status()
        active = WLAN.active()
        connected = WLAN.isconnected()

        message = f"""
        WLAN INFO
        ---------
        MODE: {WLAN_MODE_STR}
        STATUS: {status}
        ACTIVE: {active}
        CONNECTED: {connected}
        """

        self.debug_message(message)
