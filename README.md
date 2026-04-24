# Amarhouse DB Management

Python automation project for collecting product data from supplier sources, normalizing it, and publishing validated product data into the Beevo admin API.

This repository is structured as an integration-focused engineering project rather than a set of ad hoc scripts. The current codebase emphasizes:

- API response validation
- defensive error handling
- data normalization before publication
- unit-test coverage around failure-prone paths
- automated CI execution of the test suite
- reusable publishing and pricing workflows

## What This Project Does

The project supports a product ingestion workflow for Amarhouse:

- scrape supplier product data
- transform supplier data into a normalized internal shape
- publish products, option groups, and variants into Beevo
- update pricing from Excel-based supplier files
- query Beevo data for verification and operational scripts

At the moment, the main supplier-specific areas in the repo are under:

- `scrapers/efapel`
- `scrapers/golmar`
- `scrapers/ecolux`
- `scrapers/ledme`
- `scrapers/rointe`

## Architecture

The repository is split into a few practical layers:

- `beevo/`
  Beevo integration layer. Contains the HTTP client, configuration, validation helpers, and API-specific modules for products, variants, options, assets, labels, and facets.

- `core/`
  Workflow orchestration. `ProductPublisher` coordinates the end-to-end publishing flow using the Beevo API modules.

- `scrapers/`
  Supplier-specific crawling, extraction, parsing, and publication logic.
  The repository now includes a shared scraper foundation under `scrapers/base/` so new supplier integrations can follow a common contract.

- `scripts/`
  Task-focused entrypoints for one-off or operational workflows such as updating prices and filtering products by facet.

- `tests/`
  Unit tests for transport validation, configuration handling, helper validation logic, publishing behavior, and price update flows.

## Key Engineering Decisions

### 1. Validated Beevo Client

The Beevo transport layer in [beevo/client.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/beevo/client.py:11) validates:

- required configuration
- HTTP status codes
- JSON parsing
- GraphQL error payloads
- transport-level failures

This makes integration failures deterministic and testable instead of relying on silent assumptions.

### 2. Explicit Exceptions

Custom exception types in [beevo/exceptions.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/beevo/exceptions.py:1) separate:

- configuration failures
- transport failures
- unexpected API responses
- validation failures

This is useful both operationally and from a testing perspective.

### 3. Response Validation Helpers

The helper functions in [beevo/validation.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/beevo/validation.py:6) are used to assert expected response shape before the rest of the code consumes Beevo data.

This reduces the chance of downstream runtime errors caused by malformed or incomplete API payloads.

### 4. Workflow-Oriented Publisher

[core/publisher.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/core/publisher.py:16) acts as an orchestration layer rather than mixing Beevo transport logic directly into scripts.

That separation makes the publishing flow easier to reason about and easier to test with stubs.

## Environment Variables

Create a `.env` file in the project root. The main variables currently used are:

```env
BEEVO_URL=https://your-domain.beevo.com/admin-api?languageCode=pt_PT
BEEVO_COOKIE=your-session-cookie
ENV=development
REQUEST_TIMEOUT=30
DEBUG=false
```

Environment loading and validation are handled in:

- [beevo/config/config.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/beevo/config/config.py:8)
- [beevo/config/env_loader.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/beevo/config/env_loader.py:4)

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running Tests

The project includes unit tests for:

- Beevo client validation
- configuration loading and validation
- generic validation helper functions
- option API request/response behavior
- publisher workflow behavior
- Excel-based price import and update behavior

Run the test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

Current test modules:

- [tests/test_client.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_client.py:1)
- [tests/test_config.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_config.py:1)
- [tests/test_options_api.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_options_api.py:1)
- [tests/test_publisher.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_publisher.py:1)
- [tests/test_update_prices.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_update_prices.py:1)
- [tests/test_validation_helpers.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/tests/test_validation_helpers.py:1)

## Continuous Integration

GitHub Actions is configured in [`.github/workflows/ci.yml`](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/.github/workflows/ci.yml:1).

The CI pipeline:

- runs on pushes, pull requests, and manual dispatch
- tests the project on `ubuntu-latest` and `windows-latest`
- installs dependencies from `requirements.txt`
- runs `pytest`
- uploads JUnit-style test results as build artifacts

This gives the repository a proper automated quality gate and strengthens the test-engineering context of the project.

## Common Workflows

### Update prices from Excel

```powershell
.\.venv\Scripts\python.exe .\scripts\update_prices.py
```

This workflow:

- loads Beevo settings from `.env`
- reads a supplier Excel workbook
- normalizes SKU and price values
- builds a Beevo variant lookup
- updates only changed prices

Implementation: [scripts/update_prices.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/scripts/update_prices.py:1)

### Run the product publisher

```powershell
.\.venv\Scripts\python.exe .\core\publisher.py
```

The publisher currently:

- checks whether a product already exists by slug
- creates products if missing
- creates and attaches option groups
- creates variants

Implementation: [core/publisher.py](/C:/Users/janua/Documents/amarhouse/amarhouse_db_management/core/publisher.py:16)

### Query products by facet

```powershell
.\.venv\Scripts\python.exe .\scripts\get_products_filtered_by_facet.py
```

## Repository Layout

```text
amarhouse_db_management/
|-- beevo/
|   |-- client.py
|   |-- product.py
|   |-- options.py
|   |-- variants.py
|   |-- assets.py
|   |-- labels.py
|   |-- facets.py
|   |-- exceptions.py
|   |-- validation.py
|   `-- config/
|-- core/
|   `-- publisher.py
|-- scrapers/
|   |-- base/
|   |-- efapel/
|   |-- golmar/
|   |-- ecolux/
|   |-- ledme/
|   `-- rointe/
|-- scripts/
|-- tests/
`-- utils/
```

## Why This Repo Is Useful As A Portfolio Project

This project demonstrates more than scraping or scripting. It shows:

- API integration design
- validation-first engineering
- defensive handling of unreliable external data
- workflow orchestration
- regression-focused unit testing
- CI-based automated test execution
- practical automation for product operations

That combination makes it a strong example of test-aware backend/integration work, especially for a Test Engineer or QA Automation profile.

## Next Improvements

High-value next steps:

- add unit tests for `ProductAPI` and `VariantsAPI` response validation
- add CLI argument parsing for operational scripts
- standardize logging across scripts and scrapers
- add fixture-based sample payloads for Beevo response contract testing
- add coverage reporting and a CI badge to the README
