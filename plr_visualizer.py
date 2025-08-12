from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import ChatterBoxBackend
from pylabrobot.visualizer.visualizer import Visualizer
import asyncio
from pylabrobot.resources.hamilton import STARLetDeck


async def main():
    # Create liquid handler with chatterbox backend and STARLet deck
    lh = LiquidHandler(backend=ChatterBoxBackend(), deck=STARLetDeck())

    # Setup the liquid handler
    await lh.setup()

    # Create and setup visualizer
    vis = Visualizer(resource=lh)
    await vis.setup()

    # Keep the visualizer running - you can add your liquid handling operations here
    print("Visualizer is running. Press Ctrl+C to exit.")
    try:
        # You can add your liquid handling operations here
        # For example:
        # await lh.pick_up_tips(...)
        # await lh.aspirate(...)
        # await lh.dispense(...)

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up
        await vis.stop()
        await lh.stop()


if __name__ == "__main__":
    asyncio.run(main())
