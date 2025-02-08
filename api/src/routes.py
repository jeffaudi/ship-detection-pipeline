"""Routes module for the API."""

from typing import Any, Dict, Tuple, Union

import requests
from flask import Blueprint, Response, request
from flask.wrappers import Response as FlaskResponse

from .middleware import require_api_key
from .services.annotation_service import AnnotationService
from .services.detection_service import DetectionService
from .services.sentinel_service import SentinelService

api_bp = Blueprint("api", __name__)

# Initialize services
sentinel_service = SentinelService()
detection_service = DetectionService()
annotation_service = AnnotationService()


def configure_options_handler(app):
    """Configure OPTIONS request handler.

    Args:
        app: The Flask application instance.
    """

    @app.before_request
    def handle_options() -> Union[None, Tuple[str, int]]:
        """Handle OPTIONS requests."""
        if request.method == "OPTIONS":
            return "", 200
        return None


@api_bp.route("/health", methods=["GET"])
def health_check() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint to verify API and service status.

    Returns:
        Tuple containing the response data and status code.
    """
    try:
        # Check services
        services_status = {"sentinel_api": False, "supabase": False, "api": True}

        # Check CDSE API connection
        try:
            # Get access token and make a simple query
            token = sentinel_service._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
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

        # Check Supabase connection
        try:
            sentinel_service.supabase.table("sentinel2_images").select("*").limit(1).execute()
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


# Sentinel image routes
@api_bp.route("/sentinel/search", methods=["POST"])
@require_api_key
def search_images() -> Tuple[Dict[str, Any], int]:
    """Search for Sentinel images based on provided criteria.

    Returns:
        Tuple containing the response data and status code.
    """
    try:
        print("Received request to /sentinel/search")
        data = request.get_json()
        print(f"Request data: {data}")

        if not data:
            print("No data provided in request")
            return {"error": "No data provided"}, 400

        bbox = data.get("bbox")
        if not bbox or len(bbox) != 2 or len(bbox[0]) != 2 or len(bbox[1]) != 2:
            print(f"Invalid bbox format: {bbox}")
            return {"error": "Invalid bbox format"}, 400

        print(
            f"Searching with parameters: bbox={bbox}, date_from={data.get('date_from')}, date_to={data.get('date_to')}, cloud_cover={data.get('cloud_cover', 20)}"  # noqa: E501
        )
        results = sentinel_service.search_images(
            bbox=bbox,
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            cloud_cover=data.get("cloud_cover", 20),
        )
        print(f"Raw results from sentinel_service: {results}")

        if isinstance(results, dict) and "error" in results:
            print(f"Search error: {results['error']}")
            return results, 400

        print(f"Found {len(results)} results")
        response = {"results": results}
        print(f"Sending response: {response}")
        return response, 200

    except Exception as e:
        print(f"Error in search_images: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}, 500


@api_bp.route("/sentinel/<image_id>", methods=["GET"])
@require_api_key
def get_image_metadata(image_id: str) -> Tuple[Dict[str, Any], int]:
    """Get metadata for a specific Sentinel image.

    Args:
        image_id: The ID of the Sentinel image.

    Returns:
        Tuple containing the response data and status code.
    """
    try:
        metadata = sentinel_service.get_metadata(image_id)
        return metadata, 200
    except Exception as e:
        return {"error": str(e)}, 400


@api_bp.route("/sentinel/<image_id>/quicklook", methods=["GET"])
@require_api_key
def get_image_quicklook(
    image_id: str,
) -> Union[FlaskResponse, Tuple[Dict[str, Any], int]]:
    """Get quicklook preview for a specific Sentinel image.

    Args:
        image_id: The ID of the Sentinel image.

    Returns:
        Either a Flask Response with the image or a tuple with error details and status code.
    """
    try:
        # Get access token
        token = sentinel_service._get_access_token()
        if not token:
            return {"error": "Failed to get access token"}, 401

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        # First, get the product with its Assets
        query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Id eq '{image_id}'&$expand=Assets"  # noqa: E501
        print(f"Requesting product with assets from: {query_url}")

        response = requests.get(query_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        print(f"Product response: {data}")

        if not data.get("value"):
            return {"error": "Product not found"}, 404

        product = data["value"][0]
        assets = product.get("Assets", [])

        # Find the quicklook asset
        quicklook_asset = next(
            (asset for asset in assets if asset.get("Type") == "QUICKLOOK"), None
        )

        if not quicklook_asset:
            return {"error": "Quicklook not found for this image"}, 404

        # Use the DownloadLink from the asset
        quicklook_url = quicklook_asset["DownloadLink"]
        headers["Accept"] = "image/jpeg"

        print(f"Requesting quicklook from: {quicklook_url}")
        response = requests.get(quicklook_url, headers=headers, stream=True)
        response.raise_for_status()

        # Forward the image response
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get("Content-Type", "image/jpeg"),
            status=response.status_code,
        )
    except requests.exceptions.RequestException as e:
        print(f"Error fetching quicklook: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response content: {e.response.text}")
        return {"error": str(e)}, 400


# Detection routes
@api_bp.route("/detect", methods=["POST"])
@require_api_key
def detect_ships() -> Tuple[Dict[str, Any], int]:
    """Detect ships in a given image.

    Returns:
        Tuple containing the response data and status code.
    """
    data = request.json
    try:
        results = detection_service.detect_ships(
            image_id=data["image_id"],
            bbox=data.get("bbox"),
            confidence=data.get("confidence", 0.5),
        )
        return results, 200
    except Exception as e:
        return {"error": str(e)}, 400


@api_bp.route("/detections/<detection_id>", methods=["GET"])
@require_api_key
def get_detection(detection_id: str) -> Tuple[Dict[str, Any], int]:
    """Get detection results for a specific detection ID.

    Args:
        detection_id: The ID of the detection.

    Returns:
        Tuple containing the response data and status code.
    """
    try:
        detection = detection_service.get_detection(detection_id)
        return detection, 200
    except Exception as e:
        return {"error": str(e)}, 400


# Annotation routes
@api_bp.route("/annotations", methods=["POST"])
@require_api_key
def create_annotation() -> Tuple[Dict[str, Any], int]:
    """Create a new annotation.

    Returns:
        Tuple containing the response data and status code.
    """
    data = request.json
    try:
        annotation = annotation_service.create_annotation(data)
        return annotation, 200
    except Exception as e:
        return {"error": str(e)}, 400


@api_bp.route("/annotations/<annotation_id>", methods=["PUT"])
@require_api_key
def update_annotation(annotation_id: str) -> Tuple[Dict[str, Any], int]:
    """Update an existing annotation.

    Args:
        annotation_id: The ID of the annotation to update.

    Returns:
        Tuple containing the response data and status code.
    """
    data = request.json
    try:
        updated = annotation_service.update_annotation(annotation_id, data)
        return updated, 200
    except Exception as e:
        return {"error": str(e)}, 400
