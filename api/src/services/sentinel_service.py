"""Service for interacting with Sentinel data."""

import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import requests
from supabase import Client, create_client


class SentinelService:
    """Service for interacting with Sentinel data."""

    def __init__(self) -> None:
        """Initialize the SentinelService with Supabase client and CDSE credentials."""
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_KEY", "")
        self.supabase: Client = create_client(url, key)

        # CDSE credentials
        self.cdse_username = os.environ.get("CDSE_USERNAME")
        self.cdse_password = os.environ.get("CDSE_PASSWORD")
        self.access_token = None

    def _get_access_token(self) -> str | None:
        """Get CDSE access token."""
        token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"  # noqa: E501
        payload = {
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": self.cdse_username,
            "password": self.cdse_password,
        }

        # Check if the token is still valid
        if (
            self.access_token is not None
            and self.token_expiry is not None
            and datetime.now(timezone.utc) < self.token_expiry
        ):
            return self.access_token

        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not provided
            print(f"Access token expires in: {expires_in} seconds")
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return self.access_token

        except Exception as e:
            print(f"Error getting access token: {str(e)}")
            raise

    def search_images(
        self, bbox: list, date_from: str, date_to: str, cloud_cover: int = 20
    ) -> Dict[str, Any]:
        """Search Sentinel images and cache results in Supabase."""
        # bbox: [[south, west], [north, east]]
        try:
            # Get access token
            access_token = self._get_access_token()

            # Convert dates to ISO format if needed
            if isinstance(date_from, datetime):
                date_from = date_from.isoformat() + "Z"
            if isinstance(date_to, datetime):
                date_to = date_to.isoformat() + "Z"

            print(f"Searching with dates: {date_from} to {date_to}")

            # Construct filters
            filter_collection = "Collection/Name eq 'SENTINEL-2'"
            filter_product_type = (
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
                "and att/Value eq 'S2MSI1C')"
            )
            filter_dates = f"ContentDate/Start gt {date_from} and ContentDate/End lt {date_to}"
            filter_cloud_cover = (
                "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"and att/OData.CSC.DoubleAttribute/Value le {cloud_cover})"
            )

            # Convert bbox to WKT format
            aoi_wkt = self._bbox_to_wkt(
                {"south": bbox[0][0], "west": bbox[0][1], "north": bbox[1][0], "east": bbox[1][1]}
            )
            filter_aoi = f"OData.CSC.Intersects(area=geography'SRID=4326;{aoi_wkt}')"

            # Combine filters
            combined_filter = (
                f"{filter_collection} and {filter_product_type} and "
                f"{filter_dates} and {filter_cloud_cover} and {filter_aoi}"
            )

            print(f"Using filter: {combined_filter}")

            # Encode the combined filter for URL inclusion
            encoded_filter = urllib.parse.quote(combined_filter)

            # Construct the full query URL
            query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter={encoded_filter}"  # noqa: E501
            print(f"Query URL: {query_url}")

            # Set up headers with the access token
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            # Execute the query
            response = requests.get(query_url, headers=headers)
            if not response.ok:
                print(f"Error response: {response.text}")
                return {"error": f"API request failed: {response.text}"}

            response_data = response.json()
            products = response_data.get("value", [])

            # Format results
            results = []

            for product in products:
                image_data = {
                    "identifier": product["Id"],
                    "title": product["Name"],
                    "timestamp": product["ContentDate"]["Start"],
                    "footprint": product["Footprint"].split(";")[1][0:-1],
                    "metadata": product,
                }
                results.append(image_data)

            if results:
                try:
                    # Delete existing records for these identifiers
                    identifiers = [r["identifier"] for r in results]
                    self.supabase.table("sentinel_images").delete().in_(
                        "identifier", identifiers
                    ).execute()

                    # Insert all new records
                    self.supabase.table("sentinel_images").insert(results).execute()
                except Exception as e:
                    print(f"Error caching results in Supabase: {str(e)}")
                    # Continue even if caching fails

            return {"results": results, "status": "success"}

        except Exception as e:
            print(f"Error searching Sentinel images: {str(e)}")
            return {"error": str(e), "status": "error"}

    def get_metadata(self, image_id: str) -> Dict[str, Any]:
        """Get image metadata from cache or CDSE API."""
        try:
            # Try cache first
            response = (
                self.supabase.table("sentinel_images")
                .select("*")
                .eq("id", image_id)
                .single()
                .execute()
            )

            if response.data:
                return response.data

            # If not in cache, get from CDSE API
            access_token = self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products('{image_id}')"
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            product = response.json()

            # Format and cache it
            image_data = {
                "id": product["Id"],
                "title": product["Name"],
                "timestamp": product["ContentDate"]["Start"],
                "footprint": product["Footprint"],
                "metadata": product,
            }

            self.supabase.table("sentinel_images").insert(image_data).execute()

            return image_data

        except Exception as e:
            print(f"Error getting image metadata: {str(e)}")
            return {"error": str(e)}

    def _bbox_to_wkt(self, bbox: Dict[str, float]) -> str:
        """Convert bbox to WKT format."""
        return (
            f"POLYGON(({bbox['west']} {bbox['south']}, "
            f"{bbox['east']} {bbox['south']}, "
            f"{bbox['east']} {bbox['north']}, "
            f"{bbox['west']} {bbox['north']}, "
            f"{bbox['west']} {bbox['south']}))"
        )
