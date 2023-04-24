import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Question(SqlAlchemyBase):  # вопрос викторины
    __tablename__ = 'questions'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    text = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    correct_answer = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    other_answers = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    attachment = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    category_id = sqlalchemy.Column(sqlalchemy.Integer,
                                    sqlalchemy.ForeignKey("categories.id"))
    category = orm.relationship('Category')
