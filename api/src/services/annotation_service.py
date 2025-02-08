"""Service for managing ship detection annotations."""

from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from ..config import Config


class AnnotationService:
    """Service for managing ship detection annotations."""

    def __init__(self) -> None:
        """Initialize the AnnotationService."""
        # Initialize Supabase client
        supabase_url = Config.get_supabase_url()
        supabase_key = Config.get_supabase_key()
        self.supabase: Client = create_client(supabase_url, supabase_key)

    def create_annotation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new annotation.

        Args:
            data: Dictionary containing annotation data including:
                - image_id: ID of the Sentinel image
                - bbox: Bounding box coordinates [[lon1, lat1], [lon2, lat2]]
                - type: Type of the annotation (e.g., "ship", "not_ship")
                - confidence: Confidence score (optional)
                - metadata: Additional metadata (optional)

        Returns:
            A dictionary containing the created annotation data.
        """
        try:
            # Validate required fields
            required_fields = ["image_id", "bbox", "type"]
            for field in required_fields:
                if field not in data:
                    return {"error": f"Missing required field: {field}"}

            # Create annotation
            response = self.supabase.table("annotations").insert(data).execute()
            if not response.data:
                return {"error": "Failed to create annotation"}

            created_annotation: Dict[str, Any] = response.data[0]
            return created_annotation

        except Exception as e:
            print(f"Error in create_annotation: {str(e)}")
            return {"error": str(e)}

    def update_annotation(self, annotation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing annotation.

        Args:
            annotation_id: The ID of the annotation to update.
            data: Dictionary containing updated annotation data.

        Returns:
            A dictionary containing the updated annotation data.
        """
        try:
            # Update annotation
            response = (
                self.supabase.table("annotations").update(data).eq("id", annotation_id).execute()
            )
            if not response.data:
                return {"error": "Annotation not found"}

            updated_annotation: Dict[str, Any] = response.data[0]
            return updated_annotation

        except Exception as e:
            print(f"Error in update_annotation: {str(e)}")
            return {"error": str(e)}

    def get_annotations(
        self, image_id: Optional[str] = None, type: Optional[str] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """Get annotations with optional filtering.

        Args:
            image_id: Optional ID of the Sentinel image to filter by.
            type: Optional type of annotations to filter by.

        Returns:
            A list of annotation dictionaries or an error dictionary.
        """
        try:
            query = self.supabase.table("annotations").select("*")

            if image_id:
                query = query.eq("image_id", image_id)
            if type:
                query = query.eq("type", type)

            response = query.execute()
            annotations: List[Dict[str, Any]] = response.data
            return annotations

        except Exception as e:
            print(f"Error in get_annotations: {str(e)}")
            return {"error": str(e)}

    def delete_annotation(self, annotation_id: str) -> Dict[str, Any]:
        """Delete an annotation.

        Args:
            annotation_id: The ID of the annotation to delete.

        Returns:
            A dictionary containing the result of the deletion.
        """
        try:
            response = self.supabase.table("annotations").delete().eq("id", annotation_id).execute()
            if not response.data:
                return {"error": "Annotation not found"}

            return {"message": "Annotation deleted successfully"}

        except Exception as e:
            print(f"Error in delete_annotation: {str(e)}")
            return {"error": str(e)}
