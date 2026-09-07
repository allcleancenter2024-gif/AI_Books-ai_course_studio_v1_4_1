import json
from datetime import datetime
from fastapi import HTTPException
from ..data.catalog import COURSE12, COURSE15
from ..multidb import upsert_service, next_service_id


def timing():
    return {"개념설명":18,"실기와실습":144,"정리와점검":18,"총시간":180}


def course_source(weeks:int):
    if weeks not in (12,15):
        raise HTTPException(400,"12주 또는 15주만 지원합니다.")
    return COURSE12 if weeks==12 else COURSE15


def create_course(weeks:int,audience:str):
    src=course_source(weeks)
    schedule=[{"week":i+1,"topic":t,"practice":p,"timing":timing()} for i,(t,p) in enumerate(src)]
    payload={"weeks":weeks,"audience":audience,"ratio":"개념 10% · 실기/실습 80% · 정리/점검 10%","timing":timing(),"schedule":schedule}
    created_at=datetime.now().isoformat(timespec='seconds')
    payload['course_id']=next_service_id('courses')
    upsert_service('courses', payload['course_id'], payload, created_at=created_at)
    return payload
