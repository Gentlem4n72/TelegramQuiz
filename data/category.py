import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Category(SqlAlchemyBase):
    __tablename__ = 'categories'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    questions = orm.relationship("Question", back_populates='category')

    def __repr__(self):
        return f'{self.title}'