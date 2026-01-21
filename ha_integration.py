"""
Home Assistant Integration for Generic Condition Monitoring
Checks configurable conditions and flashes LED blue when met.
"""
import requests
from typing import Optional, Dict, Any

try:
    from ha_config import HA_URL, HA_TOKEN
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("ha_config.py not found - Home Assistant integration disabled")
    print("Copy ha_config.py.example to ha_config.py and configure it")

# Optional alert conditions - defaults to empty (no alerts)
try:
    from ha_config import CONDITIONS, CONDITION_LOGIC
except ImportError:
    CONDITIONS = []
    CONDITION_LOGIC = "AND"

# Optional message entity - can be configured separately
try:
    from ha_config import MESSAGE_ENTITY_ID
except ImportError:
    MESSAGE_ENTITY_ID = None


def get_entity_state(entity_id: str) -> Optional[dict]:
    """
    Get the state of a Home Assistant entity.

    Args:
        entity_id: The entity ID to query (e.g., 'sensor.temperature')

    Returns:
        Dictionary with state info, or None if error
    """
    if not CONFIG_AVAILABLE:
        return None

    try:
        headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        print(f"Error fetching {entity_id} from Home Assistant: {e}")
        return None


def evaluate_condition(condition: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition against Home Assistant state.

    Args:
        condition: Dictionary with entity_id, condition type, and value

    Returns:
        True if condition is met, False otherwise
    """
    entity_id = condition.get("entity_id")
    condition_type = condition.get("condition")
    expected_value = condition.get("value")

    # Get entity state
    state_data = get_entity_state(entity_id)
    if not state_data:
        return False

    current_state = state_data.get("state")

    # Handle numeric comparisons
    if condition_type in ["less_than", "greater_than"]:
        try:
            current_value = float(current_state)
            expected_value = float(expected_value)

            if condition_type == "less_than":
                return current_value < expected_value
            elif condition_type == "greater_than":
                return current_value > expected_value
        except (ValueError, TypeError):
            print(f"Cannot compare {current_state} numerically with {expected_value}")
            return False

    # Handle string comparisons
    elif condition_type == "equals":
        return str(current_state) == str(expected_value)
    elif condition_type == "not_equals":
        return str(current_state) != str(expected_value)

    return False


def get_message_of_the_day() -> Optional[str]:
    """
    Get the message of the day from Home Assistant input_text entity.

    Returns:
        The message string if set and non-empty, None otherwise
    """
    if not CONFIG_AVAILABLE or not MESSAGE_ENTITY_ID:
        return None

    state_data = get_entity_state(MESSAGE_ENTITY_ID)
    if not state_data:
        return None

    message = state_data.get("state", "")

    # Return None for empty, unknown, or unavailable states
    if not message or message.lower() in ("unknown", "unavailable", ""):
        return None

    return message.strip()


def should_flash_dehumidifier() -> bool:
    """
    Check if configured conditions are met and LED should flash blue.

    Returns True if conditions are met based on CONDITION_LOGIC (AND/OR)
    Returns False if:
    - HA integration not configured
    - Unable to fetch sensor data
    - Conditions not met
    """
    if not CONFIG_AVAILABLE:
        return False

    if not CONDITIONS:
        return False

    results = []
    for condition in CONDITIONS:
        result = evaluate_condition(condition)
        results.append(result)

        desc = condition.get("description", condition.get("entity_id"))
        if result:
            print(f"✓ Condition met: {desc}")
        else:
            print(f"✗ Condition not met: {desc}")

    # Apply logic
    if CONDITION_LOGIC.upper() == "AND":
        should_flash = all(results)
    else:  # OR
        should_flash = any(results)

    if should_flash:
        print(f"Alert triggered! ({CONDITION_LOGIC} logic satisfied)")

    return should_flash


if __name__ == "__main__":
    # Test the integration
    print("Testing Home Assistant integration...")
    print(f"Config available: {CONFIG_AVAILABLE}")

    if CONFIG_AVAILABLE:
        print(f"HA URL: {HA_URL}")
        print(f"Condition logic: {CONDITION_LOGIC}")
        print(f"Number of conditions: {len(CONDITIONS)}")
        print()

        for i, cond in enumerate(CONDITIONS, 1):
            desc = cond.get("description", cond.get("entity_id"))
            print(f"Condition {i}: {desc}")

        print()
        print("Evaluating conditions...")
        result = should_flash_dehumidifier()
        print()
        print(f"Final result - Should flash blue: {result}")
