"""Sentinel-2 COG converter service.

This module provides functionality to convert Sentinel-2 images to Cloud Optimized GeoTIFF (COG)
format and upload them to Google Cloud Storage.
"""

import json
import logging
import os
import tempfile
import warnings
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import rasterio
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import storage
from google.oauth2 import service_account
from middleware import APIKeyMiddleware
from pydantic import BaseModel
from rasterio.errors import NotGeoreferencedWarning
from rio_cogeo.cogeo import cog_translate
from supabase import Client, create_client

# Sentinel-2 product type configuration
# Use 'L1C' for Level-1C products or 'L2A' for Level-2A products
SENTINEL2_PRODUCT_TYPE = "L2A"

# Band patterns for different product types
BAND_PATTERNS = {
    "L1C": {"directory": "IMG_DATA", "suffix": ".jp2"},
    "L2A": {"directory": "R10m", "suffix": "_10m.jp2"},
}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress rasterio warnings about georeferencing
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

# Initialize Supabase client
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    supabase: Client = create_client(supabase_url, supabase_key)
    logger.info("Successfully initialized Supabase client")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

app = FastAPI(title="Sentinel COG Converter")

# Add API Key middleware
app.add_middleware(APIKeyMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Local development
        "http://localhost:5173",  # Vite dev server
        "http://localhost:4173",  # Vite preview server
        "https://ship-pipeline-web-577713910386.europe-west1.run.app",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files directory
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Add favicon route
@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    return FileResponse(str(static_path / "favicon.ico"))


class SentinelImage(BaseModel):
    """Model for Sentinel image request."""

    sentinel_id: str
    bucket_name: str = os.getenv("GCS_BUCKET_NAME", "dl4eo-sentinel2-cogs")


class CDSEAuth:
    """Authentication handler for Copernicus Data Space Ecosystem."""

    def __init__(self) -> None:
        """Initialize CDSE authentication."""
        self.cdse_username = os.getenv("CDSE_USERNAME")
        self.cdse_password = os.getenv("CDSE_PASSWORD")
        if not self.cdse_username or not self.cdse_password:
            raise ValueError("CDSE_USERNAME and CDSE_PASSWORD must be set")
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def get_access_token(self) -> str:
        """Get CDSE access token.

        Returns:
            str: The access token for CDSE API.

        Raises:
            HTTPException: If authentication fails.
        """
        token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"  # noqa E501
        payload = {
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": self.cdse_username,
            "password": self.cdse_password,
        }

        # Check if token is still valid
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
            token = token_data.get("access_token")
            if not isinstance(token, str):
                raise HTTPException(status_code=401, detail="Invalid access token in response")
            self.access_token = token
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in) - timedelta(seconds=10)
            )
            return token
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            if hasattr(e, "response"):
                logger.error(f"Response content: {e.response.text}")
            raise HTTPException(
                status_code=401,
                detail=f"Failed to authenticate with CDSE: {str(e)}",
            )


cdse_auth = CDSEAuth()


def find_rgb_bands(zip_path: str) -> Dict[str, str]:
    """Find RGB band files (B02, B03, B04) in the Sentinel-2 ZIP archive.

    Args:
        zip_path: Path to the Sentinel-2 ZIP archive.

    Returns:
        Dict mapping band names to their file paths.

    Raises:
        ValueError: If required bands are missing.
    """
    bands: Dict[str, str] = {}
    required_bands = {"B02", "B03", "B04"}  # Blue, Green, Red
    band_pattern = BAND_PATTERNS[SENTINEL2_PRODUCT_TYPE]

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # List all files in the ZIP for debugging
        all_files = zip_ref.namelist()
        logger.info("Files in ZIP archive:")
        for f in all_files:
            if ".jp2" in f:
                logger.info(f"Found JP2: {f}")

        # Look for band files
        for filename in all_files:
            if filename.endswith(".jp2"):
                for band in required_bands:
                    # Match band pattern based on product type
                    if (
                        f"_{band}{band_pattern['suffix']}" in filename
                        and band_pattern["directory"] in filename
                    ):
                        bands[band] = filename
                        logger.info(f"Found {band} band: {filename}")
                        break

    missing_bands = required_bands - set(bands.keys())
    if missing_bands:
        logger.error(f"Missing bands: {missing_bands}")
        logger.error("Please check the ZIP structure and band naming patterns")
        raise ValueError(
            f"Missing required bands: {missing_bands}. Maybe this is not a {SENTINEL2_PRODUCT_TYPE} product?"  # noqa: E501
        )

    logger.info("Found all required band files:")
    for band, filename in bands.items():
        logger.info(f"{band}: {filename}")

    return bands


def validate_cog(filepath: str) -> bool:
    """Validate that the output file is a proper COG.

    Args:
        filepath: Path to the file to validate.

    Returns:
        bool: True if the file is a valid COG, False otherwise.
    """
    try:
        with rasterio.open(filepath) as src:
            # Check basic requirements
            if not src.driver == "GTiff":
                logger.error("File is not a GeoTIFF")
                return False

            # Check if tiled
            if not src.profile.get("tiled", False):
                logger.error("File is not tiled")
                return False

            # Check block size
            if src.profile.get("blockxsize", 0) != 512 or src.profile.get("blockysize", 0) != 512:
                logger.error("Invalid block size")
                return False

            # Check overviews
            if not src.overviews(1):
                logger.error("No overviews found")
                return False

            # Check interleave
            if src.profile.get("interleave", "") != "pixel":
                logger.error("Not using pixel interleaving")
                return False

            # Check compression
            if src.profile.get("compress", "") != "deflate":
                logger.error("Not using deflate compression")
                return False

            logger.info("COG validation successful")
            logger.info(f"Profile: {src.profile}")
            return True

    except Exception as e:
        logger.error(f"Error validating COG: {str(e)}")
        return False


def extract_and_stack_rgb_bands(
    zip_path: str, band_files: Dict[str, str], output_path: str
) -> None:
    """Extract RGB bands from ZIP, stack them, and convert to COG.

    Args:
        zip_path: Path to the Sentinel-2 ZIP archive.
        band_files: Dictionary mapping band names to their file paths.
        output_path: Path where the output COG should be saved.

    Raises:
        ValueError: If band extraction or processing fails.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Extract all bands
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for band_file in band_files.values():
                    zip_ref.extract(band_file, tmp_dir)
        except Exception as e:
            logger.error(f"Error extracting bands from ZIP: {str(e)}")
            raise ValueError(f"Failed to extract bands from ZIP: {str(e)}")

        # Read and stack bands
        band_data: List[np.ndarray] = []
        profile: Optional[Dict[str, Any]] = None

        try:
            # Read bands in RGB order (B04, B03, B02)
            for band_name in ["B04", "B03", "B02"]:
                band_path = os.path.join(tmp_dir, band_files[band_name])
                if not os.path.exists(band_path):
                    raise ValueError(f"Band file not found: {band_path}")

                with rasterio.open(band_path) as src:
                    if profile is None:
                        profile = src.profile.copy()
                        # Set nodata in source profile
                        profile.update({"nodata": 0, "dtype": "uint8"})  # Update dtype here as well
                        logger.info(f"Source profile: {profile}")

                        # Validate source profile
                        required_fields = ["width", "height", "crs", "transform"]
                        missing_fields = [f for f in required_fields if f not in profile]
                        if missing_fields:
                            raise ValueError(
                                f"Source profile missing required fields: {missing_fields}"
                            )

                    # Read data and scale from 12-bit (0-4095) to 8-bit (0-255)
                    data = src.read(1)
                    if data is None:
                        raise ValueError(f"Failed to read data from band {band_name}")

                    data = data.astype(np.float32)
                    data = np.clip(data, 0, 4095)

                    # Perform histogram stretch
                    p2, p98 = np.percentile(data, (0.1, 99.9))
                    data = np.clip(data, p2, p98)
                    data = ((data - p2) / (p98 - p2) * 254 + 1).astype(np.uint8)
                    band_data.append(data)

            if len(band_data) != 3:
                raise ValueError(f"Expected 3 bands, got {len(band_data)}")

            # Create output profile with explicit types
            output_profile = {
                "driver": "GTiff",
                "dtype": "uint8",
                "nodata": int(0),
                "width": int(profile["width"]),
                "height": int(profile["height"]),
                "count": 3,
                "crs": profile["crs"],
                "transform": profile["transform"],
                "tiled": True,
                "blockxsize": 512,
                "blockysize": 512,
                "compress": "deflate",
                "predictor": 2,
                "zlevel": 9,
                "photometric": "rgb",
                "interleave": "pixel",
            }

            logger.info(f"Output profile: {output_profile}")

            # Create temporary RGB TIFF
            with tempfile.NamedTemporaryFile(suffix=".tif") as tmp_rgb:
                # Write stacked bands
                try:
                    with rasterio.open(tmp_rgb.name, "w", **output_profile) as dst:
                        stacked_data = np.stack(band_data)
                        if stacked_data.shape != (
                            3,
                            output_profile["height"],
                            output_profile["width"],
                        ):
                            raise ValueError(f"Invalid data shape: {stacked_data.shape}")
                        dst.write(stacked_data)
                except Exception as e:
                    logger.error(f"Error writing RGB TIFF: {str(e)}")
                    raise ValueError(f"Failed to write RGB TIFF: {str(e)}")

                logger.info(f"Temp RGB TIFF {tmp_rgb.name} created.")

                # Convert to COG
                # Create COG profile with only supported GTiff creation options
                cog_profile = {
                    "driver": "GTiff",
                    "tiled": True,
                    "blockxsize": 512,
                    "blockysize": 512,
                    "compress": "deflate",
                    "predictor": 2,
                    "photometric": "rgb",
                    "interleave": "pixel",
                }

                logger.info("Final COG profile:")
                for key, value in cog_profile.items():
                    logger.info(f"{key}: {value} ({type(value)})")

                # Use rio_cogeo with explicit configuration
                config = {
                    "GDAL_TIFF_OVR_BLOCKSIZE": 512,  # Integer instead of string
                    "GDAL_TIFF_INTERNAL_MASK": True,  # Boolean instead of string
                    "GDAL_NUM_THREADS": "ALL_CPUS",  # This one stays as string
                    "GDAL_CACHEMAX": 1024,  # Integer instead of string
                }

                logger.info(f"GDAL config: {config}")

                try:
                    with rasterio.Env(**config):
                        logger.info("Starting COG translation...")
                        cog_translate(
                            tmp_rgb.name,
                            output_path,
                            cog_profile,
                            quiet=False,  # Enable output for debugging
                            web_optimized=False,  # Disable web optimization
                            overview_level=4,  # Changed back to overview_level (singular)
                            overview_resampling="nearest",  # 'nearest' is better than 'average'
                            add_mask=False,
                        )
                        logger.info("COG translation completed")
                except Exception as e:
                    logger.error(f"Error in COG translation: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    logger.error(f"Error args: {e.args}")
                    if hasattr(e, "__dict__"):
                        logger.error(f"Error attributes: {e.__dict__}")
                    raise ValueError(f"Failed to create COG: {str(e)}")

                # Validate the output COG
                if not os.path.exists(output_path):
                    raise ValueError("COG file was not created")

                if not validate_cog(output_path):
                    raise ValueError("Generated file failed COG validation")

        except Exception as e:
            logger.error(f"Error processing bands: {str(e)}")
            logger.error(f"Profile: {profile}")
            raise ValueError(f"Error processing bands: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint for the Sentinel COG Converter Service.

    Returns:
        A dictionary with a welcome message.
    """
    return {"message": "Sentinel COG Converter Service"}


@app.get("/health")
async def health_check():

    try:
        # Check services
        services_status = {"sentinel_api": False, "google_storage": False, "supabase": False}

        # Check CDSE API connection
        try:
            # Get access token and make a simple query
            access_token = cdse_auth.get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            query_url = (
                "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
                "$filter=Collection/Name eq 'SENTINEL-2'&$top=1"
            )
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            services_status["sentinel_api"] = True
        except Exception as e:
            print(f"CDSE API error: {str(e)}")
            services_status["sentinel_api"] = False

        # Check Google Storage connection
        try:
            # Load credentials from the environment variable if it exists
            if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                credentials = service_account.Credentials.from_service_account_file(
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
                )
                storage_client = storage.Client(credentials=credentials)
            else:
                storage_client = storage.Client()

            # List contents of the bucket
            print(f"GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME')}")
            bucket_name = os.getenv("GCS_BUCKET_NAME", "dl4eo-sentinel2-cogs")
            bucket = storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(max_results=1)
            logger.info(f"Displaying first GCS blob: {blobs}")

            services_status["google_storage"] = True
        except Exception as e:
            print(f"Google Storage error: {str(e)}")
            services_status["google_storage"] = False

        # Check Supabase connection
        try:
            supabase.table("sentinel2_cogs").select("*").limit(1).execute()
            services_status["supabase"] = True
        except Exception as e:
            print(f"Supabase error: {str(e)}")
            services_status["supabase"] = False

        return {
            "status": "healthy",
            "services": services_status,
            "version": "0.1.0",
        }, 200

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500


async def update_cog_status(
    identifier: str, status: str, bucket: Optional[str] = None, path: Optional[str] = None
) -> None:
    """Update the status of a COG in Supabase.

    Args:
        identifier: The Sentinel-2 image identifier.
        status: The status to set ('processing' or 'ready').
        bucket: Optional bucket name where the COG is stored.
        path: Optional path to the COG in the bucket.
    """
    try:
        data = {"identifier": identifier, "status": status}
        if bucket:
            data["bucket"] = bucket
        if path:
            data["path"] = path

        response = supabase.table("sentinel2_cogs").upsert(data, on_conflict="identifier").execute()
        if not response.data:
            logger.error(f"Failed to update COG status for {identifier}")
        else:
            logger.info(f"Updated COG status for {identifier} to {status}")
    except Exception as e:
        logger.error(f"Error updating COG status: {str(e)}")
        raise


@app.post("/convert")
async def convert_to_cog(image: SentinelImage) -> Dict[str, str]:
    """Convert Sentinel-2 image to COG and upload to GCS.

    Args:
        image: SentinelImage model containing sentinel_id and bucket_name.

    Returns:
        Dict containing the status and GCS URI of the converted image.

    Raises:
        HTTPException: If conversion or upload fails.
    """
    # Update status to processing
    await update_cog_status(image.sentinel_id, "processing")

    error_detail = None
    try:
        # Get CDSE access token
        access_token = cdse_auth.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        # Get product metadata and download URL
        query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Id eq '{image.sentinel_id}'&$expand=Assets"  # noqa E501
        logger.info(f"Requesting product with assets from: {query_url}")

        try:
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"API Response: {json.dumps(data, indent=2)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product metadata: {str(e)}")
            if hasattr(e, "response"):
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching product metadata: {str(e)}"
            )

        if not data.get("value"):
            raise HTTPException(status_code=404, detail="Product not found")

        product = data["value"][0]
        logger.info(f"Available assets: {json.dumps(product.get('Assets', []), indent=2)}")

        # Get the S3 path for the full product
        s3_path = product.get("S3Path")
        if not s3_path:
            raise HTTPException(status_code=404, detail="S3 path not found for product")

        # Construct the download URL for the full product (without quotes around UUID)
        download_url = (
            f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({image.sentinel_id})/$value"
        )
        logger.info(f"Using product download URL: {download_url}")

        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp_zip, tempfile.NamedTemporaryFile(
            suffix=".tif"
        ) as tmp_output:
            # Download Sentinel image as ZIP
            logger.info(f"Downloading image from: {download_url}")
            try:
                download_response = requests.get(download_url, headers=headers, stream=True)
                download_response.raise_for_status()

                # Verify content type
                content_type = download_response.headers.get("content-type", "")
                if "zip" not in content_type.lower():
                    error_msg = f"Unexpected content type: {content_type}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Save the ZIP file
                file_size = 0
                with open(tmp_zip.name, "wb") as f:
                    for chunk in download_response.iter_content(chunk_size=8192):
                        if chunk:
                            file_size += len(chunk)
                            f.write(chunk)

                if file_size == 0:
                    raise ValueError("Downloaded file is empty")

                logger.info(f"Downloaded ZIP file size: {file_size} bytes")

            except requests.exceptions.RequestException as e:
                error_detail = f"Download failed: {str(e)}"
                logger.error(error_detail)
                raise HTTPException(status_code=500, detail=error_detail)

            try:
                # Find RGB band files
                band_files = find_rgb_bands(tmp_zip.name)
                logger.info(f"Found RGB band files: {json.dumps(band_files, indent=2)}")

                # Extract and stack RGB bands
                extract_and_stack_rgb_bands(tmp_zip.name, band_files, tmp_output.name)

            except Exception as e:
                error_detail = f"Error processing image files: {str(e)}"
                logger.error(error_detail)
                raise HTTPException(status_code=500, detail=error_detail)

            # Upload to GCS
            try:
                # Load credentials from the environment variable if it exists
                if "GOOGLE_APPLICATION_CREDENTIALS_FILE" in os.environ:
                    credentials = service_account.Credentials.from_service_account_file(
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS_FILE"]
                    )
                    storage_client = storage.Client(credentials=credentials)
                else:
                    storage_client = storage.Client()

                logger.info(f"Uploading to GCS bucket: {image.bucket_name}")
                bucket = storage_client.bucket(image.bucket_name)

                if not os.path.exists(tmp_output.name):
                    raise ValueError("COG file not found for upload")

                output_blob_name = f"cogs/{image.sentinel_id}_rgb.tif"
                blob = bucket.blob(output_blob_name)
                blob.upload_from_filename(tmp_output.name)

                # After successful upload, update status to ready
                gcs_uri = f"gs://{image.bucket_name}/{output_blob_name}"
                await update_cog_status(
                    image.sentinel_id, "ready", bucket=image.bucket_name, path=output_blob_name
                )

                return {
                    "status": "success",
                    "message": "Image converted and uploaded successfully",
                    "gcs_uri": gcs_uri,
                }
            except Exception as e:
                error_detail = f"Error uploading to GCS: {str(e)}"
                logger.error(error_detail)
                raise HTTPException(status_code=500, detail=error_detail)

    except Exception as e:
        # Update status back to null on failure
        await update_cog_status(image.sentinel_id, "error")
        if not error_detail:
            error_detail = str(e)
        logger.error(f"Error processing image: {error_detail}")
        if hasattr(e, "response"):
            logger.error(f"Response content: {e.response.text}")
        raise HTTPException(status_code=500, detail=error_detail)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
