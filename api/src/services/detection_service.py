"""Service for ship detection."""

import os
from typing import Any, Dict, Optional

from supabase import Client, create_client


class DetectionService:
    """Service for ship detection in images."""

    def __init__(self) -> None:
        """Initialize the DetectionService with Supabase client."""
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_KEY", "")
        self.supabase: Client = create_client(url, key)

    def detect_ships(
        self, image_id: str, bbox: Optional[list] = None, confidence: float = 0.5
    ) -> Dict[str, Any]:
        """Run ship detection on an image."""
        try:
            # Get image metadata
            image = (
                self.supabase.table("sentinel_images")
                .select("*")
                .eq("product_id", image_id)
                .single()
                .execute()
            )

            if not image.data:
                raise Exception("Image not found")

            # Run detection (mocked for now)
            detections: list[Dict[str, Any]] = []  # Placeholder for actual detection logic

            # Store results in Supabase
            detection_id = (
                self.supabase.table("detections")
                .insert(
                    {
                        "image_id": image_id,
                        "bbox": bbox,
                        "confidence_threshold": confidence,
                        "results": detections,
                        "status": "completed",
                    }
                )
                .execute()
            )

            return {"detection_id": detection_id, "results": detections}

        except Exception as e:
            print(f"Error running detection: {str(e)}")
            raise

    def get_detection(self, detection_id: str) -> Dict[str, Any]:
        """Get detection results from the database."""
        try:
            response = (
                self.supabase.table("detections")
                .select("*")
                .eq("id", detection_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            print(f"Error getting detection: {str(e)}")
            raise
