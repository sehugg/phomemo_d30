# phomemo_d30
Python script to print text and images on a Phomemo D30 label printer via Bluetooth Low Energy (BLE)

Fork updated for macOS.

# Acknowledgements
Based on [phomemo-tools](https://github.com/vivier/phomemo-tools) by Laurent Vivier and
[phomemo_m02s](https://github.com/theacodes/phomemo_m02s) by theacodes.

# Example
<a href="http://www.youtube.com/watch?feature=player_embedded&v=U1ZqjYgFxjY
" target="_blank"><img src="http://img.youtube.com/vi/U1ZqjYgFxjY/maxresdefault.jpg"
alt="Video example of the Python script" width="640" /></a>

# Requirements
- Python 3
- ImageMagick (required for text rendering)
- Bluetooth adapter with BLE support

# Checkout and install
```bash
git clone https://github.com/polskafan/phomemo_d30.git
cd phomemo_d30
python3 -m venv venv
venv/bin/pip install -r requirements.txt
. venv/bin/activate
```

# Usage

The script automatically discovers and connects to your Phomemo D30 printer via Bluetooth Low Energy. Just ensure your printer is powered on and Bluetooth is enabled on your computer.

## Text Printing

Basic usage:
```bash
venv/bin/python print.py "Hello World!"
```

Print on "fruit" labels (adjusts offsets):
```bash
venv/bin/python print.py --fruit "This is a fruit label."
```

Change font:
```bash
venv/bin/python print.py --font Arial.ttf "Hello World!"
```

Multiline labels:
```bash
venv/bin/python print.py "First line\nSecond line"
```

## Image Printing

Print an image file:
```bash
venv/bin/python print.py --image photo.jpg
```

Print image on fruit label:
```bash
venv/bin/python print.py --image logo.png --fruit
```

Adjust brightness (0-200, default: 100):
```bash
venv/bin/python print.py --image photo.jpg --brightness 150
```

## Preview Mode

Preview the processed black & white image without printing:
```bash
venv/bin/python print.py --preview preview.png "Hello World!"
venv/bin/python print.py --image photo.jpg --brightness 120 --preview preview.png
```

## Manual Device Selection

Skip auto-discovery by specifying the device address:
```bash
venv/bin/python print.py --device XX:XX:XX:XX:XX:XX "Text"
```

## Reverse engineering steps
We are sniffing the Bluetooth initialization from "Printer Master" with Android bluetooth debugging and Wireshark (see https://www.wireshark.org/docs/man-pages/androiddump.html). tl;dr: If debugging is enabled in developer options and the phone is connected via ADB, Wireshark will display the bluetooth interface to create a capture file.

Looking at the pcap file, the printer seems to use the ESC/POS protocol by Epson. The init string that is sent right before the image data contains the paper size:
```1f1124001b401d7630000c004001```
(see [theacodes/phomemo_m02s/printer.py](https://github.com/theacodes/phomemo_m02s/blob/main/phomemo_m02s/printer.py))

```
Control Code: 1d
Page Init: 7630
Mode: 00
Paper Width: 0c00 =(Little Endian)=> 0xC =(hex2bin)=> 12 (=> 12 byte * 8 bit = 96 pixel)
Paper Height: 4001 =(Little Endian)=> 0x140 =(hex2bin)=> 320 pixel
```

Therefore the picture size is 320x96 (note: The picture is rotated by 90 degrees before printing).
