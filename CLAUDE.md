# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Stiebel Eltron Servicewelt, providing cloud polling integration to monitor heating system data. The integration follows the standard Home Assistant custom component architecture with a coordinator pattern for data fetching.

## Development Commands

### Setup
```bash
./scripts/setup
```
Installs Poetry and project dependencies.

### Development Server
```bash
./scripts/develop
```
Starts a local Home Assistant instance with the integration loaded for testing. Uses `config/` directory for HA configuration.

### Linting
```bash
./scripts/lint
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
- **Switches** (`switch.py`): Controllable on/off entities

### Configuration
- Update interval: 10 seconds (defined in `__init__.py:44`)
- Domain: `servicewelt` 
- IoT Class: `cloud_polling`
- Config flow enabled for UI setup

### Dependencies
- Python 3.13+
- Poetry for dependency management
- Ruff for code formatting and linting
- colorlog for enhanced logging