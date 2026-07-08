"""Hardware adapters for ESC/POS printers (Network, USB, etc.)."""
import socket
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BasePrinterAdapter(ABC):
    """Abstract base class for all ESC/POS printer hardware interfaces."""
    
    @abstractmethod
    def print_bytes(self, payload: bytes) -> None:
        """Send byte payload to the physical printer.
        Raises IOError or ConnectionError on failure.
        """
        pass


class NetworkPrinterAdapter(BasePrinterAdapter):
    """Communicates with ESC/POS printers via TCP/IP."""
    
    def __init__(self, ip_address: str, port: int = 9100, timeout: float = 3.0):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout

    def print_bytes(self, payload: bytes) -> None:
        if not self.ip_address:
            raise ConnectionError("Network printer missing IP address.")
            
        try:
            with socket.create_connection((self.ip_address, self.port), timeout=self.timeout) as s:
                s.sendall(payload)
        except (socket.timeout, ConnectionRefusedError) as e:
            raise ConnectionError(f"Network printer unreachable at {self.ip_address}:{self.port} - {e}")
        except socket.error as e:
            raise IOError(f"Socket error communicating with {self.ip_address}: {e}")


class MockPrinterAdapter(BasePrinterAdapter):
    """Mock printer for testing and development."""
    def __init__(self, name: str):
        self.name = name

    def print_bytes(self, payload: bytes) -> None:
        if self.name.lower() == "mock_paper_out":
            raise IOError("Paper Out")
        # Silently succeed
        pass


class USBPrinterAdapter(BasePrinterAdapter):
    """Communicates with local USB printers (platform-dependent)."""
    
    def __init__(self, device_path: str = None):
        self.device_path = device_path

    def print_bytes(self, payload: bytes) -> None:
        """Attempt to send bytes to a local printer spooler or USB endpoint."""
        import os
        import platform
        
        # Windows via win32print
        if platform.system() == "Windows":
            try:
                import win32print
            except ImportError:
                logger.warning("win32print not installed. Cannot print to USB on Windows. Falling back to Mock.")
                return
            
            try:
                # If no specific device path is provided, use default printer
                printer_name = self.device_path or win32print.GetDefaultPrinter()
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    win32print.StartDocPrinter(hPrinter, 1, ("POS_Receipt", None, "RAW"))
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, payload)
                    win32print.EndPagePrinter(hPrinter)
                    win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)
            except Exception as e:
                raise IOError(f"Windows USB Print failed for '{self.device_path}': {e}")
        
        # Unix/Linux via /dev/usb/lpX or lp
        else:
            try:
                dev = self.device_path or "/dev/usb/lp0"
                if os.path.exists(dev):
                    with open(dev, "wb") as f:
                        f.write(payload)
                else:
                    # Fallback to lpr command
                    import subprocess
                    process = subprocess.Popen(['lpr', '-o', 'raw'], stdin=subprocess.PIPE)
                    process.communicate(payload)
                    if process.returncode != 0:
                        raise IOError("lpr command failed")
            except Exception as e:
                raise IOError(f"Unix USB Print failed: {e}")


def get_printer_adapter(printer_config) -> BasePrinterAdapter:
    """Factory method to return the correct adapter for a given Printer model instance."""
    if printer_config.name.lower().startswith("mock"):
        return MockPrinterAdapter(printer_config.name)
        
    if printer_config.connection_type == 'lan' or printer_config.connection_type == 'wifi':
        return NetworkPrinterAdapter(printer_config.ip_address, printer_config.port)
        
    if printer_config.connection_type == 'usb':
        return USBPrinterAdapter(printer_config.connection.get("device_path", ""))
        
    # Default fallback
    return MockPrinterAdapter("default_mock")
