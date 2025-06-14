"""
Printer helper
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from PIL import Image


class PrinterError(Exception):
    """Exception raised when printing operations fail."""


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
        except FileNotFoundError as exc:
            raise PrinterError("Command not found - printing system is not properly installed") from exc

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
    def print_image(
        cls,
        image_path: Path,
        copies: int = 1,
        landscape: bool = True,
        printer_name: str | None = None,
        print_args: Optional[List[str]] = None,
        border: int = 0,
    ) -> bool:
        """
        Print an image using lpr command.

        :param border:
        :param print_args: Additional settings to be passed to lpr
        :param printer_name: Override default printer
        :param image_path: Path to the image file
        :param copies: Number of copies to print, defaults to 1
        :param landscape: Whether to print in landscape orientation, defaults to True
        :return: True if printing was successful
        """
        if not image_path.exists():
            raise PrinterError(f"Image file does not exist: {image_path}")

        # Create temporary file with border if needed
        if border > 0:
            with Image.open(image_path) as img:
                # Calculate new dimensions while preserving aspect ratio
                aspect_ratio = img.width / img.height
                if aspect_ratio >= 1:  # Landscape or square
                    new_width = img.width + 2 * border
                    new_height = int(new_width / aspect_ratio)
                    if new_height % 2 != 0:  # Ensure even height for symmetry
                        new_height += 1
                else:  # Portrait
                    new_height = img.height + 2 * border
                    new_width = int(new_height * aspect_ratio)
                    if new_width % 2 != 0:  # Ensure even width for symmetry
                        new_width += 1

                new_img = Image.new("RGB", (new_width, new_height), "white")
                # Center the image in the new canvas
                paste_x = (new_width - img.width) // 2
                paste_y = (new_height - img.height) // 2
                new_img.paste(img, (paste_x, paste_y))

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    new_img.save(tmp.name, "JPEG")
                    image_path = Path(tmp.name)

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

        if print_args:
            cmd.extend(print_args)

        # Add the file to print
        cmd.append(str(image_path))

        cls._run_command(cmd, "Failed to print image")
        return True


if __name__ == "__main__":
    ps = PrinterService()
    print(ps.get_default_printer())
    print(ps.get_all_printers())

    # ps.print_image(Path("~/Downloads/test.txt").expanduser(), copies=1, landscape=False)
