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
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from rio_tiler.io import COGReader
from rio_tiler.utils import render

from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.mosaic.errors import MOSAIC_STATUS_CODES

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="TiTiler for COGs",
    description="A simple TiTiler application to serve COG files",
)

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
    logger.debug(f"Request path: {request.url.path}")
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request query params: {request.query_params}")
    logger.debug(f"Request path params: {request.path_params}")
    response = await call_next(request)
    logger.debug(f"Response status: {response.status_code}")
    return response


# Create router with custom prefix
router = APIRouter()


@router.get("/info/{path:path}")
async def info(path: str) -> Dict[str, Any]:
    """Get COG info.

    Args:
        path: Path to the COG file.

    Returns:
        Dict containing the COG metadata and geographic bounds.

    Raises:
        HTTPException: If the file is not found or cannot be read.
    """
    logger.debug(f"Getting info for path: {path}")
    try:
        # Construct absolute path from the app directory
        file_path = Path(__file__).parent / path
        logger.info(f"Looking for file at: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with COGReader(str(file_path)) as cog:
            # Get the basic info
            info_dict = dict(cog.info())

            # Get the source CRS and bounds
            src_crs = cog.crs
            bounds = cog.bounds

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
        path: Path to the COG file.

    Returns:
        Dict containing preview data and bounds.

    Raises:
        HTTPException: If the file is not found or cannot be read.
    """
    logger.debug(f"Getting preview for path: {path}")
    try:
        # Construct absolute path from the app directory
        file_path = Path(__file__).parent / path
        logger.info(f"Looking for file at: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with COGReader(str(file_path)) as cog:
            data = cog.preview()
            return {
                "data": data.data.tolist(),
                "bounds": data.bounds,
            }
    except Exception as e:
        logger.error(f"Error getting preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiles/{path:path}/{z}/{x}/{y}")
async def tiles(path: str, z: int, x: int, y: int) -> Response:
    """Get map tile.

    Args:
        path: Path to the COG file.
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
        # Construct absolute path from the app directory
        file_path = Path(__file__).parent / path
        logger.info(f"Looking for file at: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with COGReader(str(file_path)) as cog:
            # Get bounds and CRS
            bounds = cog.bounds
            src_crs = cog.crs
            logger.debug(f"COG bounds: {bounds}")
            logger.debug(f"COG CRS: {src_crs}")

            try:
                # Get the tile using rio-tiler (it handles the reprojection internally)
                tile = cog.tile(x, y, z)

                # Get the mask from the tile data
                mask = tile.mask
                if mask is None:
                    # If no mask provided, create one based on non-zero values
                    mask = np.any(tile.data > 0, axis=0)

                # Convert tile data to PNG with mask
                content = render(tile.data, img_format="PNG", colormap=None, mask=mask)

                return Response(content=content, media_type="image/png")

            except Exception as tile_error:
                logger.debug(
                    f"Error getting tile data: {str(tile_error)}. Returning transparent tile."
                )
                # Create a transparent tile (256x256 RGBA)
                empty_tile = np.zeros((4, 256, 256), dtype=np.uint8)
                content = render(empty_tile, img_format="PNG")
                return Response(content=content, media_type="image/png")

    except FileNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))
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
