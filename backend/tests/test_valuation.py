import pytest
import numpy as np
from service_layer import service


class TestParseNumericFromDfValue:
    def test_handles_numpy_int64(self):
        """Test that numpy.int64 values are parsed correctly."""
        value = np.int64(36269000000)
        result = service._parse_numeric_from_df_value(value)
        assert result == 36269000000.0

    def test_handles_regular_int(self):
        """Test that regular int values are parsed correctly."""
        value = 36269000000
        result = service._parse_numeric_from_df_value(value)
        assert result == 36269000000.0

    def test_handles_float(self):
        """Test that float values are parsed correctly."""
        value = 36269000000.5
        result = service._parse_numeric_from_df_value(value)
        assert result == 36269000000.5

    def test_handles_string_numbers(self):
        """Test that string numbers are parsed correctly."""
        value = "36269000000"
        result = service._parse_numeric_from_df_value(value)
        assert result == 36269000000.0

    def test_handles_formatted_strings(self):
        """Test that formatted string numbers are parsed correctly."""
        value = "$36,269,000,000"
        result = service._parse_numeric_from_df_value(value)
        assert result == 36269000000.0

    def test_handles_none(self):
        """Test that None values return None."""
        value = None
        result = service._parse_numeric_from_df_value(value)
        assert result is None

    def test_handles_empty_string(self):
        """Test that empty strings return None."""
        value = ""
        result = service._parse_numeric_from_df_value(value)
        assert result is None

    def test_handles_dash(self):
        """Test that dash strings return None."""
        value = "-"
        result = service._parse_numeric_from_df_value(value)
        assert result is None
