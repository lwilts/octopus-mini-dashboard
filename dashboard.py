#!/usr/bin/env python3
"""
Development version of Octopus Energy Dashboard
Works on any system without Raspberry Pi hardware
"""
import time
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import sys
import os

# Try to import real ST7789, fall back to mock
try:
    import ST7789
    MOCK_MODE = False
    print("Running with real ST7789 display")
except ImportError:
    # Import mock version from local file
    try:
        import ST7789
        MOCK_MODE = True
        print("Running in MOCK MODE - will save images to PNG files")
    except ImportError:
        print("ERROR: ST7789.py mock file not found!")
        print("Place the mock ST7789.py file in the same directory")
        sys.exit(1)

# Display configuration
WIDTH = 320
HEIGHT = 240
ROTATION = 0

# Initialize display
disp = ST7789.ST7789(
    height=HEIGHT,
    width=WIDTH,
    rotation=ROTATION,
    port=0,
    cs=1,
    dc=9,
    backlight=13,
    spi_speed_hz=80 * 1000 * 1000
)

# Configuration
REGION = "C"  # London
AGILE_PRODUCT = "AGILE-24-10-01"
GAS_PRODUCT = "SILVER-25-09-02"

# Colors
BG_COLOR = (17, 24, 39)  # gray-900
TEXT_COLOR = (255, 255, 255)
BLUE = (59, 130, 246)
PURPLE = (168, 85, 247)
ORANGE = (251, 146, 60)
GRAY = (107, 114, 128)
GREEN = (34, 197, 94)
RED = (239, 68, 68)

# Try to load fonts, fall back to default
try:
    # Try Linux paths first
    font_paths = [
        "/usr/share/fonts/gnu-free/FreeSansBold.ttf",
        "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
        "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
    ]
    
    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break
    
    if font_path:
        font_xlarge = ImageFont.truetype(font_path, 28)
        font_large = ImageFont.truetype(font_path, 22)
        font_medium = ImageFont.truetype(font_path, 16)
        font_small = ImageFont.truetype(font_path, 12)
        font_tiny = ImageFont.truetype(font_path, 10)
        print(f"Using font: {font_path}")
    else:
        raise Exception("No font found")
except Exception as e:
    print(f"Could not load TTF fonts: {e}")
    print("Using default fonts")
    font_xlarge = ImageFont.load_default()
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_tiny = ImageFont.load_default()


def fetch_agile_prices():
    """Fetch Agile electricity prices with caching - returns (today_prices, tomorrow_prices)"""
    import json
    import glob

    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        today_cache = f"price-data-{today.strftime('%Y-%m-%d')}.json"
        tomorrow_cache = f"price-data-{tomorrow.strftime('%Y-%m-%d')}.json"

        # Clean up old cache files
        for old_file in glob.glob("price-data-*.json"):
            try:
                file_date_str = old_file.replace('price-data-', '').replace('.json', '')
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
                if file_date < today:
                    os.remove(old_file)
                    print(f"Removed old cache file: {old_file}")
            except:
                pass

        # Load from cache if available
        today_prices = []
        tomorrow_prices = []

        if os.path.exists(today_cache):
            print(f"Loading cached today prices from {today_cache}")
            with open(today_cache, 'r') as f:
                cached_data = json.load(f)
                for item in cached_data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    item['date'] = item['timestamp'].date()
                    today_prices.append(item)

        if os.path.exists(tomorrow_cache):
            print(f"Loading cached tomorrow prices from {tomorrow_cache}")
            with open(tomorrow_cache, 'r') as f:
                cached_data = json.load(f)
                for item in cached_data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    item['date'] = item['timestamp'].date()
                    tomorrow_prices.append(item)

        # If we have both from cache, return them
        if today_prices and tomorrow_prices:
            print(f"Loaded {len(today_prices)} today + {len(tomorrow_prices)} tomorrow from cache")
            return today_prices, tomorrow_prices

        # Otherwise fetch fresh data
        url = f"https://api.octopus.energy/v1/products/{AGILE_PRODUCT}/electricity-tariffs/E-1R-{AGILE_PRODUCT}-{REGION}/standard-unit-rates/"

        # Fetch today
        if not today_prices:
            params = {
                'period_from': f"{today}T00:00:00Z",
                'period_to': f"{tomorrow}T00:00:00Z"
            }
            print(f"Fetching today's prices...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data['results']:
                valid_from_utc = datetime.fromisoformat(item['valid_from'].replace('Z', '+00:00'))
                valid_from_local = valid_from_utc.astimezone()
                if valid_from_local.date() == today:
                    today_prices.append({
                        'hour': valid_from_local.hour,
                        'minute': valid_from_local.minute,
                        'price': item['value_inc_vat'],
                        'timestamp': valid_from_local,
                        'date': valid_from_local.date()
                    })

            today_prices.sort(key=lambda x: x['timestamp'])

            # Save today to cache
            cache_data = []
            for item in today_prices:
                cache_item = item.copy()
                cache_item['timestamp'] = cache_item['timestamp'].isoformat()
                cache_item['date'] = str(cache_item['date'])
                cache_data.append(cache_item)
            with open(today_cache, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Saved {len(today_prices)} today prices to cache")

        # Fetch tomorrow
        if not tomorrow_prices:
            day_after = tomorrow + timedelta(days=1)
            params = {
                'period_from': f"{tomorrow}T00:00:00Z",
                'period_to': f"{day_after}T00:00:00Z"
            }
            print(f"Fetching tomorrow's prices...")
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                for item in data['results']:
                    valid_from_utc = datetime.fromisoformat(item['valid_from'].replace('Z', '+00:00'))
                    valid_from_local = valid_from_utc.astimezone()
                    if valid_from_local.date() == tomorrow:
                        tomorrow_prices.append({
                            'hour': valid_from_local.hour,
                            'minute': valid_from_local.minute,
                            'price': item['value_inc_vat'],
                            'timestamp': valid_from_local,
                            'date': valid_from_local.date()
                        })

                tomorrow_prices.sort(key=lambda x: x['timestamp'])

                if tomorrow_prices:
                    # Save tomorrow to cache
                    cache_data = []
                    for item in tomorrow_prices:
                        cache_item = item.copy()
                        cache_item['timestamp'] = cache_item['timestamp'].isoformat()
                        cache_item['date'] = str(cache_item['date'])
                        cache_data.append(cache_item)
                    with open(tomorrow_cache, 'w') as f:
                        json.dump(cache_data, f, indent=2)
                    print(f"Saved {len(tomorrow_prices)} tomorrow prices to cache")
            except:
                print("Tomorrow's prices not available yet")

        return today_prices, tomorrow_prices

    except Exception as e:
        print(f"Error fetching Agile prices: {e}")
        return [], []


def fetch_gas_price():
    """Fetch gas tracker price - returns (today_price, tomorrow_price)"""
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        url = f"https://api.octopus.energy/v1/products/{GAS_PRODUCT}/gas-tariffs/G-1R-{GAS_PRODUCT}-{REGION}/standard-unit-rates/"

        # Fetch today and tomorrow in one call
        params = {
            'period_from': f"{today}T00:00:00Z",
            'period_to': f"{tomorrow}T23:59:59Z"
        }

        print(f"Fetching gas prices...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        today_price = None
        tomorrow_price = None

        for item in data['results']:
            valid_from_utc = datetime.fromisoformat(item['valid_from'].replace('Z', '+00:00'))
            valid_from_local = valid_from_utc.astimezone()

            if valid_from_local.date() == today:
                today_price = item['value_inc_vat']
            elif valid_from_local.date() == tomorrow:
                tomorrow_price = item['value_inc_vat']

        print(f"Gas - Today: {today_price}p/kWh, Tomorrow: {tomorrow_price}p/kWh")
        return today_price, tomorrow_price

    except Exception as e:
        print(f"Error fetching gas price: {e}")
        return None, None


def draw_price_with_small_p(draw, x, y, price, font_main, font_small, color):
    """Draw price with smaller 'p' suffix aligned to bottom of numerals"""
    price_str = f"{price:.1f}"
    draw.text((x, y), price_str, font=font_main, fill=color)

    # Get bounding boxes to align 'p' to bottom
    main_bbox = draw.textbbox((x, y), price_str, font=font_main)
    p_bbox = draw.textbbox((0, 0), "p", font=font_small)

    # Position 'p' after the price, aligned to bottom with slight offset up
    p_x = main_bbox[2] + 1
    p_y = main_bbox[3] - (p_bbox[3] - p_bbox[1]) - 2  # Align bottom edges, 2px higher

    draw.text((p_x, p_y), "p", font=font_small, fill=color)


def draw_dashboard(today_prices, tomorrow_prices, gas_today, gas_tomorrow):
    """Draw the dashboard on the display"""
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((5, 5), "Octopus Energy", font=font_medium, fill=TEXT_COLOR)

    # Current time
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    draw.text((WIDTH - 60, 5), time_str, font=font_medium, fill=TEXT_COLOR)

    if not today_prices:
        draw.text((10, HEIGHT//2), "Loading...", font=font_medium, fill=TEXT_COLOR)
        disp.display(img)
        return

    # Keep reference to all of today's prices (before trimming)
    all_today = today_prices.copy()

    # If we have tomorrow's data, trim first 12 hours of today
    has_tomorrow = bool(tomorrow_prices)
    if has_tomorrow and len(today_prices) >= 24:
        today_prices = today_prices[24:]  # Keep last 12 hours

    # Combine for display
    display_prices = today_prices + tomorrow_prices

    # Calculate current price, min, and max from ALL of today (not trimmed)
    current_hour = now.hour
    current_minute = now.minute
    current_price = next((p['price'] for p in all_today if p['hour'] == current_hour and p['minute'] == current_minute // 30 * 30), None)
    min_price = min(p['price'] for p in all_today)
    max_price = max(p['price'] for p in all_today)

    # Helper function to get color based on price thresholds
    def get_price_color(price):
        if price < 10: return GREEN
        elif price < 20: return BLUE
        elif price < 35: return (234, 179, 8)  # Yellow
        else: return RED

    # Draw price boxes (larger version)
    y_offset = 30
    box_height = 50
    box_half_height = box_height // 2

    # Current price box (left third) - color coded by price
    current_color = get_price_color(current_price) if current_price else BLUE
    draw.rectangle([(5, y_offset), (WIDTH//3 - 2, y_offset + box_height)], fill=current_color)
    draw.text((10, y_offset + 3), "Now", font=font_small, fill=(200, 200, 200))
    if current_price:
        draw_price_with_small_p(draw, 10, y_offset + 16, current_price, font_xlarge, font_medium, TEXT_COLOR)

    # Min price box (middle third, top half) - color coded by price
    min_color = get_price_color(min_price)
    draw.rectangle([(WIDTH//3 + 2, y_offset), (2*WIDTH//3 - 2, y_offset + box_half_height - 1)], fill=min_color)
    draw.text((WIDTH//3 + 7, y_offset + 3), "Min", font=font_small, fill=(200, 200, 200))
    draw_price_with_small_p(draw, WIDTH//3 + 35, y_offset + 3, min_price, font_large, font_small, TEXT_COLOR)

    # Max price box (middle third, bottom half) - color coded by price
    max_color = get_price_color(max_price)
    draw.rectangle([(WIDTH//3 + 2, y_offset + box_half_height + 1), (2*WIDTH//3 - 2, y_offset + box_height)], fill=max_color)
    draw.text((WIDTH//3 + 7, y_offset + box_half_height + 3), "Max", font=font_small, fill=(200, 200, 200))
    draw_price_with_small_p(draw, WIDTH//3 + 35, y_offset + box_half_height + 3, max_price, font_large, font_small, TEXT_COLOR)

    # Gas price box (right third)
    draw.rectangle([(2*WIDTH//3 + 2, y_offset), (WIDTH - 5, y_offset + box_height)], fill=ORANGE)
    draw.text((2*WIDTH//3 + 7, y_offset + 3), "Gas", font=font_small, fill=(255, 220, 200))
    if gas_today:
        draw_price_with_small_p(draw, 2*WIDTH//3 + 7, y_offset + 16, gas_today, font_xlarge, font_medium, TEXT_COLOR)

    # Tomorrow gas price in top-right if available
    if has_tomorrow and gas_tomorrow:
        gas_box_right = WIDTH - 8
        draw_price_with_small_p(draw, gas_box_right - 28, y_offset + 3, gas_tomorrow, font_medium, font_tiny, (255, 220, 200))
        tmrw_bbox = draw.textbbox((0, 0), "Tmrw", font=font_tiny)
        tmrw_width = tmrw_bbox[2] - tmrw_bbox[0]
        draw.text((gas_box_right - tmrw_width, y_offset + 18), "Tmrw", font=font_tiny, fill=(200,190,180))

    # Draw mini bar chart
    chart_y = y_offset + box_height + 10
    chart_height = HEIGHT - chart_y - 20
    chart_width = WIDTH - 35  # Leave space for y-axis labels
    chart_x = 30  # Start chart after labels

    if display_prices:
        # Y-axis always includes 0, but extends below if there are negative prices
        actual_min = min(p['price'] for p in display_prices)
        chart_min_price = min(0, actual_min)
        chart_max_price = max(p['price'] for p in display_prices)
        price_range = chart_max_price - chart_min_price if chart_max_price != chart_min_price else 1

        # Calculate bar width - use integer division for consistent width
        num_bars = len(display_prices)
        bar_width = chart_width // num_bars  # Integer division for consistent bar width
        remainder = chart_width % num_bars  # Leftover pixels

        # Calculate where tomorrow section starts
        tomorrow_start_idx = len(today_prices)
        tomorrow_start_x = chart_x + tomorrow_start_idx * bar_width

        # Draw tomorrow background FIRST (before gridlines)
        if has_tomorrow and tomorrow_start_idx < len(display_prices):
            tomorrow_bg_color = (30, 40, 60)
            draw.rectangle([
                (tomorrow_start_x, chart_y),
                (chart_x + chart_width, chart_y + chart_height)
            ], fill=tomorrow_bg_color)

        # Draw horizontal gridlines at 10p intervals - AFTER background, BEFORE bars
        gridline_interval = 10  # pence
        gridline_color = (100, 110, 130)
        for price_level in range(0, int(chart_max_price) + 10, gridline_interval):
            if price_level >= chart_min_price:
                y_pos = chart_y + chart_height - int((price_level - chart_min_price) / price_range * chart_height)
                # Only draw if within chart bounds
                if chart_y <= y_pos <= chart_y + chart_height:
                    draw.line([(chart_x, y_pos), (chart_x + chart_width, y_pos)], fill=gridline_color, width=1)

                    # Y-axis labels on the left
                    label = f"{price_level}"
                    draw.text((5, y_pos - 6), label, font=font_tiny, fill=(150, 150, 160))

        # Draw bars AFTER gridlines
        for i, price_data in enumerate(display_prices):
            x = chart_x + i * bar_width
            price = price_data['price']
            hour = price_data['hour']
            minute = price_data['minute']

            # Normalize height
            bar_height = int((price - chart_min_price) / price_range * chart_height)
            y = chart_y + chart_height - bar_height

            # Color coding
            color = get_price_color(price)

            # All bars have same width, with 2px gap
            bar_right = x + bar_width - 2

            # Draw the bar
            draw.rectangle([(x, y), (bar_right, chart_y + chart_height)], fill=color)

            # Draw vertical dashed line for current half-hour slot (only in today section)
            is_current = hour == current_hour and minute == current_minute // 30 * 30 and i < tomorrow_start_idx
            if is_current:
                line_x = x + bar_width // 2
                # Draw only within chart area
                for dash_y in range(chart_y, chart_y + chart_height, 6):
                    draw.line([(line_x, dash_y), (line_x, dash_y + 3)], fill=(220, 220, 220), width=1)

            # Draw hour labels for every 4 hours (including midnight) - center them under the bar
            if minute == 0 and (hour % 4 == 0 or hour == 0):
                hour_text = str(hour)
                # Adjust x position for single digit vs double digit
                text_offset = 3 if hour < 10 else 5
                text_x = x + (bar_width // 2) - text_offset
                draw.text((text_x, chart_y + chart_height + 2), hour_text, font=font_small, fill=TEXT_COLOR)

        # Draw tomorrow labels AFTER bars so they're on top
        if has_tomorrow and tomorrow_start_idx < len(display_prices):
            draw.text((tomorrow_start_x + 3, chart_y + 5), "Tmrw", font=font_medium, fill=(230, 230, 240))

            # Tomorrow max electric price - top-right of tomorrow section
            tomorrow_max = max(p['price'] for p in tomorrow_prices)
            tomorrow_max_color = get_price_color(tomorrow_max)
            chart_right = chart_x + chart_width

            # Draw "Max:" label - right aligned
            max_label = "Max:"
            max_label_bbox = draw.textbbox((0, 0), max_label, font=font_small)
            max_label_width = max_label_bbox[2] - max_label_bbox[0]
            max_label_x = chart_right - max_label_width - 2
            draw.text((max_label_x, chart_y + 5), max_label, font=font_small, fill=(230, 230, 240))

            # Draw price value below label - right aligned, color coded, no decimal
            price_str = f"{int(round(tomorrow_max))}p"
            price_bbox = draw.textbbox((0, 0), price_str, font=font_large)
            price_width = price_bbox[2] - price_bbox[0]
            price_x = chart_right - price_width - 2
            draw.text((price_x, chart_y + 16), price_str, font=font_large, fill=tomorrow_max_color)

    # Display the image
    disp.display(img)

    # In mock mode, also show the image
    if MOCK_MODE:
        try:
            img.show()  # Opens in default image viewer
        except:
            pass


def main():
    """Main loop"""
    print("Starting Octopus Energy Dashboard...")
    print(f"Display: {WIDTH}x{HEIGHT}, Region: {REGION}")
    print(f"Mode: {'MOCK (saving to files)' if MOCK_MODE else 'REAL HARDWARE'}")

    disp.begin()

    # Fetch data immediately
    print("\nFetching initial data...")
    today_prices, tomorrow_prices = fetch_agile_prices()
    gas_today, gas_tomorrow = fetch_gas_price()

    # Draw once
    print("\nDrawing dashboard...")
    draw_dashboard(today_prices, tomorrow_prices, gas_today, gas_tomorrow)

    if MOCK_MODE:
        print("\n" + "="*50)
        print("DEVELOPMENT MODE")
        print("="*50)
        print("Images saved to display_output_XXXX.png")
        print("Check your current directory for the files")
        print("\nIn production, this will run continuously.")
        print("Press Ctrl+C to exit early, or wait 30 seconds...")
        print("="*50)

        # In mock mode, just do a few iterations for testing
        for i in range(2):
            time.sleep(2)
            print(f"\nIteration {i+2}...")
            draw_dashboard(today_prices, tomorrow_prices, gas_today, gas_tomorrow)

        print("\nDevelopment test complete!")
    else:
        # Real hardware - run continuously
        last_update = time.time()
        update_interval = 300  # 5 minutes

        while True:
            try:
                current_time = time.time()

                # Update data every 5 minutes
                if current_time - last_update > update_interval:
                    print("Fetching new data...")
                    today_prices, tomorrow_prices = fetch_agile_prices()
                    gas_today, gas_tomorrow = fetch_gas_price()
                    last_update = current_time

                # Redraw display
                draw_dashboard(today_prices, tomorrow_prices, gas_today, gas_tomorrow)

                time.sleep(30)  # Redraw every 30 seconds for time update

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(10)


if __name__ == "__main__":
    main()