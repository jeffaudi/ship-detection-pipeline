"""Routes module for the API."""

import requests
from flask import Blueprint, Response, jsonify, request

from .services.annotation_service import AnnotationService
from .services.detection_service import DetectionService
from .services.sentinel_service import SentinelService

api_bp = Blueprint("api", __name__)

# Initialize services
sentinel_service = SentinelService()
detection_service = DetectionService()
annotation_service = AnnotationService()


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify API and service status."""
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
            sentinel_service.supabase.table("sentinel_images").select("*").limit(1).execute()
            services_status["supabase"] = True
        except Exception as e:
            print(f"Supabase error: {str(e)}")
            services_status["supabase"] = False

        return jsonify({"status": "healthy", "services": services_status, "version": "0.1.0"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


# Sentinel image routes
@api_bp.route("/sentinel/search", methods=["POST"])
def search_images():
    """Search for Sentinel images based on provided criteria."""
    try:
        data = request.get_json()
        print(f"Received search request with data: {data}")

        if not data:
            return jsonify({"error": "No data provided"}), 400

        bbox = data.get("bbox")
        if not bbox or len(bbox) != 2 or len(bbox[0]) != 2 or len(bbox[1]) != 2:
            return jsonify({"error": "Invalid bbox format"}), 400

        results = sentinel_service.search_images(
            bbox=bbox,
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            cloud_cover=data.get("cloud_cover", 20),
        )

        if isinstance(results, dict) and "error" in results:
            return jsonify(results), 400

        print(f"Received {len(results)} results.")
        return jsonify(results)

    except Exception as e:
        print(f"Error in search_images: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/sentinel/<image_id>", methods=["GET"])
def get_image_metadata(image_id):
    """Get metadata for a specific Sentinel image."""
    try:
        metadata = sentinel_service.get_metadata(image_id)
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/sentinel/<image_id>/quicklook", methods=["GET"])
def get_image_quicklook(image_id):
    """Get quicklook preview for a specific Sentinel image."""
    try:
        # Get access token
        token = sentinel_service._get_access_token()
        if not token:
            return jsonify({"error": "Failed to get access token"}), 401

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        # First, get the product with its Assets
        query_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Id eq '{image_id}'&$expand=Assets"  # noqa: E501
        print(f"Requesting product with assets from: {query_url}")

        response = requests.get(query_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        print(f"Product response: {data}")

        if not data.get("value"):
            return jsonify({"error": "Product not found"}), 404

        product = data["value"][0]
        assets = product.get("Assets", [])

        # Find the quicklook asset
        quicklook_asset = next(
            (asset for asset in assets if asset.get("Type") == "QUICKLOOK"), None
        )

        if not quicklook_asset:
            return jsonify({"error": "Quicklook not found for this image"}), 404

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
        if hasattr(e.response, "text"):
            print(f"Response content: {e.response.text}")
        return jsonify({"error": str(e)}), 400


# Detection routes
@api_bp.route("/detect", methods=["POST"])
def detect_ships():
    """Detect ships in a given image."""
    data = request.json
    try:
        results = detection_service.detect_ships(
            image_id=data["image_id"], bbox=data.get("bbox"), confidence=data.get("confidence", 0.5)
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/detections/<detection_id>", methods=["GET"])
def get_detection(detection_id):
    """Get detection results for a specific detection ID."""
    try:
        detection = detection_service.get_detection(detection_id)
        return jsonify(detection)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Annotation routes
@api_bp.route("/annotations", methods=["POST"])
def create_annotation():
    """Create a new annotation."""
    data = request.json
    try:
        annotation = annotation_service.create_annotation(data)
        return jsonify(annotation)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route("/annotations/<annotation_id>", methods=["PUT"])
def update_annotation(annotation_id):
    """Update an existing annotation."""
    data = request.json
    try:
        updated = annotation_service.update_annotation(annotation_id, data)
        return jsonify(updated)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
