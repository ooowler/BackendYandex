from sqlalchemy import create_engine, Column, Text, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

engine_sqlite = create_engine("sqlite:///database/api.db")

Session_lite = sessionmaker(bind=engine_sqlite)

Base = declarative_base()


class Api(Base):
    __tablename__ = 'api'

    id = Column(Text, primary_key=True)
    name = Column(Text)
    parentId = Column(Text)
    type = Column(Text)
    price = Column(Integer)
    updateDate = Column(DateTime)  # DateTime(timezone=True)) #(DATETIME)

    def __repr__(self):
        return "<api(id='%s', name='%s', parentId='%s', type='%s', price='%s', updateDate='%s')>" % (
            self.id, self.name, self.parentId, self.type, self.price, self.updateDate)


class OldDate(Base):
    __tablename__ = 'date'

    id = Column(Text, primary_key=True)
    parentId = Column(Text)
    updateDate = Column(DateTime)  # DateTime(timezone=True)) #(DATETIME)
    olddate = Column(DateTime)  # DateTime(timezone=True)) #(DATETIME)

    def __repr__(self):
        return "<api(id='%s', parentId='%s', updateDate='%s', olddate='%s')>" % (
            self.id, self.parentId, self.updateDate, self.olddate)
