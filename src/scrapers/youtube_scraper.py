"""Thu thập mô tả metadata video từ YouTube — triển khai chi tiết ở bước sau."""

import re

import requests


class YouTubeScraper:
    OEMBED_URL = "https://www.youtube.com/oembed"

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        patterns = [
            r"(?:v=|/)([0-9A-Za-z_-]{11}).*",
            r"youtu\.be/([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def fetch_metadata(self, video_url: str) -> dict:
        """Lấy title / author qua oEmbed (không cần API key)."""
        response = requests.get(
            self.OEMBED_URL,
            params={"url": video_url, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
