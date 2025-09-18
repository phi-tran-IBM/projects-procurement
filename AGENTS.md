# Agent Instructions and Environment Configuration

This document provides instructions for AI agents working with this codebase.

## Environment Setup for Testing

To facilitate testing without requiring access to external, credentialed services, this application includes a mocking framework that can be controlled via an environment variable.

### `MOCK_SERVICES`

This is the primary switch for controlling external service mocking.

-   **To enable mocking for all external services (Elasticsearch and WatsonX LLMs):**
    Set the environment variable `MOCK_SERVICES` to `"true"`.

    ```bash
    export MOCK_SERVICES="true"
    ```

    When mocking is enabled:
    -   The application will not attempt to connect to live Elasticsearch or WatsonX services.
    -   It will use mock clients that return predictable, structured data.
    -   This allows the full application logic, including response parsing and data processing, to be tested without credentials.
    -   You will see warnings in the logs indicating that mock services are in use.

-   **To disable mocking and connect to live services:**
    Unset the `MOCK_SERVICES` environment variable or set it to any other value (e.g., `"false"`).

    ```bash
    unset MOCK_SERVICES
    ```

    When mocking is disabled:
    -   The application will attempt to connect to the real Elasticsearch and WatsonX services.
    -   You must provide the necessary credentials and URLs in a `.env` file or as environment variables (e.g., `DISCOVERY_URL`, `WATSONX_PROJECT_ID`, `WATSONX_API_KEY`).
    -   If credentials are not provided, the features dependent on those services will be gracefully disabled, and warnings will be logged.

This mechanism provides a clear and explicit way to control the application's behavior for testing and development.
