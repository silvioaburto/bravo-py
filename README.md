Python driver with lower level commands control to Bravo liquid handler. These are the same commands called by VWorks, except you can now call individually as opposed to having to execute VWorks .pro file.

## Installation

```bash
pip install pybravo
```

## Requirements

- Python > 3.9, 32 bits
- Must run with administrator privileges!

## Basic Use

```
with BravoDriver(profile="bravo") as driver:

        #Aspirate from location 1
        driver.aspirate(
            volume=100,
            plate_location=1,
            distance_from_well_bottom=2.0,
            pre_aspirate_volume=10.0,
            post_aspirate_volume=5.0,
            retract_distance_per_microliter=0.1,
        )

        
        #Dispense into location 2 
        driver.dispense(
                volume=100,
                plate_location=1,
                distance_from_well_bottom=2.0,
                pre_dispense_volume=10.0,
                post_dispense_volume=5.0,
                retract_distance_per_microliter=0.1,
            )

```
