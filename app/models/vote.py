from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    count = Column(Integer, default=0)
    version = Column(Integer, default=0)
