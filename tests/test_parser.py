
import pytest
from crawler.parser import parse_book_page

def test_parse_sample_html():
    # small sample html saved inline for a minimal test
    sample = """
    <html><body>
      <div class="product_main"><h1>Test Book</h1><p class="star-rating Three"></p></div>
      <ul class="breadcrumb"><li><a>Home</a></li><li><a>Books</a></li><li><a>Poetry</a></li></ul>
      <table class="table table-striped">
        <tr><th>Price (incl. tax)</th><td>£10.00</td></tr>
        <tr><th>Price (excl. tax)</th><td>£9.00</td></tr>
        <tr><th>Number of reviews</th><td>2</td></tr>
        <tr><th>Availability</th><td>In stock (20 available)</td></tr>
      </table>
    </body></html>
    """
    data = parse_book_page(sample, "https://books.toscrape.com/catalogue/test_1")
    assert data["title"] == "Test Book"
    assert data["category"] == "Poetry"
    assert data["price_including_tax"] == 10.0
    assert data["price_excluding_tax"] == 9.0
    assert data["rating"] == 3
