import logging
from pybravo import BravoDriver

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        with BravoDriver(profile="bravo") as driver:
            driver.aspirate(
                volume=100,
                plate_location=1,
                distance_from_well_bottom=2.0,
                pre_aspirate_volume=10.0,
                post_aspirate_volume=5.0,
                retract_distance_per_microliter=0.1,
            )

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
