"""
Script to export all Velocity11 labware registry data
"""

import winreg
import json
from datetime import datetime


def export_all_labware_data():
    """Export all labware registry data to a text file"""
    base_path = r"SOFTWARE\WOW6432Node\Velocity11\Shared\Labware\Labware_Entries"
    output_file = (
        f"labware_registry_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, base_path, 0, winreg.KEY_READ
        ) as base_key:
            with open(output_file, "w") as f:
                f.write("VELOCITY11 LABWARE REGISTRY EXPORT\n")
                f.write("=" * 50 + "\n\n")

                # Enumerate all labware entries
                i = 0
                while True:
                    try:
                        entry_name = winreg.EnumKey(base_key, i)
                        f.write(f"ENTRY: {entry_name}\n")
                        f.write("-" * 30 + "\n")

                        # Open the specific entry
                        entry_path = f"{base_path}\\{entry_name}"
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE, entry_path, 0, winreg.KEY_READ
                        ) as entry_key:
                            # Enumerate all values in this entry
                            j = 0
                            while True:
                                try:
                                    name, value, reg_type = winreg.EnumValue(
                                        entry_key, j
                                    )
                                    type_str = {
                                        winreg.REG_SZ: "REG_SZ",
                                        winreg.REG_DWORD: "REG_DWORD",
                                        winreg.REG_BINARY: "REG_BINARY",
                                    }.get(reg_type, f"REG_TYPE_{reg_type}")

                                    f.write(f"  {name}: {value} ({type_str})\n")
                                    j += 1
                                except WindowsError:
                                    break

                        f.write("\n")
                        i += 1
                    except WindowsError:
                        break

        print(f"Registry data exported to: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error exporting registry data: {e}")
        return None


def export_to_json():
    """Export all labware data to JSON format"""
    base_path = r"SOFTWARE\WOW6432Node\Velocity11\Shared\Labware\Labware_Entries"
    output_file = (
        f"labware_registry_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    all_data = {}

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, base_path, 0, winreg.KEY_READ
        ) as base_key:
            # Enumerate all labware entries
            i = 0
            while True:
                try:
                    entry_name = winreg.EnumKey(base_key, i)
                    entry_data = {}

                    # Open the specific entry
                    entry_path = f"{base_path}\\{entry_name}"
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, entry_path, 0, winreg.KEY_READ
                    ) as entry_key:
                        # Enumerate all values in this entry
                        j = 0
                        while True:
                            try:
                                name, value, reg_type = winreg.EnumValue(entry_key, j)
                                entry_data[name] = value
                                j += 1
                            except WindowsError:
                                break

                    all_data[entry_name] = entry_data
                    i += 1
                except WindowsError:
                    break

        with open(output_file, "w") as f:
            json.dump(all_data, f, indent=2, default=str)

        print(f"Registry data exported to JSON: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error exporting to JSON: {e}")
        return None


if __name__ == "__main__":
    print("Exporting Velocity11 labware registry data...")

    # Export as text
    text_file = export_all_labware_data()

    # Export as JSON
    json_file = export_to_json()

    print("\nExport complete! Please share one of these files:")
    if text_file:
        print(f"  Text format: {text_file}")
    if json_file:
        print(f"  JSON format: {json_file}")
