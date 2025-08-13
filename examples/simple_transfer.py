import logging
from pybravo import BravoDriver

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        with BravoDriver(simulation_mode=True) as driver:

            driver.aspirate(100.0, plate_location=1)
            driver.dispense(50.0, plate_location=2)
            # Check simulation state
            state = driver.get_simulation_state()
            print(f"Remaining liquid: {state['liquid_volume']}")

            driver.dispense(
                volume=100,
                empty_tips=True,
                blow_out_volume=10.0,
                plate_location=2,
                distance_from_well_bottom=2.0,
                retract_distance_per_microliter=0.1,
            )
    except Exception as e:
        logging.error(f"Error: {e}")
