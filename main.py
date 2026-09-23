from datetime import date as DateType
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
import bcrypt

from database import get_db
from models import Estate, Compartment, SilvicultureOperation
from schemas import (
    LoginRequest,
    LoginResponse,
    EstateResponse,
    CompartmentResponse,
    CompartmentCreate,
    CompartmentUpdate,
    SilvicultureOperationCreate,
    SilvicultureOperationUpdate,
    SilvicultureOperationResponse,
)
from auth import (
    create_access_token,
    get_current_user,
    require_forester,
    require_estate_manager,
    require_production_manager,
    require_admin,
    enforce_estate_scope,
    ROLE_LEVEL,
    VALID_ROLES,
    PERMISSIONS,
)
from chatbot import ask_assistant

app = FastAPI(
    title="Allied Timbers Zimbabwe Forestry Management System",
    version="1.0.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def _format_date_display(d):
    return d.strftime("%d/%m/%Y") if d else None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "success": True,
        "message": "Allied Timbers Forestry Management API is running",
        "version": "1.0"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"success": True, "database": "connected"}
    except Exception as e:
        raise HTTPException(500, f"Database connection failed: {str(e)}")


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    try:
        user = db.execute(
            text("""
                SELECT user_id, username, password_hash, role,
                       is_active, estate_id
                FROM users
                WHERE username = :username
                LIMIT 1
            """),
            {"username": login_data.username}
        ).mappings().first()

        if not user:
            raise HTTPException(401, "Invalid username or password")

        if not user["is_active"]:
            raise HTTPException(403, "This user account is inactive")

        password_valid = bcrypt.checkpw(
            login_data.password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )

        if not password_valid:
            raise HTTPException(401, "Invalid username or password")

        role = user["role"] or "forester"

        if role in ("forester", "estate_manager") and user["estate_id"] is None:
            raise HTTPException(
                403,
                "Your account is not linked to an estate. Contact your manager."
            )

        token = create_access_token(
            username=user["username"],
            role=role,
            estate_id=user["estate_id"],
        )

        return {
            "success":   True,
            "token":     token,
            "username":  user["username"],
            "role":      role,
            "estate_id": user["estate_id"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login failed: {str(e)}")


# ============================================================
# CURRENT USER INFO
# ============================================================

@app.get("/api/me")
def get_me(user: dict = Depends(get_current_user)):
    return {
        "username":  user["username"],
        "role":      user["role"],
        "estate_id": user["estate_id"],
        "level":     ROLE_LEVEL.get(user["role"], 0),
    }


@app.get("/api/permissions")
def get_permissions(user: dict = Depends(get_current_user)):
    return {
        "role":        user["role"],
        "estate_id":   user["estate_id"],
        "level":       ROLE_LEVEL.get(user["role"], 0),
        "permissions": PERMISSIONS.get(user["role"], []),
    }


# ============================================================
# AI CHATBOT
# ============================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = []


@app.post("/api/chat")
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    try:
        result = ask_assistant(
            message=data.message,
            history=[m.model_dump() for m in (data.history or [])],
            user=user,
            db=db,
        )

        # ask_assistant returns {reply, map_action} — unwrap reply to a string
        if isinstance(result, dict):
            reply = result.get("reply")
            map_action = result.get("map_action")
        else:
            reply = result
            map_action = None

        # Defensive: always send a string
        if reply is None:
            reply = "(no answer)"
        elif not isinstance(reply, str):
            reply = str(reply)

        return {
            "success":    True,
            "reply":      reply,
            "map_action": map_action,
        }

    except Exception as e:
        raise HTTPException(500, f"Assistant error: {str(e)}")


# ============================================================
# USER MANAGEMENT (admin only)
# ============================================================

class UserCreateAdmin(BaseModel):
    username: str
    password: str
    role: str
    estate_id: Optional[int] = None
    is_active: Optional[bool] = True


class UserUpdateAdmin(BaseModel):
    role: Optional[str] = None
    estate_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


@app.get("/api/users")
def list_users(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = db.execute(text("""
        SELECT u.user_id, u.username, u.role, u.estate_id,
               u.is_active, e.estate_name
        FROM users u
        LEFT JOIN estates e ON e.estate_id = u.estate_id
        ORDER BY u.user_id
    """)).mappings().all()
    return [dict(r) for r in rows]


@app.post("/api/users")
def create_user(
    data: UserCreateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if data.role not in VALID_ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(VALID_ROLES)}")

    if data.role in ("forester", "estate_manager") and data.estate_id is None:
        raise HTTPException(400, "Foresters and estate managers must be linked to an estate.")

    existing = db.execute(
        text("SELECT user_id FROM users WHERE username = :u"),
        {"u": data.username}
    ).first()

    if existing:
        raise HTTPException(409, "Username already exists")

    pw_hash = bcrypt.hashpw(
        data.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    new_id = db.execute(text("""
        INSERT INTO users (username, password_hash, role, estate_id, is_active)
        VALUES (:u, :p, :r, :e, :a)
        RETURNING user_id
    """), {
        "u": data.username,
        "p": pw_hash,
        "r": data.role,
        "e": data.estate_id,
        "a": data.is_active,
    }).scalar()

    db.commit()
    return {"success": True, "user_id": new_id, "message": "User created"}


@app.put("/api/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    user = db.execute(
        text("SELECT user_id FROM users WHERE user_id = :id"),
        {"id": user_id}
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    updates = []
    params = {"id": user_id}

    if data.role is not None:
        if data.role not in VALID_ROLES:
            raise HTTPException(400, "Invalid role")
        updates.append("role = :role")
        params["role"] = data.role

    if "estate_id" in data.model_fields_set:
        updates.append("estate_id = :estate_id")
        params["estate_id"] = data.estate_id

    if data.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = data.is_active

    if data.password:
        updates.append("password_hash = :pw")
        params["pw"] = bcrypt.hashpw(
            data.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    if not updates:
        raise HTTPException(400, "No fields to update")

    db.execute(
        text(f"UPDATE users SET {', '.join(updates)} WHERE user_id = :id"),
        params
    )
    db.commit()
    return {"success": True, "message": "User updated"}


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: dict = Depends(require_admin),
):
    row = db.execute(
        text("SELECT username FROM users WHERE user_id = :id"),
        {"id": user_id}
    ).first()

    if not row:
        raise HTTPException(404, "User not found")

    if current["username"] == row[0]:
        raise HTTPException(400, "You cannot delete your own account")

    db.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": user_id})
    db.commit()
    return {"success": True, "message": "User deleted"}


# ============================================================
# GET ALL ESTATES (scoped)
# ============================================================

@app.get("/api/estates")
def get_estates(
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    if user["role"] in ("production_manager", "admin"):
        estates = db.query(Estate).order_by(Estate.estate_id).all()
    else:
        estates = (
            db.query(Estate)
            .filter(Estate.estate_id == user["estate_id"])
            .order_by(Estate.estate_id)
            .all()
        )

    return [
        {"estate_id": e.estate_id, "estate_name": e.estate_name}
        for e in estates
    ]


@app.get("/api/estates/{estate_id}")
def get_estate(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    estate = (
        db.query(Estate)
        .filter(Estate.estate_id == estate_id)
        .first()
    )

    if not estate:
        raise HTTPException(404, "Estate not found")

    return {"estate_id": estate.estate_id, "estate_name": estate.estate_name}


# ============================================================
# GET COMPARTMENTS FOR ESTATE (scoped)
# ============================================================

@app.get("/api/estates/{estate_id}/compartments")
def get_compartments(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    try:
        compartments = (
            db.query(Compartment)
            .filter(Compartment.estate_id == estate_id)
            .order_by(Compartment.compartment_code)
            .all()
        )

        return [
            {
                "compartment_id": c.compartment_id,
                "estate_id": c.estate_id,
                "compartment_code": c.compartment_code,
                "species": c.species,
                "planting_year": c.planting_year,
                "area_planted": float(c.area_planted) if c.area_planted is not None else None,
                "area_compartment": float(c.area_compartment) if c.area_compartment is not None else None,
                "status": c.status,
                "age": c.age,
                "block_id": c.block_id,
            }
            for c in compartments
        ]

    except Exception as e:
        raise HTTPException(500, f"Unable to load compartments: {str(e)}")


# ============================================================
# GET SINGLE COMPARTMENT (scoped)
# ============================================================

@app.get("/api/compartments/{compartment_id}")
def get_compartment(
    compartment_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    return {
        "compartment_id": compartment.compartment_id,
        "estate_id": compartment.estate_id,
        "compartment_code": compartment.compartment_code,
        "species": compartment.species,
        "planting_year": compartment.planting_year,
        "area_planted": float(compartment.area_planted) if compartment.area_planted is not None else None,
        "area_compartment": float(compartment.area_compartment) if compartment.area_compartment is not None else None,
        "status": compartment.status,
        "age": compartment.age,
        "block_id": compartment.block_id,
    }


# ============================================================
# ADD COMPARTMENT (estate manager+)
# ============================================================

@app.post("/api/compartments")
def create_compartment(
    data: CompartmentCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_estate_manager),
):
    enforce_estate_scope(user, data.estate_id)

    try:
        compartment = Compartment(
            estate_id=data.estate_id,
            compartment_code=data.compartment_code,
            species=data.species,
            planting_year=data.planting_year,
            area_planted=data.area_planted,
            area_compartment=data.area_compartment,
            status=data.status,
            age=data.age,
            block_id=data.block_id,
        )

        db.add(compartment)
        db.commit()
        db.refresh(compartment)

        return {
            "success": True,
            "message": "Compartment created successfully",
            "compartment": {
                "compartment_id": compartment.compartment_id,
                "estate_id": compartment.estate_id,
                "compartment_code": compartment.compartment_code,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to create compartment: {str(e)}")


# ============================================================
# UPDATE COMPARTMENT (estate manager+)
# ============================================================

@app.put("/api/compartments/{compartment_id}")
def update_compartment(
    compartment_id: int,
    data: CompartmentUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_estate_manager),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    try:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(compartment, key, value)

        db.commit()
        db.refresh(compartment)

        return {
            "success": True,
            "message": "Compartment updated successfully",
            "compartment": {
                "compartment_id": compartment.compartment_id,
                "estate_id": compartment.estate_id,
                "compartment_code": compartment.compartment_code,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to update compartment: {str(e)}")


# ============================================================
# DELETE COMPARTMENT (estate manager+)
# ============================================================

@app.delete("/api/compartments/{compartment_id}")
def delete_compartment(
    compartment_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_estate_manager),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    try:
        code = compartment.compartment_code
        db.delete(compartment)
        db.commit()
        return {
            "success": True,
            "message": f"Compartment {code} deleted successfully",
            "compartment_id": compartment_id,
            "compartment_code": code,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to delete compartment: {str(e)}")


# ============================================================
# STATISTICS (scoped)
# ============================================================

@app.get("/api/estates/{estate_id}/statistics")
def get_statistics(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    try:
        total_compartments = (
            db.query(func.count(Compartment.compartment_id))
            .filter(Compartment.estate_id == estate_id)
            .scalar()
        ) or 0

        total_area = (
            db.query(func.coalesce(func.sum(Compartment.area_planted), 0))
            .filter(Compartment.estate_id == estate_id)
            .scalar()
        ) or 0

        average_age = (
            db.query(func.avg(Compartment.age))
            .filter(
                Compartment.estate_id == estate_id,
                Compartment.age.isnot(None)
            )
            .scalar()
        ) or 0

        species_count = (
            db.query(func.count(func.distinct(Compartment.species)))
            .filter(
                Compartment.estate_id == estate_id,
                Compartment.species.isnot(None)
            )
            .scalar()
        ) or 0

        species = (
            db.query(Compartment.species)
            .filter(
                Compartment.estate_id == estate_id,
                Compartment.species.isnot(None)
            )
            .distinct()
            .order_by(Compartment.species)
            .all()
        )

        return {
            "total_compartments": int(total_compartments),
            "total_area": float(total_area),
            "average_age": round(float(average_age), 2),
            "species_count": int(species_count),
            "species": [s[0] for s in species],
        }

    except Exception as e:
        raise HTTPException(500, f"Unable to calculate statistics: {str(e)}")


# ============================================================
# SILVICULTURE OPERATIONS
# ============================================================

@app.get(
    "/api/compartments/{compartment_id}/operations",
    response_model=list[SilvicultureOperationResponse],
)
def get_compartment_operations(
    compartment_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    ops = (
        db.query(SilvicultureOperation)
        .filter(SilvicultureOperation.compartment_id == compartment_id)
        .order_by(
            SilvicultureOperation.operation_date.nulls_last(),
            SilvicultureOperation.operation_type,
        )
        .all()
    )

    return ops


@app.get("/api/estates/{estate_id}/operations")
def get_estate_operations(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    try:
        rows = (
            db.query(SilvicultureOperation, Compartment)
            .join(
                Compartment,
                Compartment.compartment_id == SilvicultureOperation.compartment_id,
            )
            .filter(Compartment.estate_id == estate_id)
            .order_by(
                Compartment.compartment_code,
                SilvicultureOperation.operation_date.nulls_last(),
                SilvicultureOperation.operation_type,
            )
            .all()
        )

        return [
            {
                "operation_id": op.operation_id,
                "compartment_id": c.compartment_id,
                "compartment_code": c.compartment_code,
                "operation_type": op.operation_type,
                "operation_date": op.operation_date.isoformat() if op.operation_date else None,
                "operation_date_display": op.operation_date_display,
                "area_treated": float(op.area_treated) if op.area_treated is not None else None,
                "status": op.status,
                "remarks": op.remarks,
                "recorded_by": op.recorded_by,
            }
            for op, c in rows
        ]

    except Exception as e:
        raise HTTPException(500, f"Unable to load operations: {str(e)}")


@app.get(
    "/api/operations/{operation_id}",
    response_model=SilvicultureOperationResponse,
)
def get_operation(
    operation_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    op = (
        db.query(SilvicultureOperation)
        .filter(SilvicultureOperation.operation_id == operation_id)
        .first()
    )

    if not op:
        raise HTTPException(404, "Operation not found")

    cpt = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == op.compartment_id)
        .first()
    )

    if cpt:
        enforce_estate_scope(user, cpt.estate_id)

    return op


@app.post("/api/compartments/{compartment_id}/operations")
def create_operation(
    compartment_id: int,
    data: SilvicultureOperationCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    try:
        op = SilvicultureOperation(
            compartment_id=compartment_id,
            operation_type=data.operation_type,
            operation_date=data.operation_date,
            operation_date_display=_format_date_display(data.operation_date),
            area_treated=data.area_treated,
            status=data.status,
            remarks=data.remarks,
            recorded_by=data.recorded_by or user["username"],
            created_at=func.now(),
        )

        db.add(op)
        db.commit()
        db.refresh(op)

        return {
            "success": True,
            "message": "Operation recorded successfully",
            "operation": {
                "operation_id": op.operation_id,
                "compartment_id": op.compartment_id,
                "operation_type": op.operation_type,
                "operation_date": op.operation_date.isoformat() if op.operation_date else None,
                "operation_date_display": op.operation_date_display,
                "status": op.status,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to create operation: {str(e)}")


@app.put("/api/operations/{operation_id}")
def update_operation(
    operation_id: int,
    data: SilvicultureOperationUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    op = (
        db.query(SilvicultureOperation)
        .filter(SilvicultureOperation.operation_id == operation_id)
        .first()
    )

    if not op:
        raise HTTPException(404, "Operation not found")

    cpt = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == op.compartment_id)
        .first()
    )

    if cpt:
        enforce_estate_scope(user, cpt.estate_id)

    try:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(op, key, value)

        if "operation_date" in update_data:
            op.operation_date_display = _format_date_display(op.operation_date)

        db.commit()
        db.refresh(op)

        return {
            "success": True,
            "message": "Operation updated successfully",
            "operation": {
                "operation_id": op.operation_id,
                "compartment_id": op.compartment_id,
                "operation_type": op.operation_type,
                "operation_date": op.operation_date.isoformat() if op.operation_date else None,
                "operation_date_display": op.operation_date_display,
                "status": op.status,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to update operation: {str(e)}")


@app.delete("/api/operations/{operation_id}")
def delete_operation(
    operation_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_estate_manager),
):
    op = (
        db.query(SilvicultureOperation)
        .filter(SilvicultureOperation.operation_id == operation_id)
        .first()
    )

    if not op:
        raise HTTPException(404, "Operation not found")

    cpt = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == op.compartment_id)
        .first()
    )

    if cpt:
        enforce_estate_scope(user, cpt.estate_id)

    try:
        db.delete(op)
        db.commit()
        return {
            "success": True,
            "message": "Operation deleted successfully",
            "operation_id": operation_id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Unable to delete operation: {str(e)}")


@app.get("/api/compartments/{compartment_id}/operations/summary")
def get_operation_summary(
    compartment_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    compartment = (
        db.query(Compartment)
        .filter(Compartment.compartment_id == compartment_id)
        .first()
    )

    if not compartment:
        raise HTTPException(404, "Compartment not found")

    enforce_estate_scope(user, compartment.estate_id)

    try:
        ops = (
            db.query(SilvicultureOperation)
            .filter(SilvicultureOperation.compartment_id == compartment_id)
            .all()
        )

        if not ops:
            return {
                "compartment_id": compartment_id,
                "total": 0,
                "by_type": {},
                "last_operation_date": None,
            }

        by_type = {}
        for op in ops:
            by_type[op.operation_type] = by_type.get(op.operation_type, 0) + 1

        dated = [op.operation_date for op in ops if op.operation_date]

        return {
            "compartment_id": compartment_id,
            "total": len(ops),
            "by_type": by_type,
            "last_operation_date": max(dated).isoformat() if dated else None,
        }

    except Exception as e:
        raise HTTPException(500, f"Unable to summarise operations: {str(e)}")


# ============================================================
# MAP (scoped)
# ============================================================

@app.get("/api/estates/{estate_id}/map")
def get_estate_map(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    estate = (
        db.query(Estate)
        .filter(Estate.estate_id == estate_id)
        .first()
    )

    if not estate:
        raise HTTPException(404, "Estate not found")

    query = text("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features',
            COALESCE(
                json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry',
                        ST_AsGeoJSON(
                            CASE
                                WHEN ST_SRID(geom) = 4326 THEN geom
                                ELSE ST_Transform(geom, 4326)
                            END
                        )::json,
                        'properties',
                        json_build_object('source', 'martin_map')
                    )
                ) FILTER (WHERE geom IS NOT NULL),
                '[]'::json
            )
        )
        FROM martin_map
    """)

    result = db.execute(query).scalar()

    if result is None:
        return {"type": "FeatureCollection", "features": []}

    return result


@app.get("/api/map/test")
def test_map(
    db: Session = Depends(get_db),
    _: dict = Depends(require_forester),
):
    try:
        total_rows = db.execute(text("SELECT COUNT(*) FROM martin_map")).scalar()
        rows_with_geometry = db.execute(
            text("SELECT COUNT(*) FROM martin_map WHERE geom IS NOT NULL")
        ).scalar()
        srid = db.execute(
            text("SELECT ST_SRID(geom) FROM martin_map WHERE geom IS NOT NULL LIMIT 1")
        ).scalar()

        return {
            "success": True,
            "table": "martin_map",
            "total_rows": total_rows,
            "rows_with_geometry": rows_with_geometry,
            "srid": srid,
        }
    except Exception as e:
        raise HTTPException(500, f"Map test failed: {str(e)}")


@app.get("/api/estates/{estate_id}/map/count")
def map_count(
    estate_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_forester),
):
    enforce_estate_scope(user, estate_id)

    try:
        management_compartments = db.execute(
            text("SELECT COUNT(*) FROM compartments WHERE estate_id = :id"),
            {"id": estate_id}
        ).scalar()

        martin_map_geometries = db.execute(
            text("SELECT COUNT(*) FROM martin_map WHERE geom IS NOT NULL")
        ).scalar()

        compartments_with_geometry = db.execute(
            text("SELECT COUNT(*) FROM compartments WHERE estate_id = :id AND geom IS NOT NULL"),
            {"id": estate_id}
        ).scalar()

        return {
            "estate_id": estate_id,
            "management_compartments": management_compartments,
            "martin_map_geometries": martin_map_geometries,
            "compartments_with_geometry": compartments_with_geometry,
        }
    except Exception as e:
        raise HTTPException(500, f"Map count failed: {str(e)}")