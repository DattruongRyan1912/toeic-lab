from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from server.database import Base
from server.utils.timeutil import utcnow


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    tool_calls_json = Column(Text, nullable=True)  # JSON list of actions the mentor executed
    created_at = Column(DateTime, default=utcnow)
