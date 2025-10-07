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

# Always use mock mode for snapshot script
import ST7789
MOCK_MODE = True
print("Running in SNAPSHOT MODE - will save single image to PNG")

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
    """Fetch Agile electricity prices with caching - includes tomorrow if available"""
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        cache_file = f"price-data-{today.strftime('%Y-%m-%d')}.json"

        # Clean up old cache files
        import glob
        for old_file in glob.glob("price-data-*.json"):
            try:
                file_date_str = old_file.replace('price-data-', '').replace('.json', '')
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
                if file_date < today:
                    os.remove(old_file)
                    print(f"Removed old cache file: {old_file}")
            except:
                pass

        # Check if we have cached data for today
        if os.path.exists(cache_file):
            print(f"Loading cached price data from {cache_file}")
            with open(cache_file, 'r') as f:
                import json
                cached_data = json.load(f)
                # Reconstruct datetime objects
                prices = []
                for item in cached_data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    if 'date' in item:
                        item['date'] = datetime.fromisoformat(item['date']).date()
                    prices.append(item)
                print(f"Loaded {len(prices)} cached price points")
                return prices

        # Fetch fresh data - try to get today and tomorrow
        day_after = tomorrow + timedelta(days=1)
        url = f"https://api.octopus.energy/v1/products/{AGILE_PRODUCT}/electricity-tariffs/E-1R-{AGILE_PRODUCT}-{REGION}/standard-unit-rates/"
        params = {
            'period_from': f"{today}T00:00:00Z",
            'period_to': f"{day_after}T00:00:00Z"  # Try to get tomorrow too
        }

        print(f"Fetching Agile prices (including tomorrow if available)...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        prices = []
        for item in data['results']:
            # Parse UTC time and convert to local time
            valid_from_utc = datetime.fromisoformat(item['valid_from'].replace('Z', '+00:00'))
            # Convert to local timezone (UK)
            valid_from_local = valid_from_utc.astimezone()
            prices.append({
                'hour': valid_from_local.hour,
                'minute': valid_from_local.minute,
                'price': item['value_inc_vat'],
                'timestamp': valid_from_local,
                'date': valid_from_local.date()
            })

        prices.sort(key=lambda x: x['timestamp'])

        # Count tomorrow's data
        tomorrow_count = sum(1 for p in prices if p['date'] == tomorrow)
        print(f"Fetched {len(prices)} price points (today: {len(prices) - tomorrow_count}, tomorrow: {tomorrow_count})")

        # Save to cache
        import json
        cache_data = []
        for item in prices:
            cache_item = item.copy()
            cache_item['timestamp'] = cache_item['timestamp'].isoformat()
            cache_item['date'] = cache_item['date'].isoformat()
            cache_data.append(cache_item)

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print(f"Saved price data to cache: {cache_file}")

        return prices
    except Exception as e:
        print(f"Error fetching Agile prices: {e}")
        return []


def fetch_gas_price():
    """Fetch gas tracker price for today and tomorrow"""
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        # Fetch today's gas price
        url = f"https://api.octopus.energy/v1/products/{GAS_PRODUCT}/gas-tariffs/G-1R-{GAS_PRODUCT}-{REGION}/standard-unit-rates/"
        params = {
            'period_from': f"{today}T00:00:00Z",
            'period_to': f"{today}T23:59:59Z"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        today_price = data['results'][0]['value_inc_vat'] if data['results'] else None

        # Try to fetch tomorrow's gas price
        params['period_from'] = f"{tomorrow}T00:00:00Z"
        params['period_to'] = f"{tomorrow}T23:59:59Z"

        response = requests.get(url, params=params, timeout=10)
        tomorrow_price = None
        if response.status_code == 200:
            data = response.json()
            tomorrow_price = data['results'][0]['value_inc_vat'] if data['results'] else None

        print(f"Gas price today: {today_price}p/kWh, tomorrow: {tomorrow_price if tomorrow_price else 'N/A'}")
        return {'today': today_price, 'tomorrow': tomorrow_price}
    except Exception as e:
        print(f"Error fetching gas price: {e}")
        return {'today': None, 'tomorrow': None}


def add_mock_tomorrow_data(prices):
    """Add mock tomorrow data for testing"""
    import random
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # Check if we already have tomorrow data
    has_tomorrow = any(p.get('date') == tomorrow for p in prices)
    if has_tomorrow:
        print("Tomorrow data already available")
        return prices

    print("Adding mock tomorrow data for testing...")
    mock_tomorrow = []

    # Generate 48 half-hourly prices for tomorrow (slightly different pattern)
    for hour in range(24):
        for minute in [0, 30]:
            timestamp = datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute))
            timestamp = timestamp.replace(tzinfo=prices[0]['timestamp'].tzinfo)

            # Mock price with some variation
            base_price = 15 + random.uniform(-5, 10)
            if hour >= 16 and hour < 19:  # Evening peak
                base_price += random.uniform(10, 20)
            elif hour >= 2 and hour < 5:  # Night cheap
                base_price -= random.uniform(8, 12)

            mock_tomorrow.append({
                'hour': hour,
                'minute': minute,
                'price': max(1, base_price),
                'timestamp': timestamp,
                'date': tomorrow
            })

    return prices + mock_tomorrow


def add_mock_tomorrow_gas(gas_price):
    """Add mock tomorrow gas price for testing"""
    if isinstance(gas_price, dict) and gas_price.get('tomorrow') is None:
        import random
        # Mock tomorrow gas price (slightly different from today)
        gas_price['tomorrow'] = gas_price['today'] + random.uniform(-0.5, 0.8)
        print(f"Added mock tomorrow gas: {gas_price['tomorrow']:.2f}p")
    return gas_price


def draw_price_with_small_p(draw, x, y, price, font_main, font_small, color):
    """Draw price with smaller 'p' suffix"""
    # Draw the number
    price_str = f"{price:.1f}"
    draw.text((x, y), price_str, font=font_main, fill=color)

    # Get bounding boxes to align 'p' to bottom
    main_bbox = draw.textbbox((x, y), price_str, font=font_main)
    p_bbox = draw.textbbox((0, 0), "p", font=font_small)

    # Position 'p' after the price, aligned to bottom with slight offset up
    p_x = main_bbox[2] + 1
    p_y = main_bbox[3] - (p_bbox[3] - p_bbox[1]) - 2  # Align bottom edges, 2px higher

    # Draw smaller 'p'
    draw.text((p_x, p_y), "p", font=font_small, fill=color)


def draw_dashboard(agile_prices, gas_price, save_path=None):
    """Draw the dashboard on the display"""
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((5, 5), "Octopus Energy", font=font_medium, fill=TEXT_COLOR)

    # Current time
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    time_str = now.strftime("%H:%M")
    draw.text((WIDTH - 60, 5), time_str, font=font_medium, fill=TEXT_COLOR)

    if not agile_prices:
        draw.text((10, HEIGHT//2), "Loading...", font=font_medium, fill=TEXT_COLOR)
        if MOCK_MODE:
            if save_path is None:
                timestamp = now.strftime("%Y%m%d-%H%M%S")
                save_path = f"dashboard-{timestamp}.png"
            img.save(save_path)
            print(f"Dashboard snapshot saved to {save_path}")
        else:
            disp.display(img)
        return

    # Separate today and tomorrow prices
    today_prices = [p for p in agile_prices if p.get('date', today) == today]
    tomorrow_prices = [p for p in agile_prices if p.get('date') == tomorrow]
    has_tomorrow = len(tomorrow_prices) > 0

    # If we have tomorrow data, trim first 12 hours of today
    if has_tomorrow and today_prices:
        noon = datetime.combine(today, datetime.min.time().replace(hour=12))
        noon = noon.replace(tzinfo=today_prices[0]['timestamp'].tzinfo)
        today_prices = [p for p in today_prices if p['timestamp'] >= noon]
        display_prices = today_prices + tomorrow_prices
    elif has_tomorrow:
        display_prices = tomorrow_prices
    else:
        display_prices = today_prices
    
    # Calculate current price, min, and max (today only for Now/Min/Max)
    current_hour = now.hour
    current_minute = now.minute

    # Find current price from ALL today's prices (before trimming)
    all_today = [p for p in agile_prices if p.get('date', today) == today]
    current_price = next((p['price'] for p in all_today if p['hour'] == current_hour and p['minute'] == current_minute // 30 * 30), None)

    # Calculate min/max from all today prices (not trimmed)
    min_price = min(p['price'] for p in all_today) if all_today else 0
    max_price = max(p['price'] for p in all_today) if all_today else 0

    # Tomorrow's peak (if available)
    tomorrow_max = max(p['price'] for p in tomorrow_prices) if tomorrow_prices else None

    # Helper function to get color based on price thresholds
    def get_price_color(price):
        if price < 10: return GREEN
        elif price < 20: return BLUE
        elif price < 35: return (234, 179, 8)  # Yellow
        else: return RED

    # Draw price boxes (adjusted for tomorrow info)
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
    gas_today = gas_price.get('today') if isinstance(gas_price, dict) else gas_price
    gas_tomorrow = gas_price.get('tomorrow') if isinstance(gas_price, dict) else None

    draw.rectangle([(2*WIDTH//3 + 2, y_offset), (WIDTH - 5, y_offset + box_height)], fill=ORANGE)
    draw.text((2*WIDTH//3 + 7, y_offset + 3), "Gas", font=font_small, fill=(255, 220, 200))

    if gas_today:
        draw_price_with_small_p(draw, 2*WIDTH//3 + 7, y_offset + 16, gas_today, font_xlarge, font_medium, TEXT_COLOR)

    # Tomorrow gas in top right of gas box (if available)
    if has_tomorrow and gas_tomorrow:
        # Position in top-right corner of gas box
        gas_box_right = WIDTH - 8
        draw.text((gas_box_right - 28, y_offset + 3), "Tmrw:", font=font_tiny, fill=(100, 100, 100))
        draw_price_with_small_p(draw, gas_box_right - 28, y_offset + 11, gas_tomorrow, font_medium, font_tiny, (80, 80, 80))

    # Tomorrow info will be drawn after chart for proper positioning
    
    # Draw mini bar chart
    chart_y = y_offset + box_height + 10
    chart_height = HEIGHT - chart_y - 20
    chart_left = 20  # Start after y-axis labels
    chart_right = WIDTH - 5  # Right edge
    chart_width = chart_right - chart_left

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

        # Find the split point between today and tomorrow
        tomorrow_start_idx = len(today_prices) if has_tomorrow else len(display_prices)

        # Draw tomorrow background FIRST (before gridlines)
        if has_tomorrow and tomorrow_start_idx < len(display_prices):
            tomorrow_start_x = chart_left + tomorrow_start_idx * bar_width
            tomorrow_bg = (30, 40, 60)  # More visibly lighter than main BG
            draw.rectangle([(tomorrow_start_x, chart_y), (chart_right, chart_y + chart_height)], fill=tomorrow_bg)

        # Y-axis gridlines every 10p (AFTER background)
        gridline_interval = 10
        min_grid = int(chart_min_price // gridline_interval) * gridline_interval
        max_grid = int(chart_max_price // gridline_interval + 1) * gridline_interval

        for grid_price in range(min_grid, max_grid + 1, gridline_interval):
            if chart_min_price <= grid_price <= chart_max_price:
                y_pos = chart_y + chart_height - int((grid_price - chart_min_price) / price_range * chart_height)
                # Only draw if within chart bounds
                if chart_y <= y_pos <= chart_y + chart_height:
                    # Solid horizontal gridline (drawn AFTER background so visible)
                    draw.line([(chart_left, y_pos), (chart_right, y_pos)], fill=(100, 110, 130), width=1)
                    # Y-axis label on the left
                    draw.text((2, y_pos - 6), f"{grid_price}", font=font_tiny, fill=GRAY)

        for i, price_data in enumerate(display_prices):
            x = chart_left + i * bar_width
            price = price_data['price']
            hour = price_data['hour']
            minute = price_data['minute']
            is_tomorrow = i >= tomorrow_start_idx

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

            # Draw hour labels for every 4 hours (including midnight)
            if minute == 0 and (hour % 4 == 0 or hour == 0):
                hour_text = str(hour)
                # Adjust x position for single digit vs double digit
                text_offset = 3 if hour < 10 else 5
                text_x = x + (bar_width // 2) - text_offset
                draw.text((text_x, chart_y + chart_height + 2), hour_text, font=font_tiny, fill=TEXT_COLOR)

        # Draw tomorrow labels AFTER bars so they're on top
        if has_tomorrow and tomorrow_start_idx < len(display_prices):
            # "Tmrw" label in top-left of tomorrow section
            draw.text((tomorrow_start_x + 3, chart_y + 5), "Tmrw", font=font_tiny, fill=(150, 150, 160))

    # Tomorrow max electric price - top right of chart area (drawn AFTER bars)
    if has_tomorrow and tomorrow_max:
        # Position in top-right of chart
        info_x = WIDTH - 30
        info_y = chart_y + 5

        # Show max price on two lines with larger value (gas is in gas box now)
        tmrw_color = get_price_color(tomorrow_max)
        draw.text((info_x, info_y), "Max:", font=font_tiny, fill=(150, 150, 160))
        # Draw price with small p
        price_str = f"{tomorrow_max:.0f}"
        draw.text((info_x - 5, info_y + 9), price_str, font=font_medium, fill=tmrw_color)
        bbox = draw.textbbox((info_x - 5, info_y + 9), price_str, font=font_medium)
        draw.text((bbox[2] + 1, info_y + 11), "p", font=font_tiny, fill=tmrw_color)

    # Save to file in snapshot mode, otherwise display
    if MOCK_MODE:
        if save_path is None:
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            save_path = f"dashboard-{timestamp}.png"
        img.save(save_path)
        print(f"Dashboard snapshot saved to {save_path}")
    else:
        disp.display(img)


def main():
    """Main loop"""
    import argparse

    parser = argparse.ArgumentParser(description='Octopus Energy Dashboard Snapshot')
    parser.add_argument('--mock-tomorrow', action='store_true',
                       help='Add mock tomorrow data for testing')
    args = parser.parse_args()

    print("Starting Octopus Energy Dashboard...")
    print(f"Display: {WIDTH}x{HEIGHT}, Region: {REGION}")
    print(f"Mode: {'MOCK (saving to files)' if MOCK_MODE else 'REAL HARDWARE'}")

    disp.begin()

    # Fetch data immediately
    print("\nFetching initial data...")
    agile_prices = fetch_agile_prices()
    gas_price = fetch_gas_price()

    # Add mock tomorrow data if requested
    if args.mock_tomorrow:
        agile_prices = add_mock_tomorrow_data(agile_prices)
        gas_price = add_mock_tomorrow_gas(gas_price)

    # Draw once
    print("\nDrawing dashboard...")
    draw_dashboard(agile_prices, gas_price)

    if MOCK_MODE:
        print("\n" + "="*50)
        print("SNAPSHOT MODE - Single image saved")
        print("="*50)
        print("Snapshot complete!")
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
                    agile_prices = fetch_agile_prices()
                    gas_price = fetch_gas_price()
                    last_update = current_time

                # Redraw display
                draw_dashboard(agile_prices, gas_price)

                time.sleep(30)  # Redraw every 30 seconds for time update

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(10)


if __name__ == "__main__":
    main()