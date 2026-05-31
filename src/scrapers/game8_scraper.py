"""Thu thập team mẫu từ Game8 — triển khai chi tiết ở bước sau."""

import requests
from bs4 import BeautifulSoup


class Game8Scraper:
    BASE_URL = "https://game8.co"

    def fetch_page(self, path: str) -> BeautifulSoup:
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def scrape_team_guide(self, path: str) -> dict:
        """Placeholder: parse team guide HTML."""
        soup = self.fetch_page(path)
        return {"title": soup.title.string if soup.title else None, "path": path}
