# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Stiebel Eltron Servicewelt, providing cloud polling integration to monitor heating system data. The integration follows the standard Home Assistant custom component architecture with a coordinator pattern for data fetching.

## Development Commands

Tasks are defined in `mise.toml` and run via [mise](https://mise.jdx.dev/).

### Setup
```bash
mise run setup
```
Installs project dependencies via uv.

### Development Server
```bash
mise run develop
```
Starts a local Home Assistant instance with the integration loaded for testing. Uses `config/` directory for HA configuration.

### Tests
```bash
mise run test       # unit tests
mise run test-e2e   # HA + fake portal in Docker, see CONTRIBUTING.md
```

### Linting
```bash
mise run lint
```
Runs ruff formatter and linter with auto-fix.

## Architecture

### Core Components
- **API Client** (`api.py`): Handles authentication and data fetching from Servicewelt API
- **Coordinator** (`coordinator.py`): Manages periodic data updates using Home Assistant's DataUpdateCoordinator
- **Config Flow** (`config_flow.py`): Handles UI-based configuration with username/password
- **Data Models** (`data.py`): Type definitions for configuration and runtime data
- **Entity Base** (`entity.py`): Base entity class for all Servicewelt entities

### Platform Support
- **Sensors** (`sensor.py`): Numeric data entities
- **Binary Sensors** (`binary_sensor.py`): On/off state entities  

### Configuration
- Update interval: 10 seconds (defined in `async_setup_entry` in `__init__.py`)
- Domain: `servicewelt` 
- IoT Class: `cloud_polling`
- Config flow enabled for UI setup

### Dependencies
- Python 3.13+
- mise for tool/task management, uv for dependency management
- Ruff for code formatting and linting
- colorlog for enhanced logging