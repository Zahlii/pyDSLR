import logging
import subprocess
from pathlib import Path
from typing import List, Optional


class PrinterError(Exception):
    """Exception raised when printing operations fail."""

    pass


class PrinterService:
    """
    Printer service for printing images using system commands.
    """

    @staticmethod
    def _run_command(cmd: List[str], error_prefix: str) -> subprocess.CompletedProcess:
        """
        Run a subprocess command and handle errors consistently.

        :param cmd: Command to run as a list of strings
        :param error_prefix: Prefix for error message if command fails
        :return: CompletedProcess instance with the command result
        :raises PrinterError: If the command fails or the command is not found
        """
        try:
            logging.info("Running %s", cmd)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result
        except subprocess.SubprocessError as e:
            stderr_output = getattr(e, "stderr", "")
            if hasattr(e, "stderr") and isinstance(e.stderr, bytes):
                stderr_output = e.stderr.decode("utf-8", errors="replace")
            error_msg = f"{error_prefix}: {e}"
            if stderr_output:
                error_msg += f"\nDetailed Error: {stderr_output}"
            raise PrinterError(error_msg) from e
        except FileNotFoundError:
            raise PrinterError(f"Command not found - printing system is not properly installed")

    @classmethod
    def get_all_printers(cls) -> list[str]:
        """
        Get a list of all available printers using lpstat command.

        :return: List of printer names
        """
        result = cls._run_command(["lpstat", "-p"], "Failed to get printer list")

        printers = []
        output = result.stdout.strip()

        # Parse each line of the output
        # Format is typically: "printer printer_name is idle.  enabled since..."
        for line in output.splitlines():
            if line.startswith("printer "):
                # Extract printer name (typically the second word before " is ")
                parts = line.split(" is ", 1)
                if len(parts) > 1:
                    printer_name = parts[0].replace("printer ", "").strip()
                    printers.append(printer_name)

        return printers

    @classmethod
    def get_default_printer(cls) -> Optional[str]:
        """
        Get the default printer name using lpstat command.

        :return: The default printer name or None if no default printer is set
        """
        result = cls._run_command(["lpstat", "-d"], "Failed to get default printer")

        # Parse the output to extract the printer name
        output = result.stdout.strip()
        if "no default destination" in output.lower():
            return None

        # Format is typically: "system default destination: printer_name"
        parts = output.split(":")
        if len(parts) > 1:
            return parts[1].strip()
        return None

    @classmethod
    def print_image(cls, image_path: Path, copies: int = 1, landscape: bool = True, printer_name: str | None = None) -> bool:
        """
        Print an image using lpr command.

        :param printer_name: Override default printer
        :param image_path: Path to the image file
        :param copies: Number of copies to print, defaults to 1
        :param landscape: Whether to print in landscape orientation, defaults to True
        :return: True if printing was successful
        """
        if not image_path.exists():
            raise PrinterError(f"Image file does not exist: {image_path}")

        # Get printer
        printer = printer_name or cls.get_default_printer()

        # Build the lpr command
        cmd = ["lpr"]

        if printer is not None:
            # Add printer if specified
            cmd.extend(["-P", printer])

        # Add copies
        if copies > 1:
            cmd.extend(["-#", str(copies)])

        # Add landscape option
        if landscape:
            cmd.extend(["-o", "landscape"])

        # Add the file to print
        cmd.append(str(image_path))

        cls._run_command(cmd, "Failed to print image")
        return True


if __name__ == "__main__":
    ps = PrinterService()
    print(ps.get_all_printers())

    ps.print_image(Path("~/Downloads/test.txt").expanduser(), copies=1, landscape=False)
