"""Test parsing with real sample HTML files."""

from __future__ import annotations

import os
import re
from bs4 import BeautifulSoup
import pytest


class TestRealSampleParsing:
    """Test the HTML parsing logic with real sample files."""

    def _parse_html_data(self, html: str) -> dict:
        """Parse HTML and extract sensor data (standalone version)."""
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
                    value = self._parse_value(value)
                
                category_data[key] = value
            
            if category_data:
                data[category] = category_data
                
        return data

    def _parse_value(self, value: str):
        """Parse and convert values to appropriate types (standalone version)."""
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

    @pytest.fixture
    def sample_files(self):
        """Load real sample HTML files."""
        sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_pages")
        files = {}
        
        file_mapping = {
            "s_1_0.html": "system",
            "s_1_1.html": "heat_pump",
            "s_1_8.html": "energy_footprint",
            "s_2_0.html": "system_status",
            "s_2_2.html": "heat_pump_status",
        }
        
        for filename, key in file_mapping.items():
            filepath = os.path.join(sample_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    files[key] = f.read()
        
        return files

    def test_system_page_real_data(self, sample_files):
        """Test parsing of real system page data."""
        if "system" not in sample_files:
            pytest.skip("System HTML sample not available")
            
        html = sample_files["system"]
        parsed_data = self._parse_html_data(html)
        
        # Should have heating data
        assert "HEATING" in parsed_data
        heating = parsed_data["HEATING"]
        
        # Check for expected temperature fields
        assert "OUTSIDE TEMPERATURE" in heating
        outside_temp = heating["OUTSIDE TEMPERATURE"]
        assert isinstance(outside_temp, dict)
        assert "value" in outside_temp
        assert "unit" in outside_temp
        assert outside_temp["unit"] == "°C"
        
        # Should have DHW data
        assert "DHW" in parsed_data
        dhw = parsed_data["DHW"]
        assert "ACTUAL TEMPERATURE" in dhw
        assert "SET TEMPERATURE" in dhw

    def test_heat_pump_page_real_data(self, sample_files):
        """Test parsing of real heat pump page data."""
        if "heat_pump" not in sample_files:
            pytest.skip("Heat pump HTML sample not available")
            
        html = sample_files["heat_pump"]
        parsed_data = self._parse_html_data(html)
        
        # Should have process data
        assert "PROCESS DATA" in parsed_data
        process_data = parsed_data["PROCESS DATA"]
        
        # Check for expected fields
        expected_fields = [
            "RETURN TEMPERATURE",
            "FLOW TEMPERATURE", 
            "OUTSIDE TEMPERATURE",
            "LOW PRESSURE",
            "HIGH PRESSURE",
            "INVERTER POWER",
        ]
        
        for field in expected_fields:
            if field in process_data:
                value = process_data[field]
                assert isinstance(value, dict)
                assert "value" in value
                assert "unit" in value
                assert isinstance(value["value"], (int, float))

    def test_system_status_page_real_data(self, sample_files):
        """Test parsing of real system status page data."""
        if "system_status" not in sample_files:
            pytest.skip("System status HTML sample not available")
            
        html = sample_files["system_status"]
        parsed_data = self._parse_html_data(html)
        
        # Should have operating mode data
        assert "OPERATING MODE" in parsed_data
        operating_mode = parsed_data["OPERATING MODE"]
        
        # Check for expected binary fields
        expected_fields = [
            "HEATING CIRCUIT 1 PUMP",
            "DHW HEATING",
            "COMPRESSOR",
            "SUMMER MODE",
        ]
        
        for field in expected_fields:
            if field in operating_mode:
                value = operating_mode[field]
                assert value in ["on", "off"]

    def test_energy_footprint_page_real_data(self, sample_files):
        """Test parsing of real energy footprint page data."""
        if "energy_footprint" not in sample_files:
            pytest.skip("Energy footprint HTML sample not available")
            
        html = sample_files["energy_footprint"]
        parsed_data = self._parse_html_data(html)
        
        # Should have energy-related data
        categories = parsed_data.keys()
        
        # Look for categories that might contain energy data
        energy_categories = [cat for cat in categories if 
                           "HEAT" in cat or "POWER" in cat or "EFFICIENCY" in cat]
        
        assert len(energy_categories) > 0, f"No energy categories found. Available: {list(categories)}"

    def test_heat_pump_status_page_real_data(self, sample_files):
        """Test parsing of real heat pump status page data."""
        if "heat_pump_status" not in sample_files:
            pytest.skip("Heat pump status HTML sample not available")
            
        html = sample_files["heat_pump_status"]
        parsed_data = self._parse_html_data(html)
        
        # Should have heat pump status data
        assert "HEAT PUMP STATUS" in parsed_data
        status_data = parsed_data["HEAT PUMP STATUS"]
        
        # Check for expected status fields
        if "COMPRESSOR" in status_data:
            assert status_data["COMPRESSOR"] in ["on", "off"]

    def test_all_samples_parse_without_errors(self, sample_files):
        """Test that all sample files can be parsed without errors."""
        for page_name, html_content in sample_files.items():
            try:
                parsed_data = self._parse_html_data(html_content)
                # Should return a dictionary
                assert isinstance(parsed_data, dict)
                print(f"✓ {page_name}: {len(parsed_data)} categories found")
                
                # Print summary of what was found
                for category, data in parsed_data.items():
                    print(f"  - {category}: {len(data)} fields")
                    
            except Exception as e:
                pytest.fail(f"Failed to parse {page_name}: {e}")

    def test_data_structure_consistency(self, sample_files):
        """Test that parsed data has consistent structure."""
        for page_name, html_content in sample_files.items():
            parsed_data = self._parse_html_data(html_content)
            
            for category, category_data in parsed_data.items():
                assert isinstance(category_data, dict), f"Category {category} should be dict"
                
                for field, value in category_data.items():
                    # Value should be either:
                    # 1. A dict with 'value' and 'unit' keys (for numeric data)
                    # 2. A string (for binary states or text)
                    # 3. A number (for plain numeric values)
                    # 4. None (for empty values)
                    
                    if isinstance(value, dict):
                        assert "value" in value, f"Numeric value missing 'value' key: {field} = {value}"
                        assert "unit" in value, f"Numeric value missing 'unit' key: {field} = {value}"
                        assert isinstance(value["value"], (int, float)), f"Value should be numeric: {field} = {value}"
                    elif value is not None:
                        assert isinstance(value, (str, int, float)), f"Invalid value type: {field} = {value} ({type(value)})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])