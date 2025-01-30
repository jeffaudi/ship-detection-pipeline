"""TiTiler application for serving Cloud Optimized GeoTIFF (COG) files.

This module provides a FastAPI application that serves COG files with tile, info,
and preview endpoints.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
import pyproj
from cachetools import TTLCache, cached
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageFilter
from rio_tiler.io import COGReader
from rio_tiler.utils import render
from supabase import Client, create_client

from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.mosaic.errors import MOSAIC_STATUS_CODES

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

# Initialize FastAPI
app = FastAPI(
    title="TiTiler for COGs",
    description="A simple TiTiler application to serve COG files from local and Google Cloud Storage",  # noqa: E501
)

# Configure GDAL for GCS authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/app/credentials.json"
os.environ["GDAL_HTTP_COOKIEFILE"] = "/vsimem/cookies.txt"
os.environ["GDAL_HTTP_COOKIEJAR"] = "/vsimem/cookies.txt"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
os.environ["VSI_CACHE"] = "TRUE"
os.environ["VSI_CACHE_SIZE"] = "1000000"

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

# Create router with custom prefix
router = APIRouter()

# Initialize a cache for COG readers with a 5-minute TTL
cog_cache = TTLCache(maxsize=100, ttl=300)


@cached(cog_cache)
def get_cog_reader(file_path: str) -> COGReader:
    """Get a cached COG reader for the given file path."""
    return COGReader(file_path, options={"nodata": 0, "resampling_method": "lanczos"})


async def get_cog_status(identifier: str) -> Dict[str, Any]:
    """Get the status of a COG from Supabase.

    Args:
        identifier: The Sentinel-2 image identifier.

    Returns:
        Dict containing the status and location information if available.
    """
    try:
        logger.info(f"Checking COG status for identifier: {identifier}")
        response = (
            supabase.table("sentinel2_cogs").select("*").eq("identifier", identifier).execute()
        )

        logger.info(f"Supabase response: {response.data}")

        if not response.data:
            logger.info(f"No COG found for identifier: {identifier}")
            return {"status": "not_available"}

        cog_info = response.data[0]
        status = cog_info.get("status")
        logger.info(f"Found COG with status: {status}")

        if status == "ready":
            result = {
                "status": "ready",
                "bucket": cog_info.get("bucket"),
                "path": cog_info.get("path"),
                "uri": f"gs://{cog_info['bucket']}/{cog_info['path']}",
            }
            logger.info(f"Returning COG info: {result}")
            return result
        elif status == "processing":
            return {"status": "processing"}
        else:
            return {"status": "not_available"}

    except Exception as e:
        logger.error(f"Error checking COG status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check COG status: {str(e)}")


@router.get("/status/{identifier}")
async def check_cog_status(identifier: str) -> Dict[str, Any]:
    """Check the status of a COG.

    Args:
        identifier: The Sentinel-2 image identifier.

    Returns:
        Dict containing the status and location information if available.
    """
    return await get_cog_status(identifier)


def parse_path(path: str) -> str:
    """Parse the input path and return the appropriate URI for COGReader.

    Handles both local files and Google Cloud Storage URLs.
    """
    if path.startswith("local/"):
        # Assume local file
        file_path = Path(__file__).parent / path
        return str(file_path)
    else:
        return f"gs://{path}"


# Debug middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Response:
    """Log incoming requests and their responses.

    Args:
        request: The incoming request.
        call_next: The next middleware or route handler.

    Returns:
        The response from the next handler.
    """
    import time

    start_time = time.time()

    logger.info(f"Request path: {request.url.path}")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request query params: {request.query_params}")
    logger.debug(f"Request path params: {request.path_params}")

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"Request completed in {process_time:.2f}ms - {request.method} {request.url.path} - {response.status_code}"  # noqa: E501
    )

    return response


@router.get("/info/{path:path}")
async def info(path: str) -> Dict[str, Any]:
    """Get COG info.

    Args:
        path: Path to the COG file (local path or GCS URL).

    Returns:
        Dict containing the COG metadata and geographic bounds.

    Raises:
        HTTPException: If the file is not found or cannot be read.
    """
    logger.debug(f"Getting info for path: {path}")
    try:
        file_path = parse_path(path)
        logger.info(f"In /info using file path: {file_path}")

        reader = get_cog_reader(file_path)
        # Get the basic info
        info_dict = dict(reader.info())
        logger.debug(f"Info dictionary: {info_dict}")

        # Get the source CRS and bounds
        src_crs = reader.crs
        bounds = reader.bounds

        # Transform bounds to WGS84 (EPSG:4326)
        transformer = pyproj.Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
        west, south = transformer.transform(bounds[0], bounds[1])
        east, north = transformer.transform(bounds[2], bounds[3])

        # Add geographic bounds to the dictionary
        info_dict["geographic_bounds"] = [west, south, east, north]
        logger.debug(f"Geographic bounds: {info_dict['geographic_bounds']}")

        return info_dict

    except Exception as e:
        logger.error(f"Error getting info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{path:path}")
async def preview(path: str) -> Dict[str, Union[List[List[float]], List[float]]]:
    """Get COG preview.

    Args:
        path: Path to the COG file (local path or GCS URL).

    Returns:
        Dict containing preview data and bounds.

    Raises:
        HTTPException: If the file is not found or cannot be read.
    """
    logger.debug(f"Getting preview for path: {path}")
    try:
        file_path = parse_path(path)
        logger.info(f"In /preview using file path: {file_path}")

        with COGReader(file_path) as cog:
            data = cog.preview()
            return {
                "data": data.data.tolist(),
                "bounds": data.bounds,
            }
    except Exception as e:
        logger.error(f"Error getting preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Parameters to make the tiles look smoother about 14 zoom level
# TODO: make the zoom level based on the actual resolution of the image
GAUSSIAN_BLUR = True
BUFFER = 2


@router.get("/tiles/{path:path}/{z}/{x}/{y}")
async def tiles(path: str, z: int, x: int, y: int) -> Response:
    """Get map tile.

    Args:
        path: Path to the COG file (local path or GCS URL).
        z: Zoom level.
        x: Tile X coordinate.
        y: Tile Y coordinate.

    Returns:
        PNG image tile.

    Raises:
        HTTPException: If the file is not found or tile cannot be generated.
    """
    logger.debug(f"Getting tile {z}/{x}/{y} for path: {path}")
    try:
        file_path = parse_path(path)
        logger.info(f"In /tiles/{z}/{x}/{y} using file path: {file_path}")

        # Return empty tile for zoom levels < 4
        if z < 4:
            logger.info(f"Returning empty tile for low zoom level: {z}")
            empty_tile = np.zeros((4, 256, 256), dtype=np.uint8)
            content = render(empty_tile, img_format="PNG")
            return Response(
                content=content,
                media_type="image/png",
                headers={"Content-Type": "image/png", "Cache-Control": "public, max-age=3600"},
            )

        # Use cached reader
        reader = get_cog_reader(file_path)

        # Get dataset info including overviews
        info = reader.info()
        logger.debug(f"Info dictionary: {info}")
        overviews = info.overviews
        logger.debug(f"Available overviews: {overviews}")

        # Get source CRS and bounds
        src_crs = reader.crs
        bounds = reader.bounds
        logger.debug(f"Source CRS: {src_crs}, bounds: {bounds}")

        # Configure tile reading options - absolute minimum
        tile_options = {
            "resampling_method": "nearest",  # "lanczos", #"cubic", #"bilinear",
            "force_binary_mask": False,
            "buffer": float(BUFFER),
        }

        try:
            # Get the tile using rio-tiler
            tile = reader.tile(x, y, z, **tile_options)
            logger.debug(f"Generated tile at zoom {z} with shape {tile.data.shape}")

            # For RGB images, we expect 3 bands
            if tile.data.shape[0] == 3:
                # Scale data to 8-bit if necessary
                data = np.clip(tile.data, 0, 255).astype(np.uint8)

                # Get the mask from the tile data if not provided
                mask = tile.mask
                if mask is None:
                    # For RGB, create mask where any band has data
                    mask = np.any(data > 0, axis=0)

                # if zoom level is 14 and up, apply a gaussian blur to the image
                if GAUSSIAN_BLUR and z >= 14:
                    # convert data to PIL image
                    pil_image = Image.fromarray(data.transpose(1, 2, 0))
                    # apply a gaussian blur to the image
                    pil_image = pil_image.filter(ImageFilter.GaussianBlur(radius=1))
                    # convert back to numpy array
                    data = np.array(pil_image).transpose(2, 0, 1).astype(np.uint8)

                # remove the buffer around the image
                data = data[:, BUFFER:-BUFFER, BUFFER:-BUFFER]

                logger.debug(
                    f"Rendering tile with data shape {data.shape} and mask shape {mask.shape}"
                )
                # Convert tile data to PNG with mask
                content = render(data, img_format="PNG", colormap=None, mask=mask)

                return Response(
                    content=content,
                    media_type="image/png",
                    headers={
                        "Content-Type": "image/png",
                        "Cache-Control": "public, max-age=3600",  # Cache tiles for 1 hour
                    },
                )
            else:
                logger.warning(f"Unexpected number of bands: {tile.data.shape[0]}")
                raise ValueError(f"Expected 3 bands, got {tile.data.shape[0]}")

        except Exception as tile_error:
            logger.error(f"Error getting tile data: {str(tile_error)}")
            # Create a transparent tile (256x256 RGBA)
            empty_tile = np.zeros((4, 256, 256), dtype=np.uint8)
            content = render(empty_tile, img_format="PNG")
            return Response(
                content=content,
                media_type="image/png",
                headers={"Content-Type": "image/png", "Cache-Control": "public, max-age=3600"},
            )

    except Exception as e:
        logger.error(f"Error getting tile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Add custom router with /cog prefix
app.include_router(router, prefix="/cog", tags=["TiTiler"])

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)


@app.get("/")
async def read_root() -> RedirectResponse:
    """Redirect to the test page.

    Returns:
        RedirectResponse to the static index.html page.
    """
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict containing the service health status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
