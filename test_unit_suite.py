import unittest
import sys
import os
import numpy as np

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app_helpers import (
    calculate_statistical_metrics,
    check_data_sufficiency,
    extract_recommendation_template,
    extract_comparison_template,
    extract_statistical_template,
    extract_synthesis_template
)
from constants import MIN_DATA_REQUIREMENTS, INSUFFICIENT_DATA_MESSAGES

class TestAppHelpers(unittest.TestCase):
    """Unit tests for functions in app_helpers.py"""

    def test_calculate_statistical_metrics(self):
        print("\n--- Testing calculate_statistical_metrics ---")
        values = np.array([10, 20, 30, 40, 50])

        # Test 'all' metrics
        all_stats = calculate_statistical_metrics(values, "all")
        self.assertEqual(all_stats['mean'], 30.0)
        self.assertEqual(all_stats['median'], 30.0)
        self.assertEqual(all_stats['min'], 10.0)
        self.assertEqual(all_stats['max'], 50.0)
        self.assertEqual(all_stats['records_analyzed'], 5)
        print("`all` metrics test passed.")

        # Test single metric
        median_stat = calculate_statistical_metrics(values, "median")
        self.assertEqual(median_stat['value'], 30.0)
        print("Single metric 'median' test passed.")

        # Test empty input
        empty_stat = calculate_statistical_metrics(np.array([]))
        self.assertIn("error", empty_stat)
        print("Empty input test passed.")

    def test_check_data_sufficiency(self):
        print("\n--- Testing check_data_sufficiency ---")

        # Test sufficient data
        sufficient_data = {'vendors': [1, 2, 3]}
        is_sufficient, msg = check_data_sufficiency(sufficient_data, 'comparison')
        self.assertTrue(is_sufficient)
        self.assertEqual(msg, "")
        print("Sufficient data test passed.")

        # Test insufficient data
        insufficient_data = {'vendors': [1]}
        is_sufficient, msg = check_data_sufficiency(insufficient_data, 'comparison')
        expected_msg = INSUFFICIENT_DATA_MESSAGES['insufficient_vendors'].format(
            required=MIN_DATA_REQUIREMENTS['comparison'],
            found=1
        )
        self.assertFalse(is_sufficient)
        self.assertEqual(msg, expected_msg)
        print("Insufficient data test passed.")

class TestResponseParsers(unittest.TestCase):
    """Unit tests for LLM response parsing functions."""

    def test_extract_recommendation_template(self):
        print("\n--- Testing extract_recommendation_template ---")
        mock_llm_response = """
        <RECOMMENDATIONS_START>
        <REC1>
        <ACTION>Consolidate vendors for office supplies.</ACTION>
        <JUSTIFICATION>High number of vendors with low spending per vendor.</JUSTIFICATION>
        <PRIORITY>HIGH</PRIORITY>
        </REC1>
        </RECOMMENDATIONS_START>
        """
        expected_output = "Strategic Recommendations:\n\n1. Consolidate vendors for office supplies. (Priority: HIGH)\n   Justification: High number of vendors with low spending per vendor."
        actual_output = extract_recommendation_template(mock_llm_response)
        self.assertEqual(expected_output.strip(), actual_output.strip())
        print("Test Passed.")

    def test_extract_comparison_template(self):
        print("\n--- Testing extract_comparison_template ---")
        mock_llm_response = """
        <COMPARISON_START>
        <SUMMARY>DELL INC has higher total spending.</SUMMARY>
        <VENDOR1><NAME>DELL INC</NAME><PERFORMANCE>Total spending: $1500.00</PERFORMANCE></VENDOR1>
        </COMPARISON_START>
        """
        expected_output = "Summary: DELL INC has higher total spending.\n\n**DELL INC**\nPerformance: Total spending: $1500.00\nStrengths: Not specified\nConcerns: None identified\n"
        actual_output = extract_comparison_template(mock_llm_response)
        self.assertEqual(expected_output.strip(), actual_output.strip())
        print("Test Passed.")

    def test_extract_statistical_template(self):
        print("\n--- Testing extract_statistical_template ---")
        mock_llm_response = """
        <STATISTICAL_ANALYSIS>
        <SUMMARY>Stable spending.</SUMMARY>
        <FINDING1>Median is close to the mean.</FINDING1>
        </STATISTICAL_ANALYSIS>
        """
        expected_output = "Summary: Stable spending.\n\nKey Findings:\n1. Median is close to the mean."
        actual_output = extract_statistical_template(mock_llm_response)
        self.assertEqual(expected_output.strip(), actual_output.strip())
        print("Test Passed.")

    def test_extract_synthesis_template(self):
        print("\n--- Testing extract_synthesis_template ---")
        mock_llm_response = "<RESPONSE_START><ANSWER>Total spending was $1.2M.</ANSWER></RESPONSE_START>"
        expected_output = "Total spending was $1.2M."
        actual_output = extract_synthesis_template(mock_llm_response)
        self.assertEqual(expected_output.strip(), actual_output.strip())
        print("Test Passed.")


import sqlite3
from hybrid_rag_architecture import VendorResolver
from constants import KNOWN_VENDOR_MAPPINGS

class TestVendorResolver(unittest.TestCase):
    """Unit tests for the VendorResolver class."""

    @classmethod
    def setUpClass(cls):
        """Set up an in-memory SQLite database for testing."""
        print("\n--- Setting up TestVendorResolver ---")
        cls.conn = sqlite3.connect(':memory:')
        cursor = cls.conn.cursor()
        cursor.execute("CREATE TABLE procurement (VENDOR_NAME_1 TEXT)")

        # Populate with sample data
        cls.sample_vendors = [
            ("DELL INC",),
            ("INTERNATIONAL BUSINESS MACHINES",),
            ("Microsoft Corporation",), # Note the different case
            ("ORACLE AMERICA, INC.",)
        ]
        cursor.executemany("INSERT INTO procurement (VENDOR_NAME_1) VALUES (?)", cls.sample_vendors)
        cls.conn.commit()

        # Instantiate the resolver with the test database
        cls.vendor_resolver = VendorResolver(db_connection=cls.conn, known_mappings=KNOWN_VENDOR_MAPPINGS)
        print("Setup complete.")

    @classmethod
    def tearDownClass(cls):
        """Close the database connection."""
        print("\n--- Tearing down TestVendorResolver ---")
        cls.conn.close()
        print("Teardown complete.")

    def test_exact_match(self):
        print("Testing: VendorResolver exact_match")
        resolved = self.vendor_resolver.resolve("DELL INC")
        self.assertEqual(resolved, ["DELL INC"])
        print("Test Passed.")

    def test_known_mappings_match(self):
        print("Testing: VendorResolver known_mappings_match")
        # Test a common alias
        resolved = self.vendor_resolver.resolve("IBM")
        self.assertEqual(resolved, ["INTERNATIONAL BUSINESS MACHINES"])
        print("Test Passed.")

    def test_normalized_match(self):
        print("Testing: VendorResolver normalized_match")
        # Test with different casing and punctuation
        resolved = self.vendor_resolver.resolve("microsoft corp")
        self.assertEqual(resolved, ["Microsoft Corporation"])
        print("Test Passed.")

    def test_fuzzy_match(self):
        print("Testing: VendorResolver fuzzy_match")
        # Test a slightly misspelled name
        resolved = self.vendor_resolver.resolve("Oracel America")
        self.assertIn("ORACLE AMERICA, INC.", resolved)
        print("Test Passed.")

    def test_no_match(self):
        print("Testing: VendorResolver no_match")
        resolved = self.vendor_resolver.resolve("NON EXISTENT VENDOR")
        self.assertEqual(resolved, [])
        print("Test Passed.")

if __name__ == '__main__':
    unittest.main()
