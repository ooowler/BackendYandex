import math

from fastapi import APIRouter, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from pydantic import Field
from sqlalchemy import delete, update
from sqlalchemy.dialects.sqlite import insert

from database.sqllite_db import Session_lite, Api
from routess.model_input.user import ShopUnitImportRequest, ShopUnit

router = APIRouter()


@router.post("/imports", tags=['Базовые задачи'], description="""
        Импортирует новые товары и/или категории. Товары/категории импортированные повторно обновляют текущие. 
        Изменение типа элемента с товара на категорию или с категории на товар не допускается. 
        Порядок элементов в запросе является произвольным.
        
          + id - товара/OFFER или категории/CATEGORY является уникальным среди товаров и категорий
          + родителем товара или категории может быть только категория
          + принадлежность к категории определяется полем parentId
          + товар или категория могут не иметь родителя (при обновлении parentId на null, элемент остается без родителя)
          + название элемента не может быть null
          + у категорий поле price должно содержать null
          + цена товара не может быть null и должна быть больше либо равна нулю.
          + при обновлении товара/категории обновленными считаются **все** их параметры
          + при обновлении параметров элемента обязательно обновляется поле **date** в соответствии с временем обновления
          + в одном запросе не может быть двух элементов с одинаковым id
          + дата должна обрабатываться согласно ISO 8601 (такой придерживается OpenAPI). Если дата не удовлетворяет данному формату, необходимо отвечать 400.

        Гарантируется, что во входных данных нет циклических зависимостей и поле updateDate монотонно возрастает. Гарантируется, что при проверке передаваемое время кратно секундам.""", dependencies=[Depends(RateLimiter(times=1000, seconds=60))])
async def import_post(Data: ShopUnitImportRequest):
    print(f'Получаю значение\n {Data}')

    requestid = []  # массив для id \\ id - товара/OFFER или категории/CATEGORY является уникальным среди товаров и категорий
    session = Session_lite()  # создание ссесии
    try:
        for i in Data.items: #обаратываю каждый элемент товаров
            if i.id in requestid:
                print(f'в одном запросе не может быть двух элементов с одинаковым id')
                return HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
            elif i.name is None:
                print(f'название элемента не может быть null')
                return HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
            elif i.price is None and i.type == 'OFFER':
                print(f'цена товара не может быть null и должна быть больше либо равна нулю.')
                return HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
            elif i.type == 'CATEGOTY' and i.price != None:
                print(f'у категорий поле price должно содержать null')
                return HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")

            try:
                print(Data.updateDate)
                isodate = Data.updateDate.isoformat()
                print(isodate)
                print(f'******************' * 30)
            except:
                print('дата должна обрабатываться согласно ISO 8601 (такой придерживается OpenAPI). '
                      'Если дата не удовлетворяет данному формату, необходимо отвечать 400.')
                return HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")

            requestid.append(i.id)  # проверка на то был ли такой id в запросе

            idbase = session.query(Api).filter(Api.id == i.id).first()  # поиск id в базе
            print(f'id в базе {idbase}')

            if idbase is None:  # Если айди нету в базе то создаю
                print(f'создание id в базе')

                parentIdBase = session.query(Api).filter(Api.id == i.parentId).first()
                print(f'родитель = {parentIdBase}')

                if parentIdBase == None:
                    print(f'i.type = {i.type}')
                    print(Data.updateDate)
                    usercreat = insert(Api).values(id=i.id, name=i.name, parentId=i.parentId, type=i.type,
                                                   price=i.price, updateDate=Data.updateDate)
                    session.execute(usercreat)
                    session.commit()

                elif parentIdBase.type == 'OFFER':  # Если тип родителя товар
                    print('родителем/parentId товара или категории может быть только категория')
                    return HTTPException(status_code=400,
                                        detail="Невалидная схема документа или входные данные не верны.")

                else:
                    usercreat = insert(Api).values(id=i.id, name=i.name, parentId=i.parentId, type=i.type, price=i.price, updateDate=Data.updateDate)
                    session.execute(usercreat)
                    session.commit()



            else:  # Если айди есть в базе то меняю его
                print(f'обновляю id')

                if i.type != idbase.type:  # Если попытаются поменять тип элемента
                    print(f'''Импортирует новые товары и/или категории. Товары/категории импортированные повторно обновляют текущие. 
                    Изменение типа элемента с товара на категорию или с категории на товар не допускается. ''')
                    return HTTPException(status_code=400,
                                        detail="Невалидная схема документа или входные данные не верны.")
                else:
                    """    
                    - принадлежность к категории определяется полем parentId
                    - товар или категория могут не иметь родителя (при обновлении parentId на null, элемент остается без родителя)
                    - при обновлении товара/категории обновленными считаются **все** их параметры
                    - при обновлении параметров элемента обязательно обновляется поле **date** в соответствии с временем обновления
                    """

                    print(f'обновляю в бд')
                    usercreat = update(Api).where(Api.id==i.id).values(name=i.name, parentId=i.parentId, type=i.type, price=i.price, updateDate=Data.updateDate)
                    session.execute(usercreat)
                    session.commit()
                    print(f'успешно обновлено')


        return HTTPException(status_code=200, detail="Вставка или обновление прошли успешно.")
    except Exception as err:
        print(f'Невалидная схема документа или входные данные не верны.')
        print(err)
        session.rollback()
        raise HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
    finally:
        session.close()


@router.delete("/delete/{id}", tags=['Базовые задачи'], description="""
        + Удалить элемент по идентификатору. При удалении категории удаляются все дочерние элементы. 
        - Доступ к статистике (истории обновлений) удаленного элемента невозможен.

        + Так как время удаления не передается, при удалении элемента время обновления родителя изменять не нужно.

        + Обратите, пожалуйста, внимание на этот обработчик. При его некорректной работе тестирование может быть невозможно.""", dependencies=[Depends(RateLimiter(times=1000, seconds=60))])
async def delete_(id: str = Field(description='Идентификатор', example='3fa85f64-5717-4562-b3fc-2c963f66a333')):
    print(f'id = {id}')

    session = Session_lite()  # создание ссесии
    try:

        idbase = session.query(Api).filter(Api.id == id).first()  # поиск id в базе
        print(f'idbase = {idbase}')

        if idbase is None:  # если не найден id
            return HTTPException(status_code=404, detail="Категория/товар не найден.")
        elif idbase.type == 'CATEGORY':  # Если каталог
            print(f'При удалении категории удаляются все дочерние элементы.')
            #ищем все дочерние каталоги и удалем их
            parentCat = session.query(Api).filter(Api.parentId == id and Api.type == 'CATEGORY').all() # ищу подкаталоги


            if parentCat != None: #если есть дочерние каталоги
                for i in parentCat: #ищу все дочерние товары в этих каталогах
                    parentOffdel = delete(Api).filter(Api.parentId == i.id) # ищу товары каждого каталога
                    session.execute(parentOffdel)
                    session.commit()

                sqldelete = delete(Api).filter(Api.parentId == id)  # удаление всех дочерние элементы
                session.execute(sqldelete)
                session.commit()
                idbasedel = delete(Api).filter(Api.id == id)  # удаление сам каталог
                session.execute(idbasedel)
                session.commit()


            else: #если нет подкаталогов то удаляю все товары внутри каталога
                sqldelete = delete(Api).filter(Api.parentId == id)  # удаление всех дочерние элементы
                session.execute(sqldelete)
                session.commit()
                idbasedel = delete(Api).filter(Api.id == id)  # удаление сам каталог
                session.execute(idbasedel)
                session.commit()




            return HTTPException(status_code=200, detail="Удаление прошло успешно.")


        elif idbase.type == 'OFFER':  # Если товар
            sqldelete = delete(Api).filter(Api.id == id)  # удаление всех дочерних элементов
            session.execute(sqldelete)
            session.commit()

            return HTTPException(status_code=200, detail="Удаление прошло успешно.")
    except Exception as err:
        print(f'Невалидная схема документа или входные данные не верны.')
        print(err)
        session.rollback()
        raise HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
    finally:
        session.close()


@router.get("/nodes/{id}", response_model=ShopUnit, tags=['Базовые задачи'], description="""
       Получить информацию об элементе по идентификатору. 
       При получении информации о категории также предоставляется информация о её дочерних элементах.

        + для пустой категории поле children равно пустому массиву, а для товара равно null
        + цена категории - это средняя цена всех её товаров, включая товары дочерних категорий. 
        + Если категория не содержит товаров цена равна null. 
        + При обновлении цены товара, средняя цена категории, которая содержит этот товар, тоже обновляется.""", status_code=200)
async def nodes(id: str = Field(description='Идентификатор элемента', example='3fa85f64-5717-4562-b3fc-2c963f66a333')):
    print(f'id = {id}')

    session = Session_lite()  # создание ссесии
    try:

        idbase = session.query(Api).filter(Api.id == id).first()  # поиск id в базе
        print(f'idbase = {idbase}')

        if idbase == None:  # если не найден id
            print(f'не найден id')
            raise ValueError('404')

        elif idbase.type == 'CATEGORY':  # Если категория то ищем все дочерние категории

            parentCat = session.query(Api).filter(Api.parentId == id).filter(Api.type == 'CATEGORY').all() #ищу все дочерние категории
            print(f'parentCat = {parentCat}')

            if len(parentCat) == 0: #если дочерние категории не найдены
                print(f'для пустой категории поле children равно пустому массиву, а для товара равно null')

                parentOff = session.query(Api).filter(Api.parentId == id).filter(Api.type == 'OFFER').all() #ищем товары в категории

                if len(parentOff) == 0: #если товаров в категории не найдено
                    return ShopUnit(id=idbase.id, name=idbase.name, date=idbase.updateDate, parentId=idbase.parentId,
                                    type=idbase.type,
                                    price=None, children=[])
                else: #иначе обрабатываем товары


                    mediumprice = sum([(math.floor(q.price)) for q in parentOff])/len(parentOff) #добавляю в массив все цены каждого товара. округленные в меньшую сторону
                    print(f'^^^^^' * 10)
                    print(mediumprice)

                    childrenOff = []  # дочерние товары
                    for offer in parentOff:
                        childrenOff.append(
                            ShopUnit(type=offer.type, name=offer.name, id=offer.id, parentId=idbase.id, price=offer.price,
                                     date=offer.updateDate, children=None))

                    return ShopUnit(id=idbase.id, name=idbase.name, date=idbase.updateDate, parentId=idbase.parentId, type=idbase.type,
                                    price=mediumprice, children=[childrenOff])

            else: #если у категории есть дочерние категории
                print(f'дочерние категории {parentCat}')
                childrenCat = [] #массив дочерних категорий

                priceOff = [] #массив для цен товаров
                for i in parentCat: #обрабатываю дочерние категории
                    print(f'обрабатываю категорию {i}')
                    parentOff = session.query(Api).filter(Api.parentId == i.id and Api.type == 'OFFER').all()  # ищу все дочерние товары категории
                    print(f'товары = {parentOff}')

                    if len(parentOff) == 0: #если категория не содержит товаров
                        print('Если категория не содержит товаров цена равна null.)')
                        childrenCat.append(
                            ShopUnit(type=i.type, name=i.name, id=i.id, parentId=idbase.id, price=None,
                                     date=i.updateDate, children=None))


                    else: # если категория содержит товары то ищу цену всех
                        mediumprice = sum([math.floor(q.price) for q in parentOff])/len(parentOff) #сумма вех товаров / число товаров
                        print(f'mediumprice = {mediumprice}')

                        #добавляю все цены товаров в массив
                        [priceOff.append(math.floor(q.price)) for q in parentOff] #добавляю в массив все цены каждого товара. округленные в меньшую сторону

                        childrenOff = []  # дочерние товары
                        # теперь нужно создать массив товаров
                        for offer in parentOff:
                            print(f'товар = {offer}')
                            childrenOff.append(ShopUnit(type=offer.type, name=offer.name, id=offer.id, parentId=i.id, price=offer.price, date=offer.updateDate, children=None))

                        #после массив товаров укладываю в категорию
                        childrenCat.append(ShopUnit(type=i.type, name=i.name, id=i.id, parentId=idbase.id, price=mediumprice, date=i.updateDate, children=childrenOff))


                '''Целое число, для категории -
                это средняя цена всех дочерних товаров(включая товары подкатегорий).
                Если цена является не целым числом, округляется в меньшую сторону до целого числа.
                Если категория не содержит товаров цена равна null., nullable=True)'''

                mediumCatPrice = sum([math.floor(money) for money in priceOff])/len(priceOff)
                print(f'mediumCatPrice = {mediumCatPrice}')
                return ShopUnit(type=idbase.type, name=idbase.name, id=idbase.id, parentId=idbase.parentId, price=mediumCatPrice, date=idbase.updateDate, children=childrenCat)










        elif idbase.type == 'OFFER':  # Если товар


            print(f'для пустой категории поле children равно пустому массиву, '
                  f'а для товара равно null')

            return ShopUnit(id=idbase.id, name=idbase.name, date=idbase.updateDate, parentId=idbase.parentId, type=idbase.type,
                            price=idbase.price, children=None)







    except Exception as err:
        session.rollback()
        print(f'err = {err}')
        if err.args[0] == '404': #возвращаю нужную ошибку
            raise HTTPException(status_code=404, detail="Категория/товар не найден.")
        else:
            raise HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")

    finally:
        session.close()
