"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")

class Project(BaseModel):
    user_id: str = Field(..., description="Owner user id")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Short description")

class Chat(BaseModel):
    project_id: str = Field(..., description="Project id")
    title: str = Field(..., description="Chat title")

class Message(BaseModel):
    chat_id: str = Field(..., description="Chat id")
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    created_at: Optional[datetime] = None

# Example schemas (kept for reference)
class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
