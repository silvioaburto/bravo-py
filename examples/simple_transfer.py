import logging
from pybravo.visualizer_enhanced import (
    BravoDriverWithVisualizer,
    start_visualizer_server,
)
import time

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Start visualizer server
    start_visualizer_server()

    try:
        with BravoDriverWithVisualizer(
            simulation_mode=True, with_visualizer=True
        ) as driver:
            driver.set_labware_at_location(2, "plate-96")
            driver.tips_on(plate_location=1)
            time.sleep(2)
            driver.aspirate(
                100.0, plate_location=2
            )  # Should show blue glow at position 2
            time.sleep(2)
            driver.dispense(
                50.0, plate_location=8
            )  # Should show green glow at position 8
            time.sleep(2)
            driver.tips_off(plate_location=9)  # Should show purple glow at position 9

            state = driver.get_simulation_state()
            print(f"Remaining liquid: {state['liquid_volume']}")

    except Exception as e:
        logging.error(f"Error: {e}")
