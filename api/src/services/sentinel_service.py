"""Service for interacting with Sentinel data."""

import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import requests
from supabase import Client, create_client

from ..config import Config

# Sentinel-2 product type configuration
# Use 'S2MSI1C' for Level-1C products or 'S2MSI2A' for Level-2A products
SENTINEL2_PRODUCT_TYPE = "S2MSI2A"


class SentinelService:
    """Service for interacting with Sentinel data."""

    def __init__(self) -> None:
        """Initialize the SentinelService with Supabase client and CDSE credentials."""
        # Initialize Supabase client
        self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

        # CDSE credentials
        self.cdse_username = Config.CDSE_USERNAME
        self.cdse_password = Config.CDSE_PASSWORD
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

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
            self.token_expiry = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in) - timedelta(seconds=10)
            )  # noqa: E501
            return self.access_token

        except Exception as e:
            print(f"Error getting access token: {str(e)}")
            raise

    def _bbox_to_wkt(self, bbox: Dict[str, float]) -> str:
        """Convert bbox to WKT format.

        Copernicus format expects coordinates as (latitude longitude)
        """
        # Create WKT polygon with coordinates as (longitude latitude)
        return (
            f"POLYGON(({bbox['south']} {bbox['west']}, "
            f"{bbox['south']} {bbox['east']}, "
            f"{bbox['north']} {bbox['east']}, "
            f"{bbox['north']} {bbox['west']}, "
            f"{bbox['south']} {bbox['west']}))"
        )

    def search_images(
        self,
        bbox: list,
        date_from: Union[str, datetime],
        date_to: Union[str, datetime],
        cloud_cover: int = 20,
        verbose: bool = True,
    ) -> Union[Dict[str, Any], list[Dict[str, Any]]]:
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

            if verbose:
                print(f"Searching with dates: {date_from} to {date_to}")

            # Construct filters
            filter_collection = "Collection/Name eq 'SENTINEL-2'"
            filter_product_type = (
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
                f"and att/Value eq '{SENTINEL2_PRODUCT_TYPE}')"
            )
            filter_dates = f"ContentDate/Start gt {date_from} and ContentDate/End lt {date_to}"
            filter_cloud_cover = (
                "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                f"and att/OData.CSC.DoubleAttribute/Value le {cloud_cover})"
            )

            # Convert bbox to WKT format
            # bbox format is [[lat1, lon1], [lat2, lon2]]
            # where lat1 is south, lat2 is north, lon1 is west, lon2 is east
            aoi_wkt = self._bbox_to_wkt(
                {
                    "south": bbox[0][0],  # lat1
                    "west": bbox[0][1],  # lon1
                    "north": bbox[1][0],  # lat2
                    "east": bbox[1][1],  # lon2
                }
            )
            # WKT format expects coordinates as (lon lat)
            filter_aoi = f"OData.CSC.Intersects(area=geography'SRID=4326;{aoi_wkt}')"

            # Combine filters
            combined_filter = (
                f"{filter_collection} and {filter_product_type} and "
                f"{filter_dates} and {filter_cloud_cover} and {filter_aoi}"
            )

            if verbose:
                print(f"Using filter: {combined_filter}")

            # Encode the combined filter for URL inclusion
            encoded_filter = urllib.parse.quote(combined_filter)

            # Construct the full query URL
            query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter={encoded_filter}&$expand=Attributes&$top=100"  # noqa: E501
            if verbose:
                print(f"Query URL: {query_url}")

            # Set up headers with the access token
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            # Execute the query
            response = requests.get(query_url, headers=headers)
            if not response.ok:
                if verbose:
                    print(f"Error response: {response.text}")
                return {"error": f"API request failed: {response.text}"}

            response_data = response.json()
            products = response_data.get("value", [])
            if verbose:
                print(f"Received {len(products)} products")
            if products:
                if verbose:
                    print("First product attributes:")
                    print(products[0].get("Attributes", {}))

            # Format results
            results = []

            for product in products:
                # Extract cloud cover
                cloud_cover = next(
                    (
                        attr["Value"]
                        for attr in product.get("Attributes", [])
                        if attr.get("Name") == "cloudCover"
                    ),
                    100,
                )

                # Parse footprint to PostGIS format
                footprint_wkt = product["Footprint"].split(";")[1][0:-1]

                # Format data for response
                image_data = {
                    "identifier": product["Id"],
                    "title": product["Name"],
                    "timestamp": product["ContentDate"]["Start"],
                    "footprint": footprint_wkt,
                    "cloud_cover": cloud_cover,
                    "metadata": str(product),  # Convert to string as per schema
                }
                results.append(image_data)

                try:
                    # Insert into Supabase, TODO:update if exists
                    if verbose:
                        print(f"Inserting/updating image {image_data['identifier']}")
                    self.supabase.table("sentinel2_images").upsert(image_data).execute()
                except Exception as e:
                    if verbose:
                        print(f"Error inserting into database: {str(e)}")
                    # Continue with next image even if this one fails

            return results

        except Exception as e:
            if verbose:
                print(f"Error searching Sentinel images: {str(e)}")
            return {"error": str(e)}

    def get_metadata(self, image_id: str) -> Dict[str, Any]:
        """Get image metadata from cache or CDSE API."""
        try:
            # Get from CDSE API
            access_token = self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

            query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products('{image_id}')"
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            product = response.json()

            # Format metadata
            image_data = {
                "identifier": product["Id"],
                "title": product["Name"],
                "timestamp": product["ContentDate"]["Start"],
                "footprint": product["Footprint"].split(";")[1][0:-1],
                "cloud_cover": next(
                    (
                        attr["Value"]
                        for attr in product.get("Attributes", [])
                        if attr.get("Name") == "cloudCover"
                    ),
                    None,
                ),
                "metadata": product,
            }

            return image_data

        except Exception as e:
            print(f"Error getting image metadata: {str(e)}")
            return {"error": str(e)}
