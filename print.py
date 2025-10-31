#!/usr/bin/env python3
import click
import asyncio
from bleak import BleakScanner, BleakClient
from wand.image import Image
from wand.font import Font
import PIL.Image
import image_helper
import os


# Phomemo D30 BLE characteristics
# Discovered via BLE scanning - service 0000ff00, characteristic 0000ff02
WRITE_CHARACTERISTIC_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"


@click.command()
@click.argument('text', required=False)
@click.option('--font', default="Helvetica", help='Path to TTF font file')
@click.option('--fruit', is_flag=True, show_default=True, default=False,
              help='Enable offsets to print on a fruit label')
@click.option('--device', default=None, help='BLE device address (auto-discover if not provided)')
@click.option('--image', type=click.Path(exists=True), help='Print an image file instead of text')
def main(text, font, fruit, device, image):
    if image is None and text is None:
        raise click.UsageError("Either TEXT argument or --image option is required")
    if image is not None and text is not None:
        raise click.UsageError("Cannot use both TEXT argument and --image option")

    asyncio.run(async_main(text, font, fruit, device, image))


async def async_main(text, font, fruit, device_address, image_path):
    if device_address is None:
        device_address = await discover_printer()
        if device_address is None:
            click.echo("No Phomemo D30 printer found. Please ensure it's powered on and in range.")
            return

    click.echo(f"Connecting to printer at {device_address}...")

    async with BleakClient(device_address, timeout=20.0) as client:
        if not client.is_connected:
            click.echo("Failed to connect to printer")
            return

        click.echo("Connected! Preparing image...")

        # Use provided image or generate from text
        if image_path:
            filename = prepare_image_file(image_path, fruit, "temp.png")
        else:
            filename = generate_image(text, font, fruit, "temp.png")

        click.echo("Sending print job...")
        await header(client)
        await print_image(client, filename)
        os.remove(filename)

        click.echo("Print complete!")


async def discover_printer():
    """Discover Phomemo D30 printer via BLE scanning"""
    click.echo("Scanning for Phomemo D30 printer...")
    devices = await BleakScanner.discover(timeout=10.0)

    for device in devices:
        # Look for D30 in device name
        if device.name and "D30" in device.name.upper():
            click.echo(f"Found printer: {device.name} ({device.address})")
            return device.address

    return None


async def header(client):
    """Send printer initialization packets via BLE"""
    # printer initialization sniffed from Android app "Print Master"
    packets = [
        '1f1138',
        '1f11121f1113',
        '1f1109',
        '1f1111',
        '1f1119',
        '1f1107',
        '1f110a1f110202'
    ]

    for packet in packets:
        await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, bytes.fromhex(packet))
        await asyncio.sleep(0.05)  # Small delay between packets


def prepare_image_file(image_path, fruit, output_filename):
    """Prepare an existing image file for printing"""
    if fruit:
        width, height = 240, 80
    else:
        width, height = 288, 88

    with Image(filename=image_path) as img:
        # Detect if image is landscape or portrait
        is_portrait = img.width < img.height

        # If portrait, rotate 90 degrees to make it landscape before processing
        if is_portrait:
            click.echo(f"Detected portrait image ({img.width}x{img.height}), rotating to landscape...")
            img.rotate(90)
        else:
            click.echo(f"Detected landscape image ({img.width}x{img.height})")

        # Resize to fit label dimensions while maintaining aspect ratio
        img.transform(resize=f"{width}x{height}")

        # Create a new image with exact dimensions and paste centered
        with Image(width=width, height=height, background="white") as canvas:
            # Center the image on the canvas
            canvas.composite(img, left=(width - img.width) // 2, top=(height - img.height) // 2)

            # Convert to 1-bit with Floyd-Steinberg dithering for better print quality
            # First enhance contrast, then apply dithering
            canvas.auto_level()  # Expand to full contrast
            canvas.quantize(number_colors=2, colorspace_type='gray', dither='floyd_steinberg')
            canvas.transform_colorspace('gray')

            # extent and rotate image
            canvas.background_color = "white"
            canvas.gravity = "center"
            if fruit:
                canvas.extent(width=320, height=96, x=-60)
            else:
                canvas.extent(width=320, height=96)
            canvas.rotate(270)
            canvas.save(filename=output_filename)

    return output_filename


def generate_image(text, font, fruit, filename):
    """Generate an image from text"""
    font = Font(path=font)
    if fruit:
        width, height = 240, 80
    else:
        width, height = 288, 88

    with Image(width=width, height=height, background="white") as img:
        # center text, fill canvas
        img.caption(text, font=font, gravity="center")

        # extent and rotate image
        img.background_color = "white"
        img.gravity = "center"
        if fruit:
            img.extent(width=320, height=96, x=-60)
        else:
            img.extent(width=320, height=96)
        img.rotate(270)
        img.save(filename=filename)

    return filename


async def print_image(client, filename):
    """Send image data to printer via BLE"""
    width = 96

    with PIL.Image.open(filename) as src:
        image = image_helper.preprocess_image(src, width)

    # printer initialization sniffed from Android app "Print Master"
    output = '1f1124001b401d7630000c004001'

    # adapted from https://github.com/theacodes/phomemo_m02s/blob/main/phomemo_m02s/printer.py
    for chunk in image_helper.split_image(image):
        output = bytearray.fromhex(output)

        bits = image_helper.image_to_bits(chunk)
        for line in bits:
            for byte_num in range(width // 8):
                byte = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte |= (pixel & 0x01) << (7 - bit)
                output.append(byte)

        # BLE has MTU limitations, so we may need to chunk large writes
        # Most BLE devices support at least 20 bytes, commonly 512 bytes
        MAX_CHUNK_SIZE = 512
        for i in range(0, len(output), MAX_CHUNK_SIZE):
            chunk_data = output[i:i + MAX_CHUNK_SIZE]
            await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, chunk_data)
            await asyncio.sleep(0.01)  # Small delay between chunks

        output = ''


if __name__ == '__main__':
    main()
