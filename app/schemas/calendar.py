from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from uuid import UUID

class CalendarBase(BaseModel):
    name: str = Field(..., description="Function name: 'get_available_meeting_slots' or 'book_meeting_slot'")
    title: str = Field(..., description="User-friendly display name")
    provider: str = Field(default="cal.com", description="Calendar provider")
    api_key: str = Field(..., description="API key for the calendar provider")
    event_type_id: str = Field(..., description="Event type ID")
    contact_method: Optional[str] = Field(None, description="Contact method: 'email' or 'phone' (required for 'book_meeting_slot')")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v not in ["get_available_meeting_slots", "book_meeting_slot"]:
            raise ValueError("name must be either 'get_available_meeting_slots' or 'book_meeting_slot'")
        return v

    @field_validator('contact_method')
    @classmethod
    def validate_contact_method(cls, v):
        if v and v not in ["email", "phone"]:
            raise ValueError("contact_method must be either 'email' or 'phone'")
        return v
    
    @model_validator(mode='after')
    def validate_contact_method_required(self):
        if self.name == 'book_meeting_slot' and not self.contact_method:
            raise ValueError("contact_method is required when name is 'book_meeting_slot'")
        return self

class CalendarCreate(CalendarBase):
    pass

class CalendarUpdate(CalendarBase):
    pass

class CalendarResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    title: str
    provider: str
    event_type_id: str
    contact_method: Optional[str] = None
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True

