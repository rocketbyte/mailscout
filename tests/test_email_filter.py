import pytest
from src.models.email_filter import EmailFilter, DataExtractionRule


def test_email_filter_creation():
    """Test creating an EmailFilter object."""
    filter_obj = EmailFilter(
        name="Test Filter",
        subject_patterns=["Test Subject"],
        from_patterns=["test@example.com"],
        content_patterns=["Test Content"]
    )
    
    assert filter_obj.name == "Test Filter"
    assert filter_obj.subject_patterns == ["Test Subject"]
    assert filter_obj.from_patterns == ["test@example.com"]
    assert filter_obj.content_patterns == ["Test Content"]
    assert filter_obj.is_active is True
    assert filter_obj.extraction_rules == []


def test_data_extraction_rule():
    """Test the DataExtractionRule functionality."""
    rule = DataExtractionRule(
        name="order_number",
        pattern=r"Order #: (\d+)"
    )
    
    # Test extraction
    text = "Your order has been confirmed. Order #: 12345 will ship tomorrow."
    extracted = rule.extract_data(text)
    assert extracted == "12345"
    
    # Test no match
    text = "Your order has been confirmed."
    extracted = rule.extract_data(text)
    assert extracted is None
    
    # Test with named group
    rule = DataExtractionRule(
        name="total_amount",
        pattern=r"Total: \$(?P<amount>\d+\.\d+)",
        group_name="amount"
    )
    
    text = "Order summary: Total: $123.45"
    extracted = rule.extract_data(text)
    assert extracted == "123.45"


def test_filter_with_extraction_rules():
    """Test EmailFilter with extraction rules."""
    extraction_rules = [
        DataExtractionRule(
            name="order_number",
            pattern=r"Order #: (\d+)"
        ),
        DataExtractionRule(
            name="total_amount",
            pattern=r"Total: \$(\d+\.\d+)"
        )
    ]
    
    filter_obj = EmailFilter(
        name="Order Confirmation",
        subject_patterns=["Order Confirmation"],
        from_patterns=["orders@example.com"],
        extraction_rules=extraction_rules
    )
    
    assert len(filter_obj.extraction_rules) == 2
    assert filter_obj.extraction_rules[0].name == "order_number"
    assert filter_obj.extraction_rules[1].name == "total_amount"