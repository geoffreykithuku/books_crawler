# Books Crawler and API

This project implements a robust and scalable web crawling solution to extract book information from [books.toscrape.com](https://books.toscrape.com/), detect changes in the scraped data, and serve this information via a secure RESTful API.

## Features

*   **Scalable Web Crawler**: Asynchronously crawls all book details from books.toscrape.com, handling pagination and transient network errors with retry logic. It collects book name, description, category, prices (including and excluding taxes), availability, number of reviews, image URL, and rating. The crawler supports resuming from the last successful crawl and stores raw HTML snapshots for fallback.
*   **Change Detection**: A daily scheduler re-fetches book pages, compares content fingerprints, and logs any detected changes (e.g., price or availability updates). It also detects and inserts newly added books into the database and maintains a detailed change log.
*   **RESTful API**: Built with FastAPI, providing secure endpoints to:
    *   Query a paginated list of books with filters (category, min/max price, rating) and sorting options.
    *   Retrieve full details for a specific book by ID or source URL.
    *   View recent updates and change logs.
*   **Authentication & Rate Limiting**: Secures API access with API key-based authentication and enforces rate limits (100 requests per hour) to prevent abuse.
*   **Data Storage**: Utilizes MongoDB as a NoSQL database for efficient storage and retrieval of book data, change logs, and crawler state.
*   **Pydantic Models**: Ensures data integrity and validation using Pydantic for defining data schemas across the crawler and API.

## Technologies Used

*   **Python 3.9+**
*   **FastAPI**: Web framework for building the API.
*   **MongoDB**: NoSQL database for data storage.
*   **Httpx**: Asynchronous HTTP client for web crawling.
*   **BeautifulSoup4** & **Lxml**: For parsing HTML content.
*   **Pydantic**: Data validation and settings management.
*   **APScheduler**: Asynchronous job scheduler.
*   **Tenacity**: Retry library for robust network requests.
*   **Pytest**: Testing framework.
*   **python-dotenv**: For managing environment variables.

## Folder Structure

The project follows a modular structure to separate concerns:

```
.
├── requirements.txt
├── api/                  # FastAPI application for serving data
│   ├── __init__.py
│   ├── main.py
├── crawler/              # Web crawling logic
│   ├── __init__.py
│   ├── crawler.py
│   ├── models.py         # Pydantic models for book data
│   ├── parser.py         # HTML parsing logic
├── db/                   # Database client and connection setup
│   ├── __init__.py
│   ├── client.py
├── scheduler/            # Job scheduling and change detection
│   ├── __init__.py
│   ├── change_detector.py
│   ├── jobs.py
├── tests/                # Unit and integration tests
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_parser.py
└── utils/                # Utility functions (if any)
    └── __init__.py
```

## Setup Instructions

### Prerequisites

*   **Python 3.9+**: Ensure Python is installed on your system.
*   **MongoDB**: Install and run MongoDB. You can find instructions [here](https://docs.mongodb.com/manual/installation/).

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/books_crawler.git
cd books_crawler
```

### 2. Set up a Virtual Environment

It's recommended to use a virtual environment to manage project dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file in the root directory of the project to configure your settings.

**Example `.env` file:**

```dotenv
MONGO_URI="mongodb://localhost:27017"
DB_NAME="bookscrape"
API_KEY="your_secret_api_key" # Change this to a strong, unique key
CRAWL_CONCURRENCY="8"
RATE_LIMIT_PER_HOUR="100"
```

*   `MONGO_URI`: Your MongoDB connection string.
*   `DB_NAME`: The name of the database to use.
*   `API_KEY`: The secret key required to access your API endpoints.
*   `CRAWL_CONCURRENCY`: The number of concurrent requests the crawler will make.
*   `RATE_LIMIT_PER_HOUR`: The maximum number of API requests allowed per hour per API key.

## Running the Application

### 1. Start MongoDB

Ensure your MongoDB instance is running.

### 2. Run the Crawler (Manual Run)

You can run the crawler once manually to populate your database:

```bash
python -m crawler.crawler
```

### 3. Start the Scheduler

The scheduler will automatically run the crawler and change detection jobs daily.

```bash
python -m scheduler.jobs
```
Press `Ctrl+C` to stop the scheduler.

### 4. Start the API Server

Run the FastAPI application using Uvicorn:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be accessible at `http://localhost:8000`.

## API Endpoints

The API provides interactive documentation via Swagger UI at `http://localhost:8000/docs` and ReDoc at `http://localhost:8000/redoc`.

All endpoints require an `X-API-Key` header for authentication.

### 1. GET /books

Retrieve a paginated list of books with filtering and sorting options.

**Query Parameters:**
*   `category` (string, optional): Filter by book category.
*   `min_price` (float, optional): Minimum price (inclusive).
*   `max_price` (float, optional): Maximum price (inclusive).
*   `rating` (integer, optional): Filter by star rating (1-5).
*   `sort_by` (string, optional): Field to sort by (`rating`, `price`, `reviews`). Default: `rating`.
*   `page` (integer, optional): Page number. Default: `1`.
*   `per_page` (integer, optional): Number of items per page. Default: `20`.

**Example Request (cURL):**

```bash
curl -X 'GET' \
  'http://localhost:8000/books?category=Poetry&min_price=10&sort_by=price&page=1&per_page=10' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your_secret_api_key'
```

### 2. GET /books/{book_id}

Retrieve full details for a specific book. `book_id` can be either the MongoDB `_id` (as a string) or the `source_url` of the book.

**Example Request (cURL - by MongoDB _id):**

```bash
curl -X 'GET' \
  'http://localhost:8000/books/654a9b2c1d2e3f4a5b6c7d8e' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your_secret_api_key'
```

**Example Request (cURL - by source_url):**

```bash
curl -X 'GET' \
  'http://localhost:8000/books/https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your_secret_api_key'
```

### 3. GET /changes

View recent updates and change logs.

**Query Parameters:**
*   `limit` (integer, optional): Maximum number of change records to return. Default: `50`.

**Example Request (cURL):**

```bash
curl -X 'GET' \
  'http://localhost:8000/changes?limit=10' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your_secret_api_key'
```

### 4. GET /report/daily_changes

Generate a comprehensive daily change report in JSON or CSV format.

**Query Parameters:**
*   `format` (string, optional): The desired output format. Can be `json` (default) or `csv`.

**Example Request (cURL - JSON):**

```bash
curl -X 'GET' \
  'http://localhost:8000/report/daily_changes?format=json' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your_secret_api_key'
```

**Example Request (cURL - CSV):**

```bash
curl -X 'GET' \
  'http://localhost:8000/report/daily_changes?format=csv' \
  -H 'accept: text/csv' \
  -H 'X-API-Key: your_secret_api_key'
```

## Sample MongoDB Document Structure

### `books` Collection Document

```json
{
  "_id": ObjectId("654a9b2c1d2e3f4a5b6c7d8e"),
  "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "title": "A Light in the Attic",
  "description": "It's hard to imagine a world without A Light in the Attic. Shel Silverstein's...",
  "category": "Poetry",
  "price_including_tax": 51.77,
  "price_excluding_tax": 51.77,
  "availability": "In stock (22 available)",
  "num_reviews": 0,
  "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
  "rating": 3,
  "crawl_timestamp": "2023-11-09T12:00:00.000Z",
  "status": "fetched",
  "fingerprint": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
  "raw_html_snapshot": "<html>...full HTML content...</html>",
  "created_at": "2023-11-09T11:55:00.000Z"
}
```

### `changes` Collection Document

```json
{
  "_id": ObjectId("654a9b2c1d2e3f4a5b6c7d8f"),
  "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "changed_at": "2023-11-09T13:00:00.000Z",
  "old_fingerprint": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
  "new_fingerprint": "x1y2z3w4x5y6z7w8x9y0z1w2x3y4z5w6x7y8z9w0x1y2z3w4x5y6z7w8x9y0z1w2",
  "old": {
    "title": "A Light in the Attic",
    "price_including_tax": 51.77,
    "availability": "In stock (22 available)",
    // ... other fields before change
  },
  "new": {
    "title": "A Light in the Attic",
    "price_including_tax": 52.00, // Example: price changed
    "availability": "In stock (20 available)",
    // ... other fields after change
  }
}
```

## Test Coverage

To run the unit tests for the project:

```bash
source .venv/bin/activate
pytest
```
