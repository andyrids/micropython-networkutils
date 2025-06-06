import time

from mpremote import transport_serial
from rich.console import Console
from serial.tools import list_ports


_console = Console()

if __name__ == "__main__":
    # VID: 2e8a PID: 0005
    #print(*map(str, (p.device for p in list_ports.comports())))

    try:
        for com in list_ports.comports():
            _console.print(com.device)
            serial_transport = transport_serial.SerialTransport(com.device)
            time.sleep(1)

            # write a ctl+c
            serial_transport.serial.write(b"\x03")

            serial_transport.enter_raw_repl(soft_reset=False)
            time.sleep(1)
            _console.print(serial_transport.in_raw_repl)

            # write a ctl+c
            #serial_transport.serial.write(b"\x03")


            out = serial_transport.exec("import sys; print(sys.implementation.name)")
            _console.print(out.decode().strip())

            # out = serial_transport.exec_raw("import sys; print(sys.implimentation.name)")
            # _console.print(*(i.decode() for i in out))
            out = serial_transport.fs_listdir()
            _console.print(out)
            
            serial_transport.exit_raw_repl()
            serial_transport.close()
    except Exception as e:
        _console.print_exception()
        serial_transport.exit_raw_repl()
        serial_transport.close()