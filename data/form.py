import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Form(SqlAlchemyBase):
    __tablename__ = 'from'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    question = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    correct_answer = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    other_answers1 = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    other_answers2 = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    other_answers3 = sqlalchemy.Column(sqlalchemy.String, nullable=True)