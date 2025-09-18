import unittest
import requests
import json
import time

class TestIntegrationSuite(unittest.TestCase):
    """
    Comprehensive integration test suite for the Procurement RAG API.
    Assumes the server is running with mocked external services.
    """
    BASE_URL = "http://127.0.0.1:8080"

    def _post_request(self, endpoint, payload):
        """Helper function to make a POST request and return the JSON response."""
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()

    def test_01_health_check(self):
        print("\n--- Testing /health endpoint ---")
        url = f"{self.BASE_URL}/health"
        response = requests.get(url, timeout=10)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        print("Health check passed.")

    def test_02_ask_endpoint_statistical(self):
        print("\n--- Testing /ask endpoint (statistical) ---")
        payload = {"question": "What is the median order value for Dell?"}
        data = self._post_request("/ask", payload)
        self.assertEqual(data['query_type'], 'statistical')
        self.assertIn('statistics', data)
        self.assertIn('median', data['statistics'])
        print("Statistical query via /ask passed.")

    def test_03_ask_endpoint_semantic_mocked(self):
        print("\n--- Testing /ask endpoint (semantic/mocked) ---")
        payload = {"question": "What are our strategic goals?"} # Generic question to trigger semantic search
        data = self._post_request("/ask", payload)
        self.assertEqual(data['query_type'], 'semantic_search')
        self.assertIn('MOCK VENDOR', data['answer'])
        print("Semantic query via /ask (mocked) passed.")

    def test_04_recommend_endpoint_mocked(self):
        print("\n--- Testing /recommend endpoint (mocked) ---")
        payload = {"context": "cost optimization"}
        data = self._post_request("/recommend", payload)
        self.assertEqual(data['source'], 'SQL-Grounded RAG')
        self.assertIn('This is a mock LLM response', data['answer'])
        print("Recommendation query (mocked) passed.")

    def test_05_compare_endpoint(self):
        print("\n--- Testing /compare endpoint ---")
        payload = {"vendors": ["DELL", "IBM"]}
        data = self._post_request("/compare", payload)
        self.assertEqual(len(data['vendors']), 2)
        vendor_names = [v['vendor'] for v in data['vendors']]
        self.assertIn('DELL INC', vendor_names)
        self.assertIn('INTERNATIONAL BUSINESS MACHINES', vendor_names)
        print("Vendor comparison passed.")

    def test_06_statistics_endpoint(self):
        print("\n--- Testing /statistics/all endpoint ---")
        payload = {"vendors": ["DELL"]}
        data = self._post_request("/statistics/all", payload)
        self.assertEqual(data['metric'], 'all')
        self.assertIn('mean', data)
        self.assertIn('median', data)
        print("Statistics 'all' for a vendor passed.")

    def test_07_invalid_requests(self):
        print("\n--- Testing invalid requests ---")

        # Test /recommend without context
        url = f"{self.BASE_URL}/recommend"
        response = requests.post(url, json={}, timeout=10)
        self.assertEqual(response.status_code, 400)
        print("/recommend with empty payload returned 400.")

        # Test /compare with too few vendors
        url = f"{self.BASE_URL}/compare"
        response = requests.post(url, json={"vendors": ["DELL"]}, timeout=10)
        self.assertEqual(response.status_code, 400)
        print("/compare with one vendor returned 400.")

if __name__ == '__main__':
    # Note: This test suite must be run against a live server.
    # It does not start the server itself.
    unittest.main()
