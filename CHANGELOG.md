# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Added | Changed | Deprecated | Removed | Fixed -->
## [0.1.0] - 2025-06-05

### Added

- Network environment variables class for credential configuration client (STA) & access point (AP) modes.
- Reset interface to AP if WiFi connection in STA mode is unsuccessful.
- Helper functions for activating, deactivating, connecting interfaces & checking connection status.
- Timeouts for network operations to handle hardware-specific quirks.
- Unit tests for `network-utils` core package.
