# Home Assistant Integration (Optional)

This dashboard supports an optional Home Assistant integration to flash the LED blue when your dehumidifier tank is full.

## Features

- Slow blue LED flash when dehumidifier tank is detected as full
- Overrides normal price-based LED colors (highest priority alert)
- Completely optional - dashboard works fine without it

## Setup

### 1. Create Home Assistant Token

1. Log into your Home Assistant instance
2. Click on your profile (bottom left)
3. Scroll down to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Give it a name like "Agile Dashboard"
6. Copy the token (you won't be able to see it again!)

### 2. Configure the Integration

On your Pi (SSH into it):

```bash
cd /home/luke/agile-dashboard

# Copy the example config
cp ha_config.py.example ha_config.py

# Edit with your details
nano ha_config.py
```

Fill in:
- `HA_URL`: Your Home Assistant URL (e.g., `http://homeassistant.local:8123`)
- `HA_TOKEN`: The long-lived access token you created
- `DEHUMIDIFIER_POWER_SENSOR`: Your power sensor entity ID
- `DEHUMIDIFIER_FAN_ENTITY`: Your dehumidifier fan entity ID
- `POWER_THRESHOLD`: Power consumption threshold in watts (default: 100W)

### 3. Copy Integration Files

The integration files need to be manually copied to the Pi (they're not deployed by Ansible to keep credentials separate):

```bash
# On your control machine, from the project directory
scp ha_integration.py luke@pizero.local:/home/luke/agile-dashboard/
scp ha_config.py luke@pizero.local:/home/luke/agile-dashboard/  # After you've created it
```

### 4. Test the Integration

```bash
# On the Pi
cd /home/luke/agile-dashboard
python3 ha_integration.py
```

This will test your connection and show the current status.

### 5. Restart the Dashboard

```bash
sudo systemctl restart agile-dashboard
```

Check logs to confirm it loaded:

```bash
journalctl -u agile-dashboard -f
```

You should see: `Home Assistant integration loaded`

## How It Works

The integration checks two conditions:

1. **Fan is ON**: `fan.electriq_cd25pro_le_v4` state is `on`
2. **Power is LOW**: `sensor.dehumidifier_pm_power` < 100W

When both are true, it means:
- Dehumidifier is running (fan on)
- But consuming very little power (tank full, compressor not running)

The LED will slowly fade blue in/out over 4 seconds to alert you.

## Troubleshooting

**Integration not loading:**
```bash
# Check files exist
ls -la /home/luke/agile-dashboard/ha_*.py

# Test directly
python3 /home/luke/agile-dashboard/ha_integration.py
```

**API errors:**
- Verify your HA URL is correct and accessible from the Pi
- Check your token hasn't expired
- Verify entity IDs exist in Home Assistant

**LED not flashing:**
- Check the dehumidifier actually meets both conditions
- Look at dashboard logs: `journalctl -u agile-dashboard -n 50`

## Disabling

To disable the integration:

```bash
# On the Pi
cd /home/luke/agile-dashboard
rm ha_config.py
sudo systemctl restart agile-dashboard
```

The dashboard will continue working normally with just price-based LED colors.

## Security Notes

- `ha_config.py` is gitignored and never committed
- Keep your access token secret
- The token has full access to your Home Assistant, so treat it like a password
- Consider creating a separate HA user with limited permissions if desired
