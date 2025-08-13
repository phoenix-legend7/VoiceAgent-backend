from sqlalchemy import Column, JSON, BigInteger, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Phone(Base):
    __tablename__ = "phone"

    id = Column(String, primary_key=True,unique=True, nullable=False)
    agent_id = Column(String, nullable=True)
    agent_config_override = Column(JSON, nullable=True)
    status = Column(String, nullable=True)
    tags = Column(JSON, nullable=False, default=[])
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)

    # Purchase Phone Number
    country = Column(String, nullable=True)
    area_code = Column(String, nullable=True)
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state_region = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    # Import Phone Number
    # country = Column(String, nullable=True)
    # phone = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    region = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    account_sid = Column(String, nullable=True)
    app_id = Column(String, nullable=True)
    subdomain = Column(String, nullable=True)
    auth_id = Column(String, nullable=True)
    auth_token = Column(String, nullable=True)
