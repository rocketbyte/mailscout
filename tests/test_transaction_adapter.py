import unittest
from datetime import datetime
from src.models.email_data import EmailData, EmailContent, TransactionType
from src.services.filter_service import BanreservasTransactionAdapter, GenericTransactionAdapter


class TestGenericTransactionAdapter(unittest.TestCase):
    def setUp(self):
        # Create test adapter with owner identifiers
        self.adapter = GenericTransactionAdapter(owner_identifiers=["TEST USER", "ACCOUNT123"])
        
        # Create a sample email
        self.email = EmailData(
            message_id='test123',
            thread_id='thread123',
            subject='Transaction Receipt',
            from_email='bank@example.com',
            to_email=['user@example.com'],
            date=datetime.now(),
            content=EmailContent(
                html='''
                Transaction: Transfer to Third Party
                Origin: TEST USER, Savings Account USD ** - 1234
                Destination: JANE DOE, Checking Account USD ** - 5678
                Amount: USD 500.00
                '''
            )
        )
    
    def test_outgoing_transaction(self):
        """Test detection of outgoing transaction."""
        # Prepare test data
        extracted_data = {
            'origen': 'TEST USER, Savings Account USD ** - 1234',
            'destino': 'JANE DOE, Checking Account USD ** - 5678',
            'monto': '500.00'
        }
        
        # Process the data
        result = self.adapter.process(self.email, extracted_data)
        
        # Verify results
        self.assertIn('transaction_type', result)
        self.assertEqual(result['transaction_type'], TransactionType.OUTGOING.value)
    
    def test_incoming_transaction(self):
        """Test detection of incoming transaction."""
        # Prepare test data
        extracted_data = {
            'origen': 'JOHN SMITH, Checking Account USD ** - 9876',
            'destino': 'TEST USER, Savings Account USD ** - 1234',
            'monto': '750.00'
        }
        
        # Process the data
        result = self.adapter.process(self.email, extracted_data)
        
        # Verify results
        self.assertIn('transaction_type', result)
        self.assertEqual(result['transaction_type'], TransactionType.INCOMING.value)
    
    def test_unknown_transaction(self):
        """Test detection of unknown transaction type."""
        # Prepare test data with no recognizable owner identifiers
        extracted_data = {
            'origen': 'JOHN SMITH, Checking Account USD ** - 9876',
            'destino': 'JANE DOE, Savings Account USD ** - 5678',
            'monto': '250.00'
        }
        
        # Process the data
        result = self.adapter.process(self.email, extracted_data)
        
        # Verify results
        self.assertIn('transaction_type', result)
        self.assertEqual(result['transaction_type'], TransactionType.UNKNOWN.value)
    
    def test_missing_fields(self):
        """Test handling of missing required fields."""
        # Test with missing origen
        extracted_data = {
            'monto': '10,000.00'
        }
        
        result = self.adapter.process(self.email, extracted_data)
        
        # Should return original data unchanged
        self.assertEqual(result, extracted_data)
        self.assertNotIn('transaction_type', result)


class TestBanreservasTransactionAdapter(unittest.TestCase):
    def setUp(self):
        # Create test adapter
        self.adapter = BanreservasTransactionAdapter()
        
        # Create a sample email
        self.email = EmailData(
            message_id='test123',
            thread_id='thread123',
            subject='Recibo de la transacción',
            from_email='test@example.com',
            to_email=['recipient@example.com'],
            date=datetime.now(),
            content=EmailContent(
                html='''
                Transacción: Transferencia a Tercero
                Origen: STARLIN FRANCISCO GIL CRUZ, CuentaAhorro DOP ** - 0129
                Destino: SRA ROSA A FELIZ, CuentaAhorro DOP ** - 5770
                Monto: DOP 10,000.00
                '''
            )
        )
    
    def test_outgoing_transaction(self):
        """Test detection of outgoing transaction."""
        # Prepare test data
        extracted_data = {
            'origen': 'STARLIN FRANCISCO GIL CRUZ, CuentaAhorro DOP ** - 0129',
            'destino': 'SRA ROSA A FELIZ, CuentaAhorro DOP ** - 5770',
            'monto': '10,000.00'
        }
        
        # Process the data
        result = self.adapter.process(self.email, extracted_data)
        
        # Verify results
        self.assertIn('transaction_type', result)
        self.assertEqual(result['transaction_type'], TransactionType.OUTGOING.value)
    
    def test_incoming_transaction(self):
        """Test detection of incoming transaction."""
        # Prepare test data
        extracted_data = {
            'origen': 'JUAN PEREZ, CuentaAhorro DOP ** - 0129',
            'destino': 'STARLIN FRANCISCO GIL CRUZ, CuentaAhorro DOP ** - 5770',
            'monto': '5,000.00'
        }
        
        # Process the data
        result = self.adapter.process(self.email, extracted_data)
        
        # Verify results
        self.assertIn('transaction_type', result)
        self.assertEqual(result['transaction_type'], TransactionType.INCOMING.value)


if __name__ == '__main__':
    unittest.main()