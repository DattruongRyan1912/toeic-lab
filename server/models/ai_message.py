from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from server.database import Base

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False) # user, assistant, system, tool
    content = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    tool_calls_json = Column(Text, nullable=True) # JSON representation of tool calls made
    created_at = Column(DateTime, default=datetime.utcnow)
