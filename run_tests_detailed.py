import requests
import json
import time
import logging
from datetime import datetime
import sqlite3

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8080"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FILE = f"test_results_{TIMESTAMP}.json"
DB_PATH = "data/verification.db"  # Path to the SQLite database

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
TEST_RESULTS = []
SUCCESS_COUNT = 0
FAILURE_COUNT = 0

# --- NEW: Database Verification Function ---
def get_sql_verification_data(query: str, params=()) -> list:
    """Execute a direct SQL query to get data for verification."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"SQL verification query failed: {e}")
        return []

def run_test(name: str, complexity: str, method: str, endpoint: str, payload: dict = None, timeout: int = 120, verification_query: str = None):
    """
    Sends a request, logs detailed trace info, and stores the result for JSON output.
    Now includes an optional SQL query for verification.
    """
    global SUCCESS_COUNT, FAILURE_COUNT, TEST_RESULTS
    url = f"{BASE_URL}{endpoint}"
    
    logging.info(f"--- [STARTING TEST] Name: '{name}' | Complexity: {complexity} ---")
    print(f"  - Target     : {method.upper()} {url}")
    if payload:
        print(f"  - Payload    : {json.dumps(payload)}")

    result_log = {
        "test_name": name,
        "complexity": complexity,
        "timestamp_utc": datetime.utcnow().isoformat(),
        "status": "FAILURE", # Default to failure
        "request": {"method": method.upper(), "url": url, "payload": payload},
        "response": {},
        "verification": {"status": "NOT_RUN", "details": ""}
    }

    try:
        start_time = time.perf_counter()
        response = requests.request(method, url, json=payload, timeout=timeout)
        end_time = time.perf_counter()
        
        duration_seconds = round(end_time - start_time, 2)
        result_log["response"] = {
            "duration_seconds": duration_seconds,
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }

        if 200 <= response.status_code < 300:
            result_log["status"] = "SUCCESS"
            SUCCESS_COUNT += 1
            logging.info(f"  - Result     : ✅ SUCCESS ({response.status_code}) in {duration_seconds}s")
            
            try:
                response_body = response.json()
                result_log["response"]["body"] = response_body
                
                # --- NEW: Verification Logic ---
                if verification_query:
                    logging.info("  - Running SQL verification...")
                    expected_data = get_sql_verification_data(verification_query)
                    
                    if not expected_data:
                        result_log["verification"]["status"] = "SKIPPED"
                        result_log["verification"]["details"] = "Could not retrieve verification data from DB."
                    else:
                        # Example: Very basic check, assuming a simple list of vendors
                        actual_vendors = [v.get('vendor') for v in response_body.get('vendors', [])]
                        expected_vendors = [row[0] for row in expected_data]
                        
                        if sorted(actual_vendors) == sorted(expected_vendors):
                            result_log["verification"]["status"] = "PASSED"
                            result_log["verification"]["details"] = "Response data matches direct SQL query."
                        else:
                            result_log["verification"]["status"] = "FAILED"
                            result_log["verification"]["details"] = f"Mismatch: API returned {actual_vendors}, DB returned {expected_vendors}"
                            result_log["status"] = "FAILURE" # Downgrade test status
                            SUCCESS_COUNT -= 1
                            FAILURE_COUNT += 1
                
            except json.JSONDecodeError:
                result_log["response"]["body"] = "Error: Response was not valid JSON."
                logging.warning("Response was not valid JSON.")
        else:
            FAILURE_COUNT += 1
            logging.error(f"  - Result     : ❌ FAILURE ({response.status_code}) in {duration_seconds}s")
            result_log["response"]["body"] = response.text
            
    except requests.exceptions.RequestException as e:
        FAILURE_COUNT += 1
        duration_seconds = round(time.perf_counter() - start_time, 2) if 'start_time' in locals() else -1
        logging.error(f"  - Result     : ❌ FAILURE (Request Exception) in {duration_seconds}s")
        error_message = f"Request failed: {str(e)}"
        result_log["response"] = {"error": error_message}
        print(f"    {error_message}")
        
    finally:
        TEST_RESULTS.append(result_log)
        print("-" * 60)

def save_results_to_json(results: list, filename: str):
    """Saves the list of test results to a JSON file."""
    logging.info(f"Attempting to save {len(results)} test results to '{filename}'...")
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4)
        logging.info(f"✅ Successfully saved test results to '{filename}'.")
    except Exception as e:
        logging.error(f"❌ Failed to save results to JSON file: {e}")

if __name__ == "__main__":
    # --- NEW: Added SQL queries for verification ---
    top_5_vendors_sql = "SELECT VENDOR_NAME_1 FROM procurement GROUP BY VENDOR_NAME_1 ORDER BY SUM(CAST(ITEM_TOTAL_COST AS FLOAT)) DESC LIMIT 5"
    dell_details_sql = "SELECT COUNT(*) FROM procurement WHERE UPPER(VENDOR_NAME_1) LIKE '%DELL%'"

    test_cases = [
        {"complexity": "Simple", "name": "Health Check", "method": "GET", "endpoint": "/health"},
        {"complexity": "Simple", "name": "Top 5 Vendors", "method": "GET", "endpoint": "/top-vendors?n=5", "verification_query": top_5_vendors_sql},
        {"complexity": "Simple", "name": "Statistical Median", "method": "POST", "endpoint": "/statistics/median", "payload": {}},
        {"complexity": "Simple", "name": "Specific Vendor Details (DELL)", "method": "GET", "endpoint": "/vendor/DELL COMPUTER CORP"},
        {"complexity": "Medium", "name": "Basic Chat Query", "method": "POST", "endpoint": "/chat", "payload": {"message": "What is our total spending?", "session_id": "test-123"}},
        {"complexity": "Medium", "name": "Ambiguous Vendor Query", "method": "POST", "endpoint": "/ask", "payload": {"question": "How many orders did we place with the big blue computer company?"}},
        {"complexity": "Medium", "name": "Direct Vendor Comparison", "method": "POST", "endpoint": "/compare-advanced", "payload": {"entities": ["DELL", "IBM"], "type": "vendors"}},
        {"complexity": "Medium", "name": "Dashboard Summary", "method": "GET", "endpoint": "/dashboard"},
        {"complexity": "Complex", "name": "Multi-Step Advanced Query", "method": "POST", "endpoint": "/ask-advanced", "payload": {"question": "Compare total spending for Dell and IBM, then recommend which relationship to focus on for cost savings."}},
        {"complexity": "Complex", "name": "Full Report Generation", "method": "POST", "endpoint": "/report", "payload": {"type": "executive", "focus_areas": ["spending", "vendors"]}},
        {"complexity": "Complex", "name": "Strategic Recommendation", "method": "POST", "endpoint": "/recommend", "payload": {"context": "strategies to reduce procurement overhead"}},
    ]
    
    print("=" * 60)
    logging.info("🚀 STARTING APPLICATION FUNCTIONALITY TEST SUITE 🚀")
    print("=" * 60)

    for test in test_cases:
        run_test(**test)
        
    save_results_to_json(TEST_RESULTS, OUTPUT_FILE)

    print("\n" + "="*60)
    logging.info("✨ TEST SUITE COMPLETE ✨")
    print("=" * 60)
    print(f"  TOTAL TESTS : {len(TEST_RESULTS)}")
    print(f"  ✅ SUCCESS   : {SUCCESS_COUNT}")
    print(f"  ❌ FAILURE   : {FAILURE_COUNT}")
    print(f"  Detailed results saved to: {OUTPUT_FILE}")
    print("=" * 60)