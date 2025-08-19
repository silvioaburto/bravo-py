#!/usr/bin/env python3
"""
Example usage of the enhanced BravoDriver with state machine integration.
This demonstrates how to track the state of all nests during liquid handling operations.
"""

import logging
import time
from pybravo import BravoDriver

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def demo_basic_operations():
    """Demonstrate basic operations with state tracking"""
    print("=== Basic Operations Demo ===")

    # Initialize driver with state tracking enabled
    with BravoDriver(simulation_mode=True, enable_state_tracking=True) as bravo:

        # Setup deck with labware
        print("\n1. Setting up deck with labware...")
        bravo.set_labware_at_nest(1, "tip_rack", "200uL Tips")
        bravo.set_labware_at_nest(2, "microplate_96", "Source Plate")
        bravo.set_labware_at_nest(3, "microplate_96", "Destination Plate")
        bravo.set_labware_at_nest(4, "reservoir", "Wash Buffer")

        # Check initial state
        print(f"Empty nests: {bravo.find_labware('empty')}")
        print(f"Tip racks: {bravo.find_labware('tip_rack')}")
        print(f"Microplates: {bravo.find_labware('microplate_96')}")

        # Load tips
        print("\n2. Loading tips...")
        bravo.tips_on(1, tip_type="200uL")

        # Check tip status
        tip_nests = [
            nest_id
            for nest_id in range(1, 10)
            if bravo.get_nest_state(nest_id)
            and bravo.get_nest_state(nest_id)["tips_loaded"]
        ]
        print(f"Nests with tips loaded: {tip_nests}")

        # Perform liquid handling
        print("\n3. Performing liquid transfers...")
        bravo.aspirate(volume=100.0, plate_location=2)  # From source
        bravo.dispense(volume=100.0, plate_location=3)  # To destination

        # Wash tips
        print("\n4. Washing tips...")
        bravo.wash(
            volume=200.0,
            empty_tips=False,
            pre_aspirate_volume=0.0,
            blow_out_volume=50.0,
            cycles=3,
            plate_location=4,
        )

        # Check volumes
        source_state = bravo.get_nest_state(2)
        dest_state = bravo.get_nest_state(3)
        wash_state = bravo.get_nest_state(4)

        print(f"Source plate volumes: {source_state['current_volume']} uL dispensed")
        print(f"Destination plate volumes: {dest_state['current_volume']} uL received")
        print(f"Wash station usage: {wash_state['current_volume']} uL used")

        # Remove tips
        print("\n5. Removing tips...")
        bravo.tips_off(1)

        # Get final deck summary
        print("\n6. Final deck state:")
        deck_summary = bravo.get_deck_summary()
        print_deck_summary(deck_summary)


def demo_pick_and_place():
    """Demonstrate pick and place operations with state tracking"""
    print("\n\n=== Pick and Place Demo ===")

    with BravoDriver(simulation_mode=True, enable_state_tracking=True) as bravo:

        # Setup initial labware
        print("\n1. Initial setup...")
        bravo.set_labware_at_nest(5, "microplate_96", "Plate A")
        bravo.set_labware_at_nest(7, "deepwell_96", "Plate B")

        print("Before pick and place:")
        print(f"Nest 5: {bravo.get_nest_state(5)['labware_name']}")
        print(f"Nest 6: {bravo.get_nest_state(6)['labware_name']}")
        print(f"Nest 7: {bravo.get_nest_state(7)['labware_name']}")

        # Move Plate A from nest 5 to nest 6
        print("\n2. Moving Plate A from nest 5 to nest 6...")
        bravo.pick_and_place(
            start_location=5, end_location=6, gripper_offset=2.0, labware_thickness=14.0
        )

        print("After pick and place:")
        print(f"Nest 5: {bravo.get_nest_state(5)['labware_name']}")
        print(f"Nest 6: {bravo.get_nest_state(6)['labware_name']}")
        print(f"Nest 7: {bravo.get_nest_state(7)['labware_name']}")


def demo_error_handling():
    """Demonstrate error handling and state tracking"""
    print("\n\n=== Error Handling Demo ===")

    with BravoDriver(simulation_mode=True, enable_state_tracking=True) as bravo:

        # Setup some labware
        bravo.set_labware_at_nest(1, "tip_rack", "Tips")
        bravo.set_labware_at_nest(2, "microplate_96", "Test Plate")

        try:
            # Simulate an error condition
            print("Attempting operation that might fail...")
            bravo.aspirate(volume=1000.0, plate_location=2)  # Large volume

        except Exception as e:
            print(f"Caught expected error: {e}")

        # Check deck summary for error tracking
        deck_summary = bravo.get_deck_summary()
        print(f"Total errors recorded: {deck_summary['deck_info']['error_count']}")
        print(f"Last error: {deck_summary['deck_info']['last_error']}")


def demo_active_operations():
    """Demonstrate monitoring active operations"""
    print("\n\n=== Active Operations Monitoring ===")

    with BravoDriver(simulation_mode=True, enable_state_tracking=True) as bravo:

        # Setup deck
        bravo.set_labware_at_nest(1, "tip_rack", "Tips")
        bravo.set_labware_at_nest(2, "microplate_96", "Source")
        bravo.set_labware_at_nest(3, "microplate_96", "Destination")

        # In a real scenario, these operations would be non-blocking
        # and you could monitor their progress

        print("Starting multiple operations...")
        bravo.tips_on(1)

        # Check active operations (in simulation, operations complete immediately)
        active_ops = bravo.get_active_operations()
        print(f"Active operations: {len(active_ops)}")

        bravo.aspirate(volume=50.0, plate_location=2)
        bravo.move_to_location(3)
        bravo.dispense(volume=50.0, plate_location=3)

        print("All operations completed")


def print_deck_summary(summary):
    """Pretty print the deck summary"""
    print("\n--- Deck Summary ---")
    deck_info = summary["deck_info"]
    print(f"Total operations performed: {deck_info['global_operation_count']}")
    print(f"Errors encountered: {deck_info['error_count']}")
    print(f"Active operations: {summary['active_operations']}")
    print(f"Nests with labware: {summary['nests_with_labware']}")
    print(f"Nests with tips: {summary['nests_with_tips']}")

    print("\n--- Individual Nest States ---")
    for nest_id, nest_info in summary["nests"].items():
        if nest_info["labware_type"] != "empty" or nest_info["tips_loaded"]:
            print(f"Nest {nest_id}:")
            print(
                f"  Labware: {nest_info['labware_name']} ({nest_info['labware_type']})"
            )
            print(f"  Tips loaded: {nest_info['tips_loaded']}")
            print(f"  Current volume: {nest_info['current_volume']} uL")
            print(f"  Status: {nest_info['operation_status']}")


def main():
    """Main demo function"""
    print("BravoDriver State Machine Integration Demo")
    print("=" * 50)

    # Run all demos
    demo_basic_operations()
    demo_pick_and_place()
    demo_error_handling()
    demo_active_operations()

    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    main()
