import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator, TEXT
import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@db:5432/variant_literature")

# Detect if we should use SQLite fallback
is_sqlite = False
try:
    if "postgresql" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 3})
        # Test connection
        conn = engine.connect()
        conn.close()
    else:
        is_sqlite = True
except Exception as e:
    print(f"PostgreSQL connection failed: {e}. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./variant_literature.db"
    is_sqlite = True

if is_sqlite:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SafeVector(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector
            return dialect.type_descriptor(Vector(self.dim))
        else:
            return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.loads(value)

class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    gene = Column(String, index=True, nullable=False)
    variant = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    reports = relationship("Report", back_populates="variant")

class Paper(Base):
    __tablename__ = "papers"

    pmid = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    journal = Column(String)
    year = Column(Integer)
    abstract = Column(Text)
    embedding = Column(SafeVector(1536), nullable=True) 

    evidences = relationship("Evidence", back_populates="paper")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String, ForeignKey("papers.pmid"), nullable=False)
    evidence_type = Column(String) 
    evidence_text = Column(Text, nullable=False)
    acmg_code = Column(String) 
    strength = Column(String) 
    embedding = Column(SafeVector(1536), nullable=True)

    paper = relationship("Paper", back_populates="evidences")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    generated_summary = Column(Text, nullable=False)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    variant = relationship("Variant", back_populates="reports")

def init_db():
    if not is_sqlite:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
