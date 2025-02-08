"""Service for ship detection in satellite images."""

import json
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from ..config import Config


class DetectionService:
    """Service for ship detection in satellite images."""

    def __init__(self) -> None:
        """Initialize the DetectionService."""
        # Initialize Supabase client
        supabase_url = Config.get_supabase_url()
        supabase_key = Config.get_supabase_key()
        self.supabase: Client = create_client(supabase_url, supabase_key)

    def detect_ships(
        self,
        image_id: str,
        bbox: Optional[List[List[float]]] = None,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Detect ships in a Sentinel image.

        Args:
            image_id: The ID of the Sentinel image.
            bbox: Optional bounding box to limit detection area [[lon1, lat1], [lon2, lat2]].
            confidence: Minimum confidence threshold for detections (default: 0.5).

        Returns:
            A dictionary containing the detection results.
        """
        try:
            # Check if we have cached results
            response = (
                self.supabase.table("ship_detections")
                .select("*")
                .eq("image_id", image_id)
                .execute()
            )
            if response.data:
                print("Found detection results in cache")
                cached_results: Dict[str, Any] = json.loads(response.data[0]["results"])
                return cached_results

            # TODO: Implement actual ship detection logic here
            # For now, return mock data
            results: Dict[str, Any] = {
                "image_id": image_id,
                "bbox": bbox,
                "confidence_threshold": confidence,
                "detections": [
                    {
                        "id": "mock_detection_1",
                        "confidence": 0.85,
                        "bbox": [[12.5, 41.9], [12.51, 41.91]],
                        "type": "ship",
                    }
                ],
            }

            # Cache results
            self.supabase.table("ship_detections").insert(
                {"image_id": image_id, "results": json.dumps(results)}
            ).execute()

            return results

        except Exception as e:
            print(f"Error in detect_ships: {str(e)}")
            return {"error": str(e)}

    def get_detection(self, detection_id: str) -> Dict[str, Any]:
        """Get detection results for a specific detection ID.

        Args:
            detection_id: The ID of the detection.

        Returns:
            A dictionary containing the detection results.
        """
        try:
            response = (
                self.supabase.table("ship_detections").select("*").eq("id", detection_id).execute()
            )
            if not response.data:
                return {"error": "Detection not found"}

            detection_data: Dict[str, Any] = json.loads(response.data[0]["results"])
            return detection_data

        except Exception as e:
            print(f"Error in get_detection: {str(e)}")
            return {"error": str(e)}
