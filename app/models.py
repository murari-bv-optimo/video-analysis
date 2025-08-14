from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class RoomFeatures(BaseModel):
    wiring: Dict[str, Any] = Field(..., description="Electrical system status")
    hvac: Dict[str, Any] = Field(..., description="HVAC systems")
    flooring: Dict[str, Any] = Field(..., description="Flooring material and condition")
    walls: Dict[str, Any] = Field(..., description="Wall condition and paint")
    ceiling: Dict[str, Any] = Field(..., description="Ceiling material and condition")
    doors_and_windows: Dict[str, Any] = Field(..., description="Doors and windows")
    fixtures: Dict[str, Any] = Field(..., description="All fixtures")
    furnishings: List[Dict[str, Any]] = Field(..., description="Furniture items")
    kitchen_appliances: Dict[str, Any] = Field(..., description="Kitchen appliances")
    balcony: Dict[str, Any] = Field(..., description="Balcony details")

class ObjectCounts(BaseModel):
    sofa: int = Field(0, description="Number of sofas")
    table: int = Field(0, description="Number of tables")
    chair: int = Field(0, description="Number of chairs")
    mirror: int = Field(0, description="Number of mirrors")
    fan: int = Field(0, description="Number of fans")
    light: int = Field(0, description="Number of lights")
    plant: int = Field(0, description="Number of plants")
    frame: int = Field(0, description="Number of frames")
    window: int = Field(0, description="Number of windows")
    wardrobe: int = Field(0, description="Number of wardrobes")
    cooking_stove: int = Field(0, description="Number of cooking stoves")
    curtain: int = Field(0, description="Number of curtains")
    decoration: int = Field(0, description="Number of decorations")

class RoomExtractionSchema(BaseModel):
    room_id: str = Field(..., description="Unique identifier for the room")
    room_type: str = Field(..., description="Type of room")
    estimated_area_sqm: float = Field(..., description="Estimated room area")
    features: RoomFeatures = Field(..., description="Detailed room features")
    object_counts: ObjectCounts = Field(..., description="Count of all objects")

class AIAgentInstructions(BaseModel):
    information: str = Field("Analyze room images for detailed assessment", description="Context information")
    instruction: str = Field("Extract comprehensive room details", description="Main instruction")
    condition: str = Field("Provide accurate counts and estimates", description="Analysis conditions")

class UploadResponse(BaseModel):
    message: str
    house_id: str
    total_images: int
    processing_status: str

class AnalysisResult(BaseModel):
    house_id: str
    status: str
    total_rooms: int
    processing_time: float
    output_file: str
    report: Optional[Dict[str, Any]] = None
