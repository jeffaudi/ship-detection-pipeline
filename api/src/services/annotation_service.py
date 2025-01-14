"""Service for managing annotations."""

import os
from typing import Any, Dict

from supabase import Client, create_client


class AnnotationService:
    """Service for managing annotations in the database."""

    def __init__(self) -> None:
        """Initialize the AnnotationService with Supabase client."""
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_KEY", "")
        self.supabase: Client = create_client(url, key)

    def create_annotation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new annotation."""
        try:
            response = (
                self.supabase.table("annotations")
                .insert(
                    {
                        "image_id": data["image_id"],
                        "bbox": data["bbox"],
                        "label": data["label"],
                        "confidence": data.get("confidence"),
                        "source": data.get("source", "manual"),
                        "metadata": data.get("metadata", {}),
                    }
                )
                .execute()
            )

            return response.data[0]

        except Exception as e:
            print(f"Error creating annotation: {str(e)}")
            raise

    def update_annotation(self, annotation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing annotation."""
        try:
            response = (
                self.supabase.table("annotations").update(data).eq("id", annotation_id).execute()
            )

            return response.data[0]

        except Exception as e:
            print(f"Error updating annotation: {str(e)}")
            raise
