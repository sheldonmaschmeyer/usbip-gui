# Combine Remote and Attached Device Lists

## 🚀 Overview
This PR simplifies the user interface in the Client Tab by combining the formerly separate "Remote Devices" and "Attached Devices" lists into a single, unified list. This provides a more streamlined, intuitive experience for managing USBIP devices. 

## 📝 Changes
- **Unified List View:** Merged the Remote and Attached lists into one cohesive table.
- **New Columns:** Added `Host`, `Port`, and `State` columns to the list to display comprehensive connection info.
- **Dynamic State:** Devices now dynamically show their state as either `Attached` or `Detached`.
- **Streamlined Toolbar:** Moved the "Detach Device" button next to the "Attach Device" button on the main toolbar and completely removed the redundant "Attached Devices" UI section.
- **Smart Double-Click Action:** Double-clicking a device now contextually determines whether to "Attach" or "Detach" based on the current state of the device.
- **Label Updates:** Renamed "Remote Bus ID" to simply "Bus ID".
- **Translations:** Added new strings for `Attached` / `Detached` and updated the French (`fr_CA`) localization (`.po` and `.mo` files) with the appropriate terms (*Attaché* / *Détaché*).
- **Test Coverage (100%):** 
  - Refactored `tests/test_client.py` to accommodate the removed UI components and updated the `SortableTreeWidgetItem` mock signatures.
  - Added new test cases to cover the new state-based logic (e.g., trying to attach an already attached device), restoring the `client.py` file coverage to a perfect 100%.

## 🧪 Testing
- Verified visually that remote devices seamlessly merge with locally attached devices into the unified widget.
- Double-clicking works for both connecting and disconnecting.
- Passed the `pixi run lint` suite completely with no warnings.
- Ran `pytest` suite via `pixi run test`; all 105 tests are passing cleanly. 

## 🖼️ Impact
This major UI refactor makes the app significantly cleaner and prevents the user from needing to visually context-switch between two different panes just to manage their USB connections.
