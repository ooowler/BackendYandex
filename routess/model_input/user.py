import datetime
import time

from enum import Enum
from typing import List, Union
from uuid import UUID

from pydantic import BaseModel, Field



class ShopUnitType(str, Enum):
    OFFER = 'OFFER'
    CATEGORY = 'CATEGORY'


class ShopUnitImport(BaseModel):
    id: str = Field(description='Уникальный идентфикатор', nullable=False, example="3fa85f64-5717-4562-b3fc-2c963f66a444")
    name: str = Field(description='Имя элемента.', nullable=False, example='Оффер')
    parentId: Union[str, None] = Field(description='UUID родительской категории', nullable=True, example='3fa85f64-5717-4562-b3fc-2c963f66a333')
    type: ShopUnitType = Field(description='Тип элемента - категория или товар', example='OFFER')

    price: Union[int, None] = Field(description='Целое число, для категорий поле должно содержать null.', nullable=True, example=234)


class ShopUnitImportRequest(BaseModel):
    items: List[ShopUnitImport] = Field(description='Импортируемые элементы', nullable=False)
    updateDate: datetime.datetime = Field(description='Время обновления добавляемых товаров/категорий.', nullable=False, example="2022-05-28T21:12:01.000Z", default=datetime.datetime.now())







### response

class ShopUnit(BaseModel):
    type: ShopUnitType = Field(description='Тип элемента - категория или товар', example='OFFER')
    name: str = Field(description='Имя элемента.', nullable=False, example='Оффер')
    id: str = Field(description='Уникальный идентфикатор', nullable=False, example="3fa85f64-5717-4562-b3fc-2c963f66a333")
    price: Union[int, None] = Field(description='Целое число, для категории - '
                                                'это средняя цена всех дочерних товаров(включая товары подкатегорий). '
                                                'Если цена является не целым числом, округляется в меньшую сторону до целого числа. '
                                                'Если категория не содержит товаров цена равна null.', nullable=True)
    parentId: Union[str, None] = Field(description='UUID родительской категории', nullable=True,
                                       example='3fa85f64-5717-4562-b3fc-2c963f66a333')
    date: str = Field(description='Время последнего обновления элемента.', nullable=False, example='2022-05-28T21:12:01.000Z')


    children: Union[list, None] #Union[List[str], None]

