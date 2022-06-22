from datetime import datetime

from sqlalchemy import create_engine, Column, Text, Integer, DATETIME, DateTime
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import sessionmaker, declarative_base


engine_sqlite = create_engine("sqlite:///database/api.db") #, connect_args={"options": "-c timezone=utc"})

Session_lite = sessionmaker(bind=engine_sqlite)

Base = declarative_base()


class Api(Base):
    __tablename__ = 'api'

    id = Column(Text, primary_key=True)
    name = Column(Text)
    parentId = Column(Text)
    type = Column(Text)
    price = Column(Integer)
    updateDate = Column(DateTime(timezone=True)) #DateTime(timezone=True)) #(DATETIME)
    # date = Column(Text, default=datetime.now()) #default=(str((datetime.now()).isoformat)))


    def __repr__(self):
        return "<api(id='%s', name='%s', parentId='%s', type='%s', price='%s', updateDate='%s')>" % (
            self.id, self.name, self.parentId, self.type, self.price, self.updateDate)#, self.date)
