from datetime import datetime
import json
from aiohttp import web
from gino import Gino
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PG_DSN = 'postgres://admin:1234@127.0.0.1:5431/aiohttp_task'

engine = create_engine(PG_DSN)
Session = sessionmaker(bind=engine)

app = web.Application()
db = Gino()


class HttpError(web.HTTPError):

    def __init__(self, *args, error='', **kwargs):
        kwargs['text'] = json.dumps({'error': error})
        super().__init__(*args, **kwargs, content_type='application/json')


class NotFound(HttpError):
    status_code = 404


class AdvertisementModel(db.Model):
    __tablename__ = 'advertisements'
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    time_create = db.Column(db.DateTime, default=datetime.now())
    Owner = db.Column(db.String, nullable=False)


async def init_orm(app):
    print('Приложение запущенно')
    await db.set_bind(PG_DSN)
    await db.gino.create_all()
    yield
    print('Приложение остановлено')
    await db.pop_bind().close()


class AdvertisementView(web.View):

    async def post(self):
        json_data = await self.request.json()
        new_advertisement = await AdvertisementModel.create(**json_data)
        return web.json_response({'advertisement_id': new_advertisement.id})

    async def get(self):
        advertisement_id = int(self.request.match_info['advertisement_id'])
        advertisement = await AdvertisementModel.get(advertisement_id)
        if advertisement is None:
            raise NotFound(error='advertisement not found')
        return web.json_response({'advertisement_id': advertisement.id,
                                  'headline': advertisement.headline,
                                  'description': advertisement.description,
                                  'time_create': str(advertisement.time_create),
                                  'owner': advertisement.Owner
                                  })

    async def delete(self):
        advertisement_id = int(self.request.match_info['advertisement_id'])
        advertisement = await AdvertisementModel.get(advertisement_id)
        if advertisement is None:
            raise NotFound(error='advertisement not found')
        await advertisement.delete()
        return web.json_response({'удаление': 'успешно'})

    async def patch(self):
        async with Session() as session:
            advertisement_id = int(self.request.match_info['advertisement_id'])
            advertisement = await AdvertisementModel.get(advertisement_id)
            if advertisement is None:
                raise NotFound(error='advertisement not found')
            data = await self.request.json()
            advertisement.headline = data.get('headline', advertisement.headline)
            advertisement.description = data.get('description', advertisement.description)
            advertisement.Owner = data.get('owner', advertisement.Owner)
            await session.commit()
            return web.json_response({'advertisement_id': advertisement.id,
                                      'headline': advertisement.headline,
                                      'description': advertisement.description,
                                      'time_create': str(advertisement.time_create),
                                      'owner': advertisement.Owner
                                      })


app.router.add_route('POST', '/advertisements/', AdvertisementView)
app.router.add_route('GET', '/advertisements/{advertisement_id:\d+}', AdvertisementView)
app.router.add_route('DELETE', '/advertisements/{advertisement_id:\d+}', AdvertisementView)
app.router.add_route('PATCH', '/advertisements/{advertisement_id:\d+}', AdvertisementView)
app.cleanup_ctx.append(init_orm)
web.run_app(app)
