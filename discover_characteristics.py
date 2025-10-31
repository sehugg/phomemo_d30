#!/usr/bin/env python3
"""
Discover BLE characteristics for Phomemo D30 printer
"""
import asyncio
from bleak import BleakScanner, BleakClient


async def discover_and_inspect():
    """Discover D30 printer and list all its characteristics"""
    print("Scanning for Phomemo D30 printer...")
    devices = await BleakScanner.discover(timeout=10.0)

    device_address = None
    for device in devices:
        if device.name and "D30" in device.name.upper():
            print(f"Found printer: {device.name} ({device.address})")
            device_address = device.address
            break

    if device_address is None:
        print("No D30 printer found!")
        return

    print(f"\nConnecting to {device_address}...")
    async with BleakClient(device_address, timeout=20.0) as client:
        if not client.is_connected:
            print("Failed to connect!")
            return

        print("Connected! Discovering services and characteristics...\n")

        for service in client.services:
            print(f"Service: {service.uuid}")
            print(f"  Description: {service.description}")

            for char in service.characteristics:
                properties = ", ".join(char.properties)
                print(f"\n  Characteristic: {char.uuid}")
                print(f"    Handle: {char.handle}")
                print(f"    Properties: {properties}")
                print(f"    Description: {char.description}")

                # Check if characteristic supports writing
                if "write" in properties.lower() or "write-without-response" in properties.lower():
                    print(f"    >>> THIS CHARACTERISTIC SUPPORTS WRITING <<<")

            print()


if __name__ == "__main__":
    asyncio.run(discover_and_inspect())
