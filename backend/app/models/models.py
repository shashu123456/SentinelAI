from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    api_name = Column(String(200), nullable=False)
    api_title = Column(String(200), nullable=True)
    api_version = Column(String(20), nullable=True)
    total_endpoints = Column(Integer, default=0)
    total_vulnerabilities = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="Unknown")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="scans")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    ai_analysis = relationship("AIAnalysis", back_populates="scan", uselist=False, cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    vulnerability_name = Column(String(200), nullable=False)
    owasp_category = Column(String(50), nullable=False)
    cwe_id = Column(String(20), nullable=True)
    severity = Column(String(20), nullable=False)
    confidence = Column(Integer, default=85)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    impact = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    affected_endpoint = Column(String(500), nullable=True)
    affected_method = Column(String(10), nullable=True)
    detection_reason = Column(Text, nullable=True)
    false_positive_note = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, unique=True)
    executive_summary = Column(Text, nullable=True)
    technical_explanation = Column(Text, nullable=True)
    business_impact = Column(Text, nullable=True)
    attack_scenario = Column(Text, nullable=True)
    recommended_mitigation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scan = relationship("Scan", back_populates="ai_analysis")
