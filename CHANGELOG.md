# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Added | Changed | Deprecated | Removed | Fixed -->
## [0.2.0] - 2025-08-13

### Added

- Asynchronous programming with `asyncio`.
- Hierarchical Finite State Machine for automatic WLAN interface state management.
- Namespace package layout & structure for development in a Python context.

### Removed

- Namespace package layout & structure for development in a Python context.
  - Package now focuses on WLAN interface management.

## [0.1.0] - 2025-06-25

### Added

- Core WLAN interface:
  - Network environment variable class for credential configuration of client (STA) & access point (AP) modes.
  - Reset interface to AP if WiFi connection in STA mode is unsuccessful.
  - Helper functions for activating, deactivating, connecting interfaces & checking connection status.
  - Timeouts for network operations to handle hardware-specific quirks.
- Unit tests for `networkutils` core package.
  - Unit tests for core interface.
  - Integration tests for a connected device running MicroPython.
  - Skip integration tests, if no `SerialTransport` is made.
- Hatch custom build hook for `mpy-cross` compilation.
- Namespace package layout & structure for development in a Python context.
