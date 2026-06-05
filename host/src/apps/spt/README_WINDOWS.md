# Windows Support for TI Security Provisioning Tool (SPT)

This document explains how to use the Security Provisioning Tool (SPT) on Windows platforms.

## Overview

The SPT application now supports cross-platform operation on Windows, Linux, and macOS. This document focuses specifically on Windows usage.

## Serial Port Names

On Windows systems, serial ports follow a different naming convention than on Unix-like systems:

- Windows: Uses `COM<n>` format (e.g., `COM1`, `COM3`, `COM10`)
- Linux: Uses `/dev/ttyUSB<n>` or `/dev/ttyACM<n>` format
- macOS: Uses `/dev/cu.usbmodem<id>` or `/dev/cu.usbserial<id>` format

## Finding Available Ports

You can list all available serial ports using the built-in `list-ports` command:

```
python -m apps.spt --device <device_name> list-ports
```

This will display a list of available serial ports on your system with their descriptions.

## Usage Examples

### Download a Binary

```
python -m apps.spt --device f29h85x download -p COM3 -b path\to\bootloader.bin
```

### Parse SoC ID

```
python -m apps.spt --device f29h85x parseSoCId -s "SoC ID string"
```

## Troubleshooting

### Port Access Issues

If you encounter issues with port access:

1. Ensure no other application is using the COM port
2. Check Device Manager to confirm the port exists and is working properly
3. Try unplugging and reconnecting the device
4. Verify you are using the correct port number

### Finding the Right COM Port

To identify the correct COM port:

1. Open Device Manager (right-click Start → Device Manager)
2. Expand "Ports (COM & LPT)"
3. Note the COM port number assigned to your device
4. Alternatively, use the `list-ports` command as described above

### Permissions

Unlike Linux, Windows does not usually require special permissions to access serial ports. However:

- Ensure you're running the command prompt or PowerShell with appropriate permissions
- Some applications may lock the COM port, preventing access until they're closed

## Additional Notes

- Paths in Windows use backslashes (`\`), but Python can handle forward slashes (`/`) as well
- When specifying file paths with spaces, enclose them in quotes
- The SPT tool handles cross-platform path normalization automatically

## Known Windows-Specific Issues

- **Error Handling**: Error messages may still contain some Linux-specific suggestions. If you see references to Linux commands, use the Windows equivalents instead.
- **COM Port Numbers**: Windows COM ports with numbers greater than 9 should be specified as `COM10`, `COM11`, etc. (no space between COM and the number)
- **USB Driver Installation**: Some TI devices may require installing specific USB drivers on Windows. Refer to the device documentation for details.

For more general information about the SPT tool, refer to the main documentation.