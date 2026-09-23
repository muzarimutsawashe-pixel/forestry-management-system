from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# ESTATES
# ============================================================

class Estate(Base):

    __tablename__ = "estates"

    estate_id = Column(
        Integer,
        primary_key=True
    )

    estate_name = Column(
        String
    )


# ============================================================
# COMPARTMENTS
# ============================================================

class Compartment(Base):

    __tablename__ = "compartments"

    compartment_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    estate_id = Column(
        Integer,
        nullable=False
    )

    compartment_code = Column(
        String
    )

    species = Column(
        String
    )

    planting_year = Column(
        Integer
    )

    area_planted = Column(
        Numeric
    )

    area_compartment = Column(
        Numeric
    )

    status = Column(
        String
    )

    age = Column(
        Integer
    )

    block_id = Column(
        String
    )

    operations = relationship(
        "SilvicultureOperation",
        back_populates="compartment",
        cascade="all, delete-orphan"
    )


# ============================================================
# SILVICULTURE OPERATIONS
# ============================================================

class SilvicultureOperation(Base):

    __tablename__ = "silviculture_operations"

    operation_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    compartment_id = Column(
        Integer,
        ForeignKey("compartments.compartment_id"),
        nullable=False,
        index=True
    )

    operation_type = Column(
        String,
        index=True
    )

    operation_date = Column(
        Date
    )

    area_treated = Column(
        Numeric
    )

    status = Column(
        String
    )

    remarks = Column(
        Text
    )

    recorded_by = Column(
        String
    )

    created_at = Column(
        DateTime
    )

    operation_date_display = Column(
        Text
    )

    compartment = relationship(
        "Compartment",
        back_populates="operations"
    )


# ============================================================
# NOTE
# ============================================================
#
# The geom column exists in PostgreSQL as a PostGIS geometry.
# It is deliberately not mapped as a normal SQLAlchemy column.
#
# The map endpoint in main.py accesses geom using PostGIS SQL.
#
# ============================================================