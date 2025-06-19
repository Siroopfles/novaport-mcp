"""Tests voor schema modules voor volledige coverage."""

import pytest
from pydantic import ValidationError

from src.novaport_mcp.schemas.error import MCPError


class TestMCPErrorSchema:
    """Test MCPError schema class."""

    def test_mcp_error_basic_creation(self):
        """Test basic MCPError creation."""
        error = MCPError(error="Test error message")
        
        assert error.error == "Test error message"
        assert error.details is None

    def test_mcp_error_with_details(self):
        """Test MCPError creation with details."""
        details = {"code": 500, "additional_info": "Server error"}
        error = MCPError(error="Internal server error", details=details)
        
        assert error.error == "Internal server error"
        assert error.details == details

    def test_mcp_error_with_string_details(self):
        """Test MCPError with string details."""
        error = MCPError(error="Validation failed", details="Invalid input format")
        
        assert error.error == "Validation failed"
        assert error.details == "Invalid input format"

    def test_mcp_error_with_none_details_explicit(self):
        """Test MCPError with explicitly set None details."""
        error = MCPError(error="No additional details", details=None)
        
        assert error.error == "No additional details"
        assert error.details is None

    def test_mcp_error_with_complex_details(self):
        """Test MCPError with complex details object."""
        complex_details = {
            "error_code": "VALIDATION_ERROR",
            "field_errors": [
                {"field": "email", "message": "Invalid email format"},
                {"field": "age", "message": "Must be a positive integer"}
            ],
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        error = MCPError(error="Multiple validation errors", details=complex_details)
        
        assert error.error == "Multiple validation errors"
        assert error.details == complex_details
        assert error.details is not None
        assert error.details["error_code"] == "VALIDATION_ERROR"
        assert len(error.details["field_errors"]) == 2

    def test_mcp_error_required_field_validation(self):
        """Test that error field is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPError.model_validate({})  # Missing required 'error' field
        
        assert "error" in str(exc_info.value)

    def test_mcp_error_empty_string_error(self):
        """Test MCPError with empty string error."""
        error = MCPError(error="")
        
        assert error.error == ""
        assert error.details is None

    def test_mcp_error_serialization(self):
        """Test MCPError serialization to dict."""
        error = MCPError(error="Test error", details={"key": "value"})
        
        error_dict = error.model_dump()
        
        assert error_dict == {
            "error": "Test error",
            "details": {"key": "value"}
        }

    def test_mcp_error_json_serialization(self):
        """Test MCPError JSON serialization."""
        error = MCPError(error="JSON test", details={"nested": {"data": "value"}})
        
        json_str = error.model_dump_json()
        
        assert '"error":"JSON test"' in json_str
        assert '"nested":{"data":"value"}' in json_str

    def test_mcp_error_from_dict(self):
        """Test creating MCPError from dictionary."""
        error_data = {
            "error": "Created from dict",
            "details": {"source": "dictionary"}
        }
        
        error = MCPError.model_validate(error_data)
        
        assert error.error == "Created from dict"
        assert error.details == {"source": "dictionary"}

    def test_mcp_error_model_fields(self):
        """Test MCPError model fields configuration."""
        # Test that the model has the expected fields
        error = MCPError(error="Field test")
        
        # Check model fields exist
        model_fields = error.model_fields
        assert "error" in model_fields
        assert "details" in model_fields
        
        # Check field types/annotations
        assert model_fields["error"].annotation == str
        # details field should allow Any type with Optional

    def test_mcp_error_repr(self):
        """Test MCPError string representation."""
        error = MCPError(error="Repr test", details="test details")
        
        repr_str = repr(error)
        
        assert "MCPError" in repr_str
        assert "error='Repr test'" in repr_str
        assert "details='test details'" in repr_str

    def test_mcp_error_equality(self):
        """Test MCPError equality comparison."""
        error1 = MCPError(error="Same error", details={"key": "value"})
        error2 = MCPError(error="Same error", details={"key": "value"})
        error3 = MCPError(error="Different error", details={"key": "value"})
        
        assert error1 == error2
        assert error1 != error3

    def test_mcp_error_with_list_details(self):
        """Test MCPError with list details."""
        list_details = ["error1", "error2", "error3"]
        error = MCPError(error="Multiple errors", details=list_details)
        
        assert error.error == "Multiple errors"
        assert error.details == list_details
        assert error.details is not None
        assert len(error.details) == 3

    def test_mcp_error_with_numeric_details(self):
        """Test MCPError with numeric details."""
        error = MCPError(error="Numeric error", details=404)
        
        assert error.error == "Numeric error"
        assert error.details == 404
        assert isinstance(error.details, int)

    def test_mcp_error_with_boolean_details(self):
        """Test MCPError with boolean details."""
        error = MCPError(error="Boolean error", details=True)
        
        assert error.error == "Boolean error"
        assert error.details is True
        assert isinstance(error.details, bool)