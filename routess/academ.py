# import datetime
import math
import time

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from pydantic import Field
from sqlalchemy import delete, update
from sqlalchemy.dialects.sqlite import insert

from database.sqllite_db import Session_lite, Api, OldDate
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

        Гарантируется, что во входных данных нет циклических зависимостей и поле updateDate монотонно возрастает. Гарантируется, что при проверке передаваемое время кратно секундам.""",
             dependencies=[Depends(RateLimiter(times=1000, seconds=60))])
async def import_post(Data: ShopUnitImportRequest):
    # print(f'Получаю значение\n {Data}')

    requestid = []  # массив для id \\ id - товара/OFFER или категории/CATEGORY является уникальным среди товаров и категорий
    session = Session_lite()  # создание ссесии
    try:
        for i in Data.items:  # обаратываю каждый элемент товаров
            if i.id in requestid:
                print(f'в одном запросе не может быть двух элементов с одинаковым id {i.id}')
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
                # print(Data.updateDate)
                isodate = Data.updateDate.isoformat()
                # print(isodate)
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

                if parentIdBase == None:  # если нету родительского id
                    usercreat = insert(Api).values(id=i.id, name=i.name, parentId=i.parentId, type=i.type,
                                                   price=i.price, updateDate=Data.updateDate)
                    olddates = insert(OldDate).values(id=i.id, parentId=i.parentId, updateDate=Data.updateDate,
                                                      olddate=None)
                    session.execute(olddates)
                    session.execute(usercreat)
                    session.commit()

                elif parentIdBase.type == 'OFFER':  # Если тип родителя товар
                    print('родителем/parentId товара или категории может быть только категория')
                    return HTTPException(status_code=400,
                                         detail="Невалидная схема документа или входные данные не верны.")

                else:
                    print(f'!!!!!!!!!!!!')
                    print(f'добавляю.... id = {i.id}')
                    print(i.price, str(i.price))
                    if i.type == "CATEGORY" and i.price is not None:
                        print(f'поле price у CATEGORY должен быть равен null')
                        return HTTPException(status_code=400,
                                             detail="Невалидная схема документа или входные данные не верны (поле price должно равняться null)")
                    usercreat = insert(Api).values(id=i.id, name=i.name, parentId=i.parentId, type=i.type,
                                                   price=i.price, updateDate=Data.updateDate)
                    olddates = insert(OldDate).values(id=i.id, parentId=i.parentId, updateDate=Data.updateDate,
                                                      olddate=None)
                    session.execute(olddates)
                    session.execute(usercreat)
                    session.commit()

                    try:
                        print(f'обновляю метку у всех товаров данной категории')

                        upCat = update(Api).where(Api.id == i.parentId).values(updateDate=Data.updateDate)
                        olddates1 = update(OldDate).where(OldDate.id == i.parentId).values(olddate=OldDate.updateDate)
                        olddates2 = update(OldDate).where(OldDate.id == i.parentId).values(updateDate=Data.updateDate)
                        session.execute(olddates1)
                        session.execute(olddates2)
                        session.execute(upCat)
                        session.commit()

                        try:  # обновление главной категории
                            print(f'i id= {i}')
                            print(f'idbase = {idbase}')
                            parentid = session.query(Api).filter(
                                Api.id == i.parentId).first()  # поиск id категории выше
                            print(f'**************' * 30)
                            print(f'parentid = {parentid}')
                            upMain = update(Api).where(Api.id == parentid.parentId).values(updateDate=Data.updateDate)
                            session.execute(upMain)
                            session.commit()

                        except:
                            print(f'ошибка обновления категории')
                    except:
                        print(f'ошибка обновления категории')



            else:  # Если айди есть в базе, то меняю его
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
                    if idbase.type == 'OFFER':
                        print(f'обновляю товар')
                        usercreat = update(Api).where(Api.id == i.id).values(name=i.name, parentId=i.parentId,
                                                                             type=i.type, price=i.price,
                                                                             updateDate=Data.updateDate)
                        usercreat_date_save = update(OldDate).where(OldDate.id == i.id).values(
                            olddate=OldDate.updateDate)
                        usercreat2 = update(OldDate).where(OldDate.id == i.id).values(parentId=i.parentId,
                                                                                      updateDate=Data.updateDate)
                        session.execute(usercreat)
                        session.execute(usercreat2)
                        session.execute(usercreat_date_save)
                        session.commit()
                        print(f'обновляю метку у самой категории')
                        upCat = update(Api).where(Api.id == i.parentId).values(updateDate=Data.updateDate)
                        upCat_date_save = update(OldDate).where(OldDate.id == i.parentId).values(
                            olddate=OldDate.updateDate)
                        upCat2 = update(OldDate).where(OldDate.id == i.parentId).values(updateDate=Data.updateDate)

                        session.execute(upCat)
                        session.execute(upCat_date_save)
                        session.execute(upCat2)

                        session.commit()

                        try:  # обновление главной категории

                            parentid = session.query(Api).filter(
                                Api.id == i.parentId).first()  # поиск id категории выше
                            parentid2 = session.query(OldDate).filter(
                                OldDate.id == i.parentId).first()  # поиск id категории выше (OldDate)
                            upMain = update(Api).where(Api.id == parentid.parentId).values(updateDate=Data.updateDate)
                            upMain2_save_data = update(OldDate).where(OldDate.id == parentid2.parentId).values(
                                olddate=OldDate.updateDate)
                            upMain2 = update(OldDate).where(OldDate.id == parentid2.parentId).values(
                                updateDate=Data.updateDate)

                            session.execute(upMain)
                            session.execute(upMain2_save_data)
                            session.execute(upMain2)
                            session.commit()


                        except Exception as err:
                            print(err)
                            time.sleep(20)
                            print(f'ошибка обновления категории')

                    else:  # если обновляется категория то обновляю метку у категории выше
                        print(f'обновление категории')
                        usercreat = update(Api).where(Api.id == i.id).values(name=i.name, parentId=i.parentId,
                                                                             type=i.type, price=i.price,
                                                                             updateDate=Data.updateDate)
                        usercreat2 = update(OldDate).where(OldDate.id == i.id).values(parentId=i.parentId,
                                                                                      updateDate=Data.updateDate)
                        usercreat2_save_data = update(OldDate).where(OldDate.id == i.id).values(
                            olddate=OldDate.updateDate)
                        session.execute(usercreat)
                        session.execute(usercreat2_save_data)
                        session.execute(usercreat2)
                        session.commit()

                        if idbase.updateDate != Data.updateDate:  # новая метка времен
                            print(f'обновляю метку у самой категории')

                            upCat = update(Api).where(Api.id == i.parentId).values(updateDate=Data.updateDate)
                            upCat2 = update(OldDate).where(OldDate.id == i.parentId).values(updateDate=Data.updateDate)
                            upCat2_save_data = update(OldDate).where(OldDate.id == i.parentId).values(
                                olddate=OldDate.updateDate)
                            session.execute(upCat)
                            session.execute(upCat2_save_data)
                            session.execute(upCat2)
                            session.commit()

                            try:  # обновление главной категории
                                print(f'i id= {i}')
                                print(f'idbase = {idbase}')
                                parentid = session.query(Api).filter(
                                    Api.id == i.parentId).first()  # поиск id категории выше
                                parentid2 = session.query(OldDate).filter(
                                    OldDate.id == i.parentId).first()  # поиск id категории выше (OldDate)
                                print(f'**************' * 30)
                                print(f'parentid = {parentid}')
                                upMain = update(Api).where(Api.id == parentid.parentId).values(
                                    updateDate=Data.updateDate)
                                upMain_another2 = update(OldDate).where(OldDate.id == parentid2.parentId).values(
                                    updateDate=Data.updateDate)
                                upMain_another2_save_data = update(OldDate).where(
                                    OldDate.id == parentid2.parentId).values(
                                    olddateDate=OldDate.updateDate)
                                session.execute(upMain)
                                session.execute(upMain_another2_save_data)
                                session.execute(upMain_another2)
                                session.commit()

                            except:
                                print(f'ошибка обновления категории')

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

        + Обратите, пожалуйста, внимание на этот обработчик. При его некорректной работе тестирование может быть невозможно.""",
               dependencies=[Depends(RateLimiter(times=1000, seconds=60))])
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
            # ищем все дочерние каталоги и удалем их
            parentCat = session.query(Api).filter(
                Api.parentId == id and Api.type == 'CATEGORY').all()  # ищу подкаталоги

            if parentCat != None:  # если есть дочерние каталоги
                for i in parentCat:  # ищу все дочерние товары в этих каталогах
                    parentOffdel = delete(Api).filter(Api.parentId == i.id)  # ищу товары каждого каталога и удаляю
                    sqldelete2 = delete(OldDate).filter(OldDate.parentId == i.id)
                    session.execute(sqldelete2)
                    session.execute(parentOffdel)
                    session.commit()

                sqldelete = delete(Api).filter(Api.parentId == id)  # удаление всех дочерних элементов
                session.execute(sqldelete)
                sqldelete2 = delete(OldDate).filter(OldDate.parentId == id)
                session.execute(sqldelete2)
                session.commit()
                idbasedel = delete(Api).filter(Api.id == id)  # удаление самого каталога
                session.execute(idbasedel)
                idbasedel2 = delete(OldDate).filter(OldDate.id == id)
                session.execute(idbasedel2)
                session.commit()


            else:  # если нет подкаталогов то удаляю все товары внутри каталога
                sqldelete = delete(Api).filter(Api.parentId == id)  # удаление всех дочерние элементы
                session.execute(sqldelete)
                sqldelete2 = delete(OldDate).filter(OldDate.parentId == id)
                session.execute(sqldelete2)
                session.commit()
                idbasedel = delete(Api).filter(Api.id == id)  # удаление сам каталог
                session.execute(idbasedel)
                idbasedel2 = delete(OldDate).filter(OldDate.id == id)
                session.execute(idbasedel2)
                session.commit()

            return HTTPException(status_code=200, detail="Удаление прошло успешно.")


        elif idbase.type == 'OFFER':  # Если товар
            sqldelete = delete(Api).filter(Api.id == id)  # удаление всех дочерних элементов
            sqldelete2 = delete(OldDate).filter(OldDate.id == id)
            session.execute(sqldelete2)
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
        + При обновлении цены товара, средняя цена категории, которая содержит этот товар, тоже обновляется.""",
            status_code=200)
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

            parentCat = session.query(Api).filter(Api.parentId == id).filter(
                Api.type == 'CATEGORY').all()  # ищем все дочерние категории
            print(f'parentCat = {parentCat}')

            if len(parentCat) == 0:  # если дочерние категории не найдены
                print(f'для пустой категории поле children равно пустому массиву, а для товара равно null')

                parentOff = session.query(Api).filter(Api.parentId == id).filter(
                    Api.type == 'OFFER').all()  # ищем товары в категории

                if len(parentOff) == 0:  # если товаров в категории не найдено
                    return ShopUnit(id=idbase.id, name=idbase.name,
                                    date=str(idbase.updateDate).replace(' ', 'T') + ".000Z", parentId=idbase.parentId,
                                    type=idbase.type,
                                    price=None, children=[])
                else:  # иначе обрабатываем товары

                    mediumprice = sum([(math.floor(q.price)) for q in parentOff]) / len(
                        parentOff)  # добавляю в массив все цены каждого товара. округленные в меньшую сторону
                    print(f'^^^^^' * 10)
                    print(mediumprice)

                    childrenOff = []  # дочерние товары
                    for offer in parentOff:
                        childrenOff.append(
                            ShopUnit(type=offer.type, name=offer.name, id=offer.id, parentId=idbase.id,
                                     price=offer.price,
                                     date=str(offer.updateDate).replace(' ', 'T') + ".000Z", children=None))

                    return ShopUnit(id=idbase.id, name=idbase.name,
                                    date=str(idbase.updateDate).replace(' ', 'T') + ".000Z", parentId=idbase.parentId,
                                    type=idbase.type,
                                    price=mediumprice, children=[childrenOff])

            else:  # если у категории есть дочерние категории
                print(f'дочерние категории {parentCat}')
                childrenCat = []  # массив дочерних категорий

                priceOff = []  # массив для цен товаров
                for i in parentCat:  # обрабатываю дочерние категории
                    print(f'обрабатываю категорию {i}')
                    parentOff = session.query(Api).filter(
                        Api.parentId == i.id and Api.type == 'OFFER').all()  # ищу все дочерние товары категории
                    print(f'товары = {parentOff}')

                    if len(parentOff) == 0:  # если категория не содержит товаров
                        print('Если категория не содержит товаров цена равна null.)')
                        childrenCat.append(
                            ShopUnit(type=i.type, name=i.name, id=i.id, parentId=idbase.id, price=None,
                                     date=str(i.updateDate).replace(' ', 'T') + ".000Z", children=None))


                    else:  # если категория содержит товары то ищу цену всех
                        mediumprice = sum([math.floor(q.price) for q in parentOff]) / len(
                            parentOff)  # сумма вех товаров / число товаров
                        print(f'mediumprice = {mediumprice}')

                        # добавляю все цены товаров в массив
                        [priceOff.append(math.floor(q.price)) for q in
                         parentOff]  # добавляю в массив все цены каждого товара. округленные в меньшую сторону

                        childrenOff = []  # дочерние товары
                        # теперь нужно создать массив товаров
                        for offer in parentOff:
                            print(f'товар = {offer}')
                            childrenOff.append(ShopUnit(type=offer.type, name=offer.name, id=offer.id, parentId=i.id,
                                                        price=offer.price,
                                                        date=str(offer.updateDate).replace(' ', 'T') + ".000Z",
                                                        children=None))

                        # после массив товаров укладываю в категорию
                        childrenCat.append(
                            ShopUnit(type=i.type, name=i.name, id=i.id, parentId=idbase.id, price=mediumprice,
                                     date=str(i.updateDate).replace(' ', 'T') + ".000Z", children=childrenOff))

                '''Целое число, для категории -
                это средняя цена всех дочерних товаров(включая товары подкатегорий).
                Если цена является не целым числом, округляется в меньшую сторону до целого числа.
                Если категория не содержит товаров цена равна null., nullable=True)'''

                mediumCatPrice = sum([math.floor(money) for money in priceOff]) / len(priceOff)
                print(f'mediumCatPrice = {mediumCatPrice}')
                return ShopUnit(type=idbase.type, name=idbase.name, id=idbase.id, parentId=idbase.parentId,
                                price=mediumCatPrice, date=str(idbase.updateDate).replace(' ', 'T') + ".000Z",
                                children=childrenCat)










        elif idbase.type == 'OFFER':  # Если товар

            print(f'для пустой категории поле children равно пустому массиву, '
                  f'а для товара равно null')
            return ShopUnit(id=idbase.id, name=idbase.name, date=str(idbase.updateDate).replace(' ', 'T') + ".000Z",
                            parentId=idbase.parentId, type=idbase.type,
                            price=idbase.price, children=None)







    except Exception as err:
        session.rollback()
        print(f'err = {err}')
        if err.args[0] == '404':  # возвращаю нужную ошибку
            raise HTTPException(status_code=404, detail="Категория/товар не найден.")
        else:
            raise HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")

    finally:
        session.close()


# @router.get("/sales", response_model=ShopUnit, tags=['Дополнительные задачи'],
#             description="Получение списка товаров, "
#                         "цена которых была обновлена за последние 24 "
#                         "часа включительно [now() - 24h, now()] от "
#                         "времени переданном в запросе. Обновление "
#                         "цены не означает её изменение. Обновления "
#                         "цен удаленных товаров недоступны. При обновлении "
#                         "цены товара, средняя цена категории, которая "
#                         "содержит этот товар, тоже обновляется.", status_code=200)
# async def sales(time: datetime):
#     print(f'time = {time}')
#
#     session = Session_lite()  # создание ссесии
#     try:
#         print(OldDate.olddate)
#         idbase = session.query(Api).join(OldDate, OldDate.id == Api.id).filter(datetime.strptime(str(OldDate.olddate).replace(' ', 'T') + ".000Z",
#                                                                                                  "%Y-%m-%dT%H:%M:%S.%f%z") >= time).first()
#                                                          # ((OldDate.olddate != OldDate.updateDate) &
#                                                          #  (OldDate.olddate >= time - timedelta(days=1))
#                                                          #  )).first()  # выбираем товары из промежутка [time-24h; time]
#         print(f'idbase = {idbase}')
#
#         if idbase == None:  # если не найден id
#             print(f'товары не найдены')
#             raise ValueError('404')
#
#         return ShopUnit(type=idbase.type, name=idbase.name, id=idbase.id, parentId=idbase.parentId,
#                         price=idbase.price, date=str(idbase.updateDate).replace(' ', 'T') + ".000Z",
#                         children=None)
#
#
#
#     except Exception as err:
#         session.rollback()
#         print(f'err = {err}')
#         if err.args[0] == '404':  # возвращаю нужную ошибку
#             raise HTTPException(status_code=404, detail="Категория/товар не найден.")
#         else:
#             raise HTTPException(status_code=400, detail="Невалидная схема документа или входные данные не верны.")
#
#     finally:
#         session.close()
