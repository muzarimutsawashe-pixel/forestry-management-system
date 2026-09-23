from pydantic import BaseModel
from typing import Optional


# ============================================================
# LOGIN REQUEST
# ============================================================

class LoginRequest(BaseModel):

    username: str

    password: str


# ============================================================
# USER CREATION
# ============================================================

class UserCreate(BaseModel):

    username: str

    password: str

    role: str


# ============================================================
# CREATE COMPARTMENT
# ============================================================

class CompartmentCreate(BaseModel):

    estate_id: int

    compartment_code: str

    species: Optional[str] = None

    planting_year: Optional[int] = None

    area_planted: Optional[float] = None

    area_compartment: Optional[float] = None

    status: Optional[str] = None

    age: Optional[int] = None

    block_id: Optional[str] = None


# ============================================================
# UPDATE COMPARTMENT
# ============================================================

class CompartmentUpdate(BaseModel):

    estate_id: Optional[int] = None

    compartment_code: Optional[str] = None

    species: Optional[str] = None

    planting_year: Optional[int] = None

    area_planted: Optional[float] = None

    area_compartment: Optional[float] = None

    status: Optional[str] = None

    age: Optional[int] = None

    block_id: Optional[str] = None


# ============================================================
# ESTATE RESPONSE
# ============================================================

class EstateResponse(BaseModel):

    estate_id: int

    estate_name: str


# ============================================================
# COMPARTMENT RESPONSE
# ============================================================

class CompartmentResponse(BaseModel):

    compartment_id: int

    estate_id: int

    compartment_code: Optional[str] = None

    species: Optional[str] = None

    planting_year: Optional[int] = None

    area_planted: Optional[float] = None

    area_compartment: Optional[float] = None

    status: Optional[str] = None

    age: Optional[int] = None

    block_id: Optional[str] = None


# ============================================================
# LOGIN RESPONSE
# ============================================================

class LoginResponse(BaseModel):

    success: bool

    token: str

    username: str

    role: str

    estate_id: Optional[int] = None


# ============================================================
# STATISTICS RESPONSE
# ============================================================

class StatisticsResponse(BaseModel):

    total_compartments: int

    total_area: float

    average_age: float

    species_count: int

    species: list[str]


# ============================================================
# USER RESPONSE
# ============================================================

class UserResponse(BaseModel):

    username: str

    role: str


# ============================================================
# SUCCESS RESPONSE
# ============================================================

class SuccessResponse(BaseModel):

    success: bool

    message: str


# ============================================================
# DELETE RESPONSE
# ============================================================

class DeleteCompartmentResponse(BaseModel):

    success: bool

    message: str

    compartment_id: int

    compartment_code: Optional[str] = None


# ============================================================
# SILVICULTURE OPERATIONS
# ============================================================

class SilvicultureOperationCreate(BaseModel):

    operation_type: str

    operation_date: Optional[object] = None

    area_treated: Optional[float] = None

    status: Optional[str] = "completed"

    remarks: Optional[str] = None

    recorded_by: Optional[str] = None


class SilvicultureOperationUpdate(BaseModel):

    operation_type: Optional[str] = None

    operation_date: Optional[object] = None

    area_treated: Optional[float] = None

    status: Optional[str] = None

    remarks: Optional[str] = None

    recorded_by: Optional[str] = None


class SilvicultureOperationResponse(BaseModel):

    operation_id: int

    compartment_id: int

    operation_type: Optional[str] = None

    operation_date: Optional[object] = None

    operation_date_display: Optional[str] = None

    area_treated: Optional[float] = None

    status: Optional[str] = None

    remarks: Optional[str] = None

    recorded_by: Optional[str] = None

    model_config = {"from_attributes": True}