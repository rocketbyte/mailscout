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


def test_extraction_rule_content_type():
    """Test extraction using different content types."""
    # Test text-only extraction
    text_rule = DataExtractionRule(
        name="amount",
        pattern=r"Amount: \$([\d,.]+)",
        content_type="text"
    )
    
    text = "Transaction details:\nAmount: $1,234.56\nDate: 2025-03-29"
    html = "<div>Transaction details:<br>Amount: $9,876.54<br>Date: 2025-03-29</div>"
    
    # Should extract from text only
    result = text_rule.extract_data(text, html)
    assert result == "1,234.56"
    
    # Test html-only extraction
    html_rule = DataExtractionRule(
        name="amount",
        pattern=r"Amount: \$([\d,.]+)",
        content_type="html"
    )
    
    # Should extract from HTML only
    result = html_rule.extract_data(text, html)
    assert result == "9,876.54"
    
    # Test both content types (prioritizes first match)
    both_rule = DataExtractionRule(
        name="amount",
        pattern=r"Amount: \$([\d,.]+)",
        content_type="both"
    )
    
    # Should extract from text first (first in the search order)
    result = both_rule.extract_data(text, html)
    assert result == "1,234.56"
    
    # If text doesn't have the pattern, should fall back to HTML
    text_no_match = "Transaction details:\nTotal: $1,234.56\nDate: 2025-03-29"
    result = both_rule.extract_data(text_no_match, html)
    assert result == "9,876.54"


def test_table_extraction():
    """Test extraction from HTML tables."""
    html = """
    <table cellpadding="0" cellspacing="0" style="width: 100%">
    <tbody>
    <tr>
    <td class="ic-form-label" style="width: 20%">Transacción: </td>
    <td class="ic-form-data">Transferencia a Tercero </td>
    </tr>
    <tr>
    <td class="ic-form-label">Origen: </td>
    <td class="ic-form-data">STARLIN FRANCISCO GIL CRUZ, CuentaAhorro DOP ** - 0129 </td>
    </tr>
    <tr>
    <td class="ic-form-label">Destino: </td>
    <td class="ic-form-data">SRA ROSA A FELIZ, CuentaAhorro DOP ** - 5770 </td>
    </tr>
    <tr>
    <td class="ic-form-label">Monto: </td>
    <td class="ic-form-data">DOP 10,000.00 </td>
    </tr>
    <tr style="display:table row;">
    <td class="ic-form-label">Comisión: </td>
    <td class="ic-form-data">DOP 25.00 </td>
    </tr>
    <tr style="display:table row;">
    <td class="ic-form-label">Impuestos: </td>
    <td class="ic-form-data">DOP 15.00 </td>
    </tr>
    <tr>
    <td class="ic-form-label">Fecha/Hora: </td>
    <td class="ic-form-data">24 de Marzo 2025 - 04:26 PM </td>
    </tr>
    <tr>
    <td class="ic-form-label">Numero de referencia: </td>
    <td class="ic-form-data">239019074182 </td>
    </tr>
    </tbody>
    </table>
    """
    
    # Test table extraction for transaction type
    transaction_rule = DataExtractionRule(
        name="tipo_transaccion",
        pattern="^(.+?)\\s*$",
        content_type="table",
        table_label="Transacción"
    )
    result = transaction_rule.extract_data("", html)
    assert result == "Transferencia a Tercero"
    
    # Test table extraction with pattern for amount
    amount_rule = DataExtractionRule(
        name="monto",
        pattern="DOP\\s+([\\d,.]+)",
        content_type="table",
        table_label="Monto"
    )
    result = amount_rule.extract_data("", html)
    # Either extract the pattern or get the full value
    assert "10,000.00" in result
    
    # Test table extraction for reference number
    ref_rule = DataExtractionRule(
        name="numero_referencia",
        pattern="^(\\d+)\\s*$",
        content_type="table",
        table_label="Numero de referencia"
    )
    result = ref_rule.extract_data("", html)
    assert result == "239019074182"


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