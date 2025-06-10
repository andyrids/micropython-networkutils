import time
from ast import literal_eval

from mpremote.commands import CommandError
from mpremote.transport import TransportError, TransportExecError
from mpremote.main import State
from mpremote import mip
from mpremote.transport_serial import SerialTransport
from rich.console import Console
from serial.tools import list_ports


_console = Console()

if __name__ == "__main__":
    # VID: 2e8a PID: 0005
    #print(*map(str, (p.device for p in list_ports.comports())))

    try: 
        # auto-detect & auto-connect to the first available USB serial port
        for p in sorted(list_ports.comports()):
            if p.vid and p.pid:
                try:
                    serial_transport = SerialTransport(p.device, 115200)
                except TransportError as e:
                    e.add_note("No devices found.")
                    _console.print_exception()
                else:
                    break
        if serial_transport.in_raw_repl:
            serial_transport.exit_raw_repl()

        serial_transport.enter_raw_repl(soft_reset=False)
        time.sleep(1)

        _console.print(f"IN REPL: {serial_transport.in_raw_repl}")

        # test package installation
        try:
            mip._install_package(
                serial_transport,
                "github:andyrids/micropython-network-utils/network-utils/",
                "https://micropython.org/pi/v2",
                "lib",
                "main",
                True
            )
        except CommandError as e:
            e.add_note("network-utils installation failed")
            _console.print_exception()

        # `/lib` should contain `network_utils` dir & other dependencies
        out = serial_transport.fs_listdir("lib")
        _console.print("DEVICE DIR:", ",".join(i.name for i in out))

        out = serial_transport.exec("import sys; print(sys.implementation.name)")
        _console.print(out.decode().strip())

        out = serial_transport.exec("import network_utils")

        out = serial_transport.exec("print(network_utils._DEVICE_ID)")
        _console.print(out.decode().strip())

        exp = (
            'env = network_utils.NetworkEnv();'
            'env.putenv("WLAN_SSID", "TEST_SSID");'
            'env.putenv("WLAN_PASSWORD", "TEST_PASSWORD");'
        )

        serial_transport.exec(exp)

        out = serial_transport.exec("print(env.getenv('WLAN_SSID'))")
        _console.print(out.decode().strip())

        out = serial_transport.exec("print(env.getenv('WLAN_PASSWORD'))")
        _console.print(out.decode().strip())


    except (Exception, TransportExecError) as e:
        _console.print_exception()
    finally:
        if serial_transport.in_raw_repl:
            serial_transport.exit_raw_repl()
        serial_transport.close()