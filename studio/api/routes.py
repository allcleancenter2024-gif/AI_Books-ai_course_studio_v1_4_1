import json
from fastapi import APIRouter, Depends, HTTPException
from ..config import VERSION, LAST_UPDATED, DB_PATH, RDBMS_NAME, RDBMS_ROLE
from ..data.catalog import TOPICS
from ..auth import require_authenticated
from ..services.generation_service import providers
from ..services.latest_info_service import product_rows

router=APIRouter(prefix='/api', dependencies=[Depends(require_authenticated)])

@router.get('/system-info')
def system_info():
    """Runtime facts shown in the UI; never expose credentials."""
    return {
        'version': VERSION, 'last_updated': LAST_UPDATED,
        'changes': 'LM Studio·Ollama 전용 로컬 AI 구조, 상세 설정, 모델 찾기, 서버·모델 자동 연결 기능 적용',
        'rdbms': RDBMS_NAME, 'role': RDBMS_ROLE,
        'location': str(DB_PATH.parent), 'database_file': DB_PATH.name,
    }

@router.get('/status')
def status():
    ps=providers.list_public()
    return {'server':'online','version':VERSION,'last_updated':LAST_UPDATED,'providers':[{'name':p['name'],'model':p['model'],'configured':bool(p.get('has_key'))} for p in ps]}

@router.get('/topics')
def topics(): return [{'name':n,'description':d} for n,d in TOPICS]

def _product_rows():
    return product_rows()

@router.get('/products')
def products(): return _product_rows()

@router.get('/products/changes')
def product_changes(): return [row for row in _product_rows() if row['has_changes']]
