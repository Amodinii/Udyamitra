'''
location_normalizer.py - Resolves raw location strings into structured administrative regions
using the Nominatim (OpenStreetMap) API.
'''

import requests
import sys
from Logging.logger import logger
from Exception.exception import UdayamitraException
from typing import Dict, Optional
import time
class LocationNormalizer:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    def __init__(self, delay: float = 1.0):
        try:
            logger.info("Initializing LocationNormalizer")
            self.delay = delay  # to respect Nominatim rate limits
            self.cache = {}     # simple in-memory cache
        except Exception as e:
            logger.error(f"Failed to initialize LocationNormalizer: {e}")
            raise UdayamitraException("Failed to initialize LocationNormalizer", sys)

    def normalize(self, raw_location: str) -> Dict[str, Optional[str]]:
        try:
            logger.info(f"Normalizing location: {raw_location}")
            if raw_location in self.cache:
                return self.cache[raw_location]

            params = {
                "q": raw_location,
                "format": "json",
                "addressdetails": 1,
                "limit": 1
            }
            response = requests.get(self.NOMINATIM_URL, params=params, headers={"User-Agent": "Udyamitra/1.0"})
            time.sleep(self.delay)  # avoid hammering the API
            data = response.json()

            if not data:
                normalized = {"raw": raw_location, "city": None, "state": None, "country": None}
                self.cache[raw_location] = normalized
                return normalized

            address = data[0].get("address", {})
            normalized = {
                "raw": raw_location,
                "city": address.get("city") or address.get("town") or address.get("suburb"),
                "state": address.get("state"),
                "country": address.get("country")
            }

            self.cache[raw_location] = normalized
            return normalized

        except UdayamitraException as e:
            logger.error(f"Error normalizing location '{raw_location}': {e}")
            return {"raw": raw_location, "city": None, "state": None, "country": None}