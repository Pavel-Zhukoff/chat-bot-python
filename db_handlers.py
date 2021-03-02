import os

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import inspect
import config
engine = create_engine(
        f'postgresql://{config.DATABASE_USER}:{config.DATABASE_PASSWORD}@{config.DATABASE_HOST}:{config.DATABASE_PORT}/{config.DATABASE_NAME}',
        pool_pre_ping=True
    )
# session_factory = sessionmaker(bind=engine)
# db_session = DBSession(session_factory())

def save_lost_data(text, aid):
    with engine.connect() as conn:
        conn.execute("INSERT INTO public.lost(content, is_lost, account_id) VALUES ('{}', true, {});".format(text, aid))


def load_lost_data():
    data = []
    with engine.connect() as con:
        rs = con.execute('SELECT * FROM public.lost l left join accounts a on l.account_id=a.id where l.is_lost=true order by l.creation_date limit 5')
        for row in rs:
            data.append(row)
    return data


def get_aid_by_token(token):
    with engine.connect() as con:
        rs = con.execute("SELECT t.account_id FROM public.token t left join accounts a on t.account_id=a.id where t.token='{}'".format(token)).scalar()
        return rs


def get_floors_count():
    # returlen(os.listdir(config.FLOORS_DIR))
    return len([name for name in os.listdir(config.FLOORS_DIR) if os.path.isfile(os.path.join(config.FLOORS_DIR, name))])