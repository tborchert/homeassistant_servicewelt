#!/usr/bin/env python3
"""Standalone integration test script to verify HTML parsing works."""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup


class StandaloneServiceweltParser:
    """Standalone version of the Servicewelt HTML parser for testing."""
    
    def parse_html_data(self, html: str) -> dict:
        """Parse HTML and extract sensor data."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        tables = soup.find_all('table', class_='info')
        
        for table in tables:
            header = table.find('th')
            if not header:
                continue
                
            category = header.get_text(strip=True)
            category_data = {}
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) != 2:
                    continue
                    
                key = cells[0].get_text(strip=True)
                value_cell = cells[1]
                
                # Check for image (binary state)
                img = value_cell.find('img')
                if img:
                    # Extract state from image filename
                    src = img.get('src', '')
                    value = 'on' if 'symbol_an' in src else 'off'
                else:
                    value = value_cell.get_text(strip=True)
                    # Parse numeric values and units
                    value = self.parse_value(value)
                
                category_data[key] = value
            
            if category_data:
                data[category] = category_data
                
        return data

    def parse_value(self, value: str):
        """Parse and convert values to appropriate types."""
        if not value or value == '':
            return None
            
        # Remove common separators and normalize
        value = value.replace(',', '.')
        
        # Try to extract numeric value with unit
        match = re.match(r'^(-?\d+(?:\.\d+)?)\s*([A-Za-z%°]+)?', value)
        if match:
            num_str, unit = match.groups()
            try:
                num_value = float(num_str)
                if unit:
                    return {"value": num_value, "unit": unit}
                else:
                    return num_value
            except ValueError:
                pass
                
        return value


def test_integration():
    """Test the integration end-to-end with sample HTML files."""
    print("🔧 Testing Servicewelt Integration (Standalone)")
    print("=" * 50)
    
    # Create parser
    parser = StandaloneServiceweltParser()
    
    # Load sample HTML files
    repo_root = Path(__file__).parent
    sample_dir = repo_root / "sample_pages"
    files = {
        "s_1_0.html": "system",
        "s_1_1.html": "heat_pump",
        "s_1_8.html": "energy_footprint", 
        "s_2_0.html": "system_status",
        "s_2_2.html": "heat_pump_status",
    }
    
    parsed_data = {}
    
    print("📄 Parsing HTML sample files...")
    for filename, page_name in files.items():
        filepath = sample_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                html = f.read()
                parsed_data[page_name] = parser.parse_html_data(html)
                print(f"  ✓ {page_name}: {len(parsed_data[page_name])} categories")
        else:
            print(f"  ✗ {filename}: File not found")
    
    print(f"\n📊 Total parsed data: {len(parsed_data)} pages")
    
    # Test sensor value extraction
    print("\n🌡️  Testing Temperature Sensors:")
    temp_sensors = [
        ("outside_temperature", ("system", "HEATING", "OUTSIDE TEMPERATURE")),
        ("dhw_actual_temperature", ("system", "DHW", "ACTUAL TEMPERATURE")),
        ("return_temperature", ("heat_pump", "PROCESS DATA", "RETURN TEMPERATURE")),
        ("hot_gas_temperature", ("heat_pump", "PROCESS DATA", "HOT GAS TEMPERATURE")),
    ]
    
    temp_count = 0
    for sensor_name, (page, category, field) in temp_sensors:
        try:
            value = parsed_data[page][category][field]
            if isinstance(value, dict) and "value" in value:
                print(f"  ✓ {sensor_name}: {value['value']}°C")
                temp_count += 1
            else:
                print(f"  ✗ {sensor_name}: Invalid value format")
        except KeyError:
            print(f"  ✗ {sensor_name}: Not found")
    
    print("\n⚡ Testing Electrical Sensors:")
    electrical_sensors = [
        ("inverter_power", ("heat_pump", "PROCESS DATA", "INVERTER POWER")),
        ("inverter_current", ("heat_pump", "PROCESS DATA", "INVERTER CURRENT")),
        ("low_pressure", ("heat_pump", "PROCESS DATA", "LOW PRESSURE")),
        ("fan_rate", ("heat_pump", "PROCESS DATA", "REL FAN RATE")),
    ]
    
    electrical_count = 0
    for sensor_name, (page, category, field) in electrical_sensors:
        try:
            value = parsed_data[page][category][field]
            if isinstance(value, dict) and "value" in value:
                print(f"  ✓ {sensor_name}: {value['value']} {value['unit']}")
                electrical_count += 1
            else:
                print(f"  ✗ {sensor_name}: Invalid value format")
        except KeyError:
            print(f"  ✗ {sensor_name}: Not found")
    
    print("\n🔄 Testing Binary Sensors:")
    binary_sensors = [
        ("heating_circuit_pump", ("system_status", "OPERATING MODE", "HEATING CIRCUIT 1 PUMP")),
        ("compressor", ("system_status", "OPERATING MODE", "COMPRESSOR")),
        ("dhw_heating", ("system_status", "OPERATING MODE", "DHW HEATING")),
        ("summer_mode", ("system_status", "OPERATING MODE", "SUMMER MODE")),
    ]
    
    binary_count = 0
    for sensor_name, (page, category, field) in binary_sensors:
        try:
            value = parsed_data[page][category][field]
            status = "ON" if value == "on" else "OFF"
            print(f"  ✓ {sensor_name}: {status}")
            binary_count += 1
        except KeyError:
            print(f"  ✗ {sensor_name}: Not found")
    
    print("\n📈 Testing Energy Sensors:")
    energy_sensors = [
        ("heating_energy_day", ("heat_pump", "AMOUNT OF HEAT", "VD HEATING DAY")),
        ("heating_energy_total", ("heat_pump", "AMOUNT OF HEAT", "VD HEATING TOTAL")),
        ("dhw_energy_day", ("heat_pump", "AMOUNT OF HEAT", "VD DHW DAY")),
    ]
    
    energy_count = 0
    for sensor_name, (page, category, field) in energy_sensors:
        try:
            value = parsed_data[page][category][field]
            if isinstance(value, dict) and "value" in value:
                print(f"  ✓ {sensor_name}: {value['value']} {value['unit']}")
                energy_count += 1
            else:
                print(f"  ✗ {sensor_name}: Invalid value format")
        except KeyError:
            print(f"  ✗ {sensor_name}: Not found")
    
    # Detailed data exploration
    print(f"\n🔍 Detailed Data Analysis:")
    for page_name, page_data in parsed_data.items():
        print(f"\n📄 {page_name.upper()} PAGE:")
        for category, fields in page_data.items():
            print(f"  📁 {category} ({len(fields)} fields):")
            for field_name, field_value in fields.items():
                if isinstance(field_value, dict) and "value" in field_value:
                    print(f"    • {field_name}: {field_value['value']} {field_value['unit']}")
                else:
                    print(f"    • {field_name}: {field_value}")
    
    # Summary
    total_categories = sum(len(data) for data in parsed_data.values())
    total_fields = sum(len(category) for data in parsed_data.values() for category in data.values())
    
    print(f"\n✅ Integration Test Summary:")
    print(f"   • {len(parsed_data)} HTML pages parsed successfully")
    print(f"   • {total_categories} data categories extracted")
    print(f"   • {total_fields} sensor data points available")
    print(f"   • {temp_count} temperature sensors working")
    print(f"   • {electrical_count} electrical sensors working")
    print(f"   • {binary_count} binary sensors working")
    print(f"   • {energy_count} energy sensors working")
    
    success = all([
        len(parsed_data) >= 4,  # At least 4 pages parsed
        temp_count >= 3,        # At least 3 temperature sensors
        electrical_count >= 3,  # At least 3 electrical sensors
        binary_count >= 3,      # At least 3 binary sensors
        energy_count >= 2,      # At least 2 energy sensors
    ])
    
    if success:
        print("\n🎉 Integration test completed successfully!")
        print("   The HTML parsing and sensor mapping is working correctly.")
        print("   Ready for Home Assistant integration!")
    else:
        print("\n❌ Integration test failed!")
        print("   Some sensors are not working as expected.")
    
    return success


if __name__ == "__main__":
    test_integration()