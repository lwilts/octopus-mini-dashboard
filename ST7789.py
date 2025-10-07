#!/usr/bin/env python3
"""
Mock ST7789 library for development on non-Raspberry Pi systems.
Place this file as ST7789.py in your project directory.
"""

class ST7789:
    """Mock ST7789 display that saves to PNG files instead"""
    
    def __init__(self, height=240, width=320, rotation=0, port=0, cs=1, 
                 dc=9, backlight=13, spi_speed_hz=80000000):
        self.height = height
        self.width = width
        self.rotation = rotation
        self.port = port
        self.cs = cs
        self.dc = dc
        self.backlight = backlight
        self.spi_speed_hz = spi_speed_hz
        self.display_count = 0
        print(f"Mock ST7789 Display initialized: {width}x{height}")
    
    def begin(self):
        """Initialize the display"""
        print("Mock display started")
    
    def display(self, image):
        """Save the image to a file instead of displaying"""
        filename = f"display_output_{self.display_count:04d}.png"
        image.save(filename)
        print(f"Saved display output to {filename}")
        self.display_count += 1
    
    def set_backlight(self, value):
        """Mock backlight control"""
        print(f"Backlight set to: {value}")


# Mock GPIO functions if needed
class GPIO:
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0
    
    @staticmethod
    def setmode(mode):
        print(f"GPIO mode set to: {mode}")
    
    @staticmethod
    def setup(pin, mode):
        print(f"GPIO pin {pin} set to {mode}")
    
    @staticmethod
    def output(pin, value):
        print(f"GPIO pin {pin} output: {value}")
    
    @staticmethod
    def cleanup():
        print("GPIO cleanup")


# Mock SPI if needed
class SpiDev:
    def __init__(self):
        self.max_speed_hz = 0
    
    def open(self, bus, device):
        print(f"SPI opened on bus {bus}, device {device}")
    
    def close(self):
        print("SPI closed")
    
    def xfer2(self, data):
        return [0] * len(data)