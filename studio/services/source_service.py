from __future__ import annotations

import ipaddress
import json
import re
import socket
import threading
import uuid
import zipfile
import hashlib
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, UploadFile
from .source_context import build_source_context
from .summarization import summarize_text
from .upload import parse_staged_upload, sha256_file, stage_upload
from .vector_index import index_source

from ..config import (SOURCE_PACKS_DIR, SUMMARY_EXPORTS_DIR, SUMMARY_MAX_CONCURRENT, SUMMARY_QUEUE_LIMIT,
                      UPLOAD_PARSE_MAX_CONCURRENT, UPLOAD_PARSE_QUEUE_LIMIT, UPLOAD_STAGING_RETENTION_SECONDS,
                      UPLOADS_DIR)
from ..db import connect
from ..multidb import mirror_source, delete_source as delete_source_mirror, source_record, source_records, create_source_record, update_source_record
from .job_status import jobs

TEXT_LIMIT = 120_000
CONTEXT_PER_SOURCE = 8_000
ALLOWED_EXT = {'.md','.markdown','.txt','.html','.htm','.pdf','.pptx','.png','.jpg','.jpeg','.webp'}
_summary_job_lock = threading.RLock()
_active_summary_jobs: dict[int, str] = {}
# Counts both running and queued jobs. Non-blocking acquisition means a
# saturated queue is rejected immediately instead of creating unbounded
# threads or leaving an HTTP request waiting indefinitely.
_summary_slots = threading.BoundedSemaphore(SUMMARY_MAX_CONCURRENT + SUMMARY_QUEUE_LIMIT)
_upload_job_lock = threading.RLock()
_active_upload_jobs: set[str] = set()
_upload_parse_slots = threading.BoundedSemaphore(UPLOAD_PARSE_MAX_CONCURRENT + UPLOAD_PARSE_QUEUE_LIMIT)


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _safe_name(name: str) -> str:
    base = Path(name or 'source').name
    return re.sub(r'[^0-9A-Za-z가-힣._ -]+','_',base)[:140]


def _public_url(url: str) -> str:
    u=urlparse(url.strip())
    if u.scheme not in ('http','https') or not u.hostname:
        raise HTTPException(400,'http 또는 https 주소를 입력하세요.')
    if u.username is not None or u.password is not None:
        raise HTTPException(400,'사용자 정보가 포함된 주소는 사용할 수 없습니다.')
    host=u.hostname.lower()
    if host == 'localhost':
        raise HTTPException(400,'로컬 주소는 외부 참고 사이트로 사용할 수 없습니다.')
    try:
        for info in socket.getaddrinfo(host, u.port or (443 if u.scheme=='https' else 80), type=socket.SOCK_STREAM):
            ip=ipaddress.ip_address(info[4][0])
            # Only globally-routable addresses are safe fetch targets.  This also rejects
            # loopback, private, link-local, multicast, unspecified and carrier-grade ranges.
            if not ip.is_global:
                raise HTTPException(400,'사설/로컬 네트워크 주소는 보안을 위해 차단됩니다.')
    except HTTPException: raise
    except Exception as e: raise HTTPException(400,f'주소 확인 실패: {e}')
    return url.strip()


def _youtube_id(url: str) -> str | None:
    m=re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|shorts/|embed/))([A-Za-z0-9_-]{6,})',url)
    return m.group(1) if m else None


def _youtube_transcript(url: str) -> tuple[str,dict]:
    vid=_youtube_id(url)
    if not vid: return '', {'video_kind':'generic'}
    meta={'video_kind':'youtube','youtube_id':vid,'transcript':'unavailable'}
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api=YouTubeTranscriptApi()
        # The library includes both creator-provided and automatically generated
        # captions. Korean is preferred but English and any available track are
        # also valid learning references.
        try:
            fetched=api.fetch(vid, languages=['ko','en','ja'])
        except Exception:
            tracks=api.list(vid)
            fetched=next(iter(tracks)).fetch()
        text='\n'.join(getattr(x,'text',str(x)) for x in fetched)
        meta.update(transcript='captions', transcript_status='자막 추출 완료', chars=len(text)); return text[:TEXT_LIMIT],meta
    except Exception as e:
        reason=str(e)[:300]
        if isinstance(e, ImportError): status='자막 모듈 미설치'
        elif 'disabled' in reason.lower() or 'not available' in reason.lower() or 'could not retrieve a transcript' in reason.lower(): status='공개·자동 자막 없음 또는 자막 접근 제한'
        else: status='YouTube 자막 요청 실패'
        meta.update(transcript_status=status, transcript_error=reason)
        return '',meta


def _youtube_metadata(url: str) -> dict:
    """Keep a useful, searchable video reference even when captions are unavailable."""
    fallback={'title':'YouTube 영상','author_name':'미확인','metadata_status':'metadata_unavailable'}
    try:
        endpoint='https://www.youtube.com/oembed?url='+quote(url,safe='')+'&format=json'
        with httpx.Client(timeout=httpx.Timeout(12),headers={'User-Agent':'AI-Course-Studio/1.5'}) as client:
            response=client.get(endpoint); response.raise_for_status(); data=response.json()
        return {'title':str(data.get('title') or fallback['title'])[:300], 'author_name':str(data.get('author_name') or fallback['author_name'])[:200], 'metadata_status':'oembed'}
    except Exception:
        return fallback


def _insert(kind,title,original_name='',url='',mime_type='',local_path='',text='',meta=None,status='ready') -> dict:
    now=_now(); digest=hashlib.sha256(text.encode('utf-8')).hexdigest() if text else ''
    row=create_source_record({'kind':kind,'title':title,'original_name':original_name,'url':url,'mime_type':mime_type,'local_path':local_path,'extracted_text':text,'summary':'','status':status,'created_at':now,'metadata_json':json.dumps(meta or {},ensure_ascii=False),'metadata':meta or {},'updated_at':now,'content_hash':digest,'vector_status':'pending','storage_mode':'database-only'})
    sid=row['id']
    if text: row['vector_status']=f"indexed:{index_source(sid,text)}"
    # Re-read after vector indexing so both databases receive the final status.
    mirror_source(get_source(sid))
    return row


def _cleanup_expired_upload_staging() -> None:
    cutoff = time.time() - UPLOAD_STAGING_RETENTION_SECONDS
    for path in UPLOADS_DIR.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def _existing_upload(idempotency_key: str, checksum: str, size: int) -> dict | None:
    for row in source_records() or []:
        try:
            metadata = row.get('metadata') or json.loads(row.get('metadata_json') or '{}')
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        if (metadata.get('upload_idempotency_key') == idempotency_key
                and metadata.get('upload_checksum') == checksum
                and int(metadata.get('upload_size', -1)) == size):
            return row
    return None


def _insert_uploaded(*args, checksum: str, size: int, idempotency_key: str):
    kind, title, original_name, url, mime, local_path, text, meta, status = args
    meta = {**(meta or {}), 'upload_checksum': checksum, 'upload_size': size,
            'upload_idempotency_key': idempotency_key}
    return _insert(kind, title, original_name, url, mime, local_path, text, meta, status)


def save_upload(file: UploadFile, job_id: str, declared_size: int = 0, idempotency_key: str = '') -> dict:
    """Accept the file synchronously, then parse/index it in a bounded worker."""
    _cleanup_expired_upload_staging()
    requested_id = job_id or str(uuid.uuid4())
    idempotency_key = re.sub(r'[^0-9A-Za-z._:-]+', '_', idempotency_key.strip())[:160] or requested_id
    if not _upload_parse_slots.acquire(blocking=False):
        raise HTTPException(429, '업로드 분석 대기열이 가득 찼습니다. 현재 작업이 끝난 뒤 다시 시도하세요.')
    try:
        name, destination, size, ext, mime = stage_upload(file, requested_id, declared_size)
        checksum = sha256_file(destination)
        with _upload_job_lock:
            _active_upload_jobs.add(requested_id)
        jobs.update(requested_id, phase='queued', message='업로드 분석 작업을 대기열에 추가했습니다.', progress=56,
                    bytes_done=size, bytes_total=size, error='', result=None,
                    payload={'kind': 'source_upload', 'filename': name, 'staged_name': destination.name,
                             'size': size, 'checksum': checksum, 'extension': ext, 'mime': mime,
                             'idempotency_key': idempotency_key})
    except Exception:
        _upload_parse_slots.release()
        raise

    def run() -> None:
        try:
            existing = _existing_upload(idempotency_key, checksum, size)
            if existing is not None:
                jobs.update(requested_id, phase='complete', message='동일 파일 재시도를 기존 자료에 연결했습니다.', progress=100,
                            result={'source_id': existing.get('id')})
                return
            result = parse_staged_upload(name, destination, size, ext, mime, requested_id,
                                         lambda *args: _insert_uploaded(*args, checksum=checksum, size=size, idempotency_key=idempotency_key))
            if result is not None and not jobs.is_cancelled(requested_id):
                jobs.update(requested_id, phase='complete', message='업로드와 분석 완료', progress=100, result={'source_id': result['id']})
        except Exception:
            # parse_staged_upload stores the public error detail and always
            # removes the staged original; the worker itself remains alive.
            pass
        finally:
            _upload_parse_slots.release()
            with _upload_job_lock:
                _active_upload_jobs.discard(requested_id)

    try:
        threading.Thread(target=run, name=f'source-upload-{requested_id[:16]}', daemon=True).start()
    except Exception:
        destination.unlink(missing_ok=True)
        _upload_parse_slots.release()
        with _upload_job_lock:
            _active_upload_jobs.discard(requested_id)
        raise
    return {'job_id': requested_id, 'accepted': True, 'already_running': False, 'phase': 'queued'}


def resume_source_upload(job_id: str) -> dict:
    state = jobs.get(job_id)
    payload = (state or {}).get('payload') or {}
    if not state or payload.get('kind') != 'source_upload':
        raise HTTPException(400, '재개할 수 있는 업로드 작업이 아닙니다.')
    if state.get('phase') not in {'interrupted', 'error', 'cancelled'}:
        raise HTTPException(409, '현재 상태에서는 업로드 작업을 재개할 수 없습니다.')
    try:
        path = (UPLOADS_DIR / Path(payload['staged_name']).name).resolve()
        if path.parent != UPLOADS_DIR.resolve() or not path.is_file(): raise ValueError('staged file missing')
        if path.stat().st_size != int(payload['size']) or sha256_file(path) != payload['checksum']: raise ValueError('checksum mismatch')
    except (KeyError, OSError, ValueError):
        jobs.update(job_id, phase='error', message='원본 검증 실패로 재업로드가 필요합니다.', progress=100, error='staged_upload_verification_failed')
        raise HTTPException(409, '보관된 업로드 원본을 검증할 수 없습니다. 원본을 다시 업로드하세요.')
    if not _upload_parse_slots.acquire(blocking=False): raise HTTPException(429, '업로드 분석 대기열이 가득 찼습니다.')
    jobs.update(job_id, phase='queued', message='검증된 업로드 분석을 재개했습니다.', progress=56)
    name, size, ext, mime = payload['filename'], int(payload['size']), payload['extension'], payload['mime']
    checksum, idempotency_key = payload['checksum'], payload['idempotency_key']
    def run() -> None:
        try:
            existing = _existing_upload(idempotency_key, checksum, size)
            if existing is not None:
                jobs.update(job_id, phase='complete', message='동일 파일 재시도를 기존 자료에 연결했습니다.', progress=100, result={'source_id': existing.get('id')})
            else:
                parse_staged_upload(name, path, size, ext, mime, job_id, lambda *args: _insert_uploaded(*args, checksum=checksum, size=size, idempotency_key=idempotency_key))
        except Exception:
            pass
        finally:
            _upload_parse_slots.release()
    threading.Thread(target=run, name=f'source-upload-resume-{job_id[:12]}', daemon=True).start()
    return {'job_id': job_id, 'accepted': True, 'resumed': True, 'phase': 'queued'}


def add_web(url: str, title: str='') -> dict:
    page_title, text, metadata, mime_type = _fetch_web_content(url, title)
    return _insert('web',page_title,'',url,mime_type,'',text,metadata)


def _fetch_web_content(url: str, title: str='') -> tuple[str, str, dict, str]:
    url=_public_url(url)
    try:
        with httpx.Client(timeout=httpx.Timeout(20), follow_redirects=False, headers={'User-Agent':'AI-Course-Studio/1.3'}) as client:
            current=url
            for _ in range(5):
                current=_public_url(current)
                r=client.get(current)
                if r.status_code in (301,302,303,307,308) and r.headers.get('location'):
                    from urllib.parse import urljoin
                    current=urljoin(current,r.headers['location'])
                    continue
                r.raise_for_status(); break
            else: raise HTTPException(400,'리디렉션이 너무 많습니다.')
            if len(r.content)>8*1024*1024: raise HTTPException(413,'웹 페이지가 너무 큽니다.')
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,f'웹 페이지를 가져오지 못했습니다: {e}')
    soup=BeautifulSoup(r.text,'html.parser')
    for x in soup(['script','style','noscript','nav','footer']): x.decompose()
    page_title=title.strip() or (soup.title.get_text(' ',strip=True) if soup.title else urlparse(url).netloc)
    text=soup.get_text('\n',strip=True)[:TEXT_LIMIT]
    return page_title, text, {'final_url':str(r.url),'chars':len(text)}, r.headers.get('content-type','text/html')


def refresh_web_sources(ids: list[int], force: bool = False, max_age_hours: int = 24) -> dict:
    """Refresh public web snapshots; a failure keeps the last usable indexed text."""
    refreshed, skipped, failed = [], [], []
    cutoff = datetime.now().timestamp() - max_age_hours * 3600
    for source_id in ids:
        try:
            source = get_source(source_id)
            if source.get('kind') != 'web' or not source.get('url'):
                skipped.append(source_id); continue
            try:
                last = datetime.fromisoformat((source.get('updated_at') or '').replace('Z','+00:00')).timestamp()
            except ValueError:
                last = 0
            if not force and last >= cutoff:
                skipped.append(source_id); continue
            title, text, metadata, mime_type = _fetch_web_content(source['url'], source.get('title') or '')
            if not text: raise ValueError('본문에서 저장할 텍스트를 찾지 못했습니다.')
            digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
            update_source_record(source_id,title=title,mime_type=mime_type,extracted_text=text,summary='',status='ready',metadata_json=json.dumps(metadata,ensure_ascii=False),metadata=metadata,updated_at=_now(),content_hash=digest,vector_status='pending',storage_mode='database-only')
            index_source(source_id, text); mirror_source(get_source(source_id)); refreshed.append(source_id)
        except Exception as exc:
            failed.append({'id':source_id,'error':str(exc)[:240]})
    return {'refreshed':refreshed,'skipped':skipped,'failed':failed}


def add_video(url: str, title: str='') -> dict:
    url=_public_url(url); text,meta=_youtube_transcript(url)
    if meta.get('video_kind')=='youtube':
        metadata=_youtube_metadata(url); meta.update(metadata)
        name=title.strip() or metadata['title']
        if not text:
            text=f"[YouTube 영상 참고자료]\n제목: {name}\n채널: {metadata['author_name']}\nURL: {url}\n자막 상태: {meta['transcript_status']}\n\n이 영상은 자막 원문을 가져오지 못했습니다. 교재에서 영상 제목·채널·URL만 참고하고, 영상 속 주장이나 수치의 사실 여부는 원본 영상과 공식 출처로 다시 확인하세요."
            meta['transcript']='metadata_only'
        return _insert('video',name,'',url,'text/url','',text,meta,'ready')
    name=title.strip() or '공개 영상 URL'
    return _insert('video',name,'',url,'text/url','','',meta,'link_only')


def refresh_video_transcript(source_id: int) -> dict:
    source=get_source(source_id)
    if source.get('kind') != 'video' or not _youtube_id(source.get('url') or ''):
        raise HTTPException(400,'YouTube 영상 자료만 자막을 다시 가져올 수 있습니다.')
    text, meta=_youtube_transcript(source['url']); metadata=_youtube_metadata(source['url']); meta.update(metadata)
    if not text:
        raise HTTPException(422,f"자막을 아직 가져오지 못했습니다: {meta.get('transcript_status')}. 영상에 공개 또는 자동 자막이 있는지 확인한 뒤 다시 시도하세요.")
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    update_source_record(source_id,extracted_text=text[:TEXT_LIMIT],summary='',status='ready',metadata_json=json.dumps(meta,ensure_ascii=False),metadata=meta,updated_at=_now(),content_hash=digest,vector_status='pending')
    index_source(source_id,text[:TEXT_LIMIT]); mirror_source(get_source(source_id))
    return {'id':source_id,'title':source['title'],'transcript_status':meta['transcript_status'],'chars':len(text)}


def list_sources() -> list[dict]:
    rows=source_records()
    if rows is None:
        c=connect(); rows=[dict(x) for x in c.execute('SELECT * FROM sources ORDER BY id DESC')]; c.close()
    rows.sort(key=lambda row: row.get('id', 0), reverse=True)
    for r in rows:
        metadata=r.pop('metadata_json', None)
        r['metadata']=r.get('metadata') or (json.loads(metadata or '{}') if isinstance(metadata, str) else {})
        r['has_text']=bool(r.get('extracted_text')); r['extracted_text']=''; r['original_retained']=bool(r.get('local_path'))
        if r.get('summary_path') and Path(r['summary_path']).exists(): r['summary_download_url']=f"/api/sources/{r['id']}/summary-file"
    return rows


def get_source(source_id:int) -> dict:
    d=source_record(source_id)
    if d is None:
        c=connect(); row=c.execute('SELECT * FROM sources WHERE id=?',(source_id,)).fetchone(); c.close()
        if not row: raise HTTPException(404,'자료를 찾을 수 없습니다.')
        d=dict(row)
    d['metadata']=d.get('metadata') or json.loads(d.get('metadata_json') or '{}')
    return d


def delete_source(source_id:int):
    d=get_source(source_id)
    if d.get('local_path'):
        try: Path(d['local_path']).unlink(missing_ok=True)
        except Exception: pass
    if d.get('summary_path'):
        try:
            summary_path=Path(d['summary_path'])
            if summary_path.parent.resolve() == SUMMARY_EXPORTS_DIR.resolve(): summary_path.unlink(missing_ok=True)
        except Exception: pass
    delete_source_mirror(source_id)
    return {'ok':True}


def source_context(ids:list[int], query:str='', max_total:int=24_000) -> str:
    return build_source_context(ids, query, max_total, CONTEXT_PER_SOURCE)


def summarize_source(source_id:int, provider_manager, provider:str, job_id: str='') -> dict:
    d=get_source(source_id); text=(d.get('extracted_text') or '').strip()
    def update(completed: int, total: int, message: str):
        if job_id: jobs.update(job_id, phase='summarizing', message=message, progress=min(96, 8 + int(88 * completed / max(total, completed))))
    if job_id: jobs.update(job_id, phase='summarizing', message='자료 길이와 모델 한도를 확인하는 중', progress=5)
    if not text:
        if d['kind']=='image' and d.get('local_path'):
            try:
                summary=provider_manager.describe_image(provider,d['local_path'],'이 이미지를 AI 초보자 강의자료의 참고자료로 사용하려고 합니다. 이미지에서 실제로 보이는 내용만 설명하고, 핵심 요소 5개와 강의 활용 포인트 3개를 한국어로 정리하세요. 글자가 불확실하면 추측하지 마세요.')
            except Exception as e:
                summary=f'이미지 원본은 보관되어 있으나 선택 모델의 이미지 분석에 실패했습니다: {e}'
        elif d['kind']=='video':
            summary='영상 링크 메타데이터만 저장되어 있어 AI 요약을 만들 수 없습니다. 자료 목록의 자막 다시 가져오기를 실행하거나, YouTube에서 공개·자동 자막을 켠 뒤 다시 시도하세요.'
        else: summary='텍스트를 추출할 수 없어 자동 요약을 생략했습니다.'
    else:
        summary=summarize_text(provider_manager,provider,text,update)
    filename=f"source_{source_id}_summary.md"; destination=SUMMARY_EXPORTS_DIR/filename
    markdown=f"# 참고자료 요약 · {d['title']}\n\n- 생성일: {_now()}\n- AI Provider: {provider}\n- 원본: {d.get('url') or d.get('original_name') or '업로드 자료'}\n\n## 요약\n\n{summary}\n"
    destination.write_text(markdown,encoding='utf-8')
    update_source_record(source_id,summary=summary,summary_path=str(destination),status='summarized')
    mirror_source(get_source(source_id))
    if job_id: jobs.update(job_id, phase='complete', message='요약 파일 생성 완료', progress=100)
    return {'id':source_id,'title':d['title'],'summary':summary,'download_url':f'/api/sources/{source_id}/summary-file'}


def start_source_summary(source_id: int, provider_manager, provider: str, job_id: str = '') -> dict:
    """Queue a source summary so a long local-model call never owns the HTTP request.

    A PPTX can produce dozens of bounded model calls.  Returning immediately
    keeps the browser connection independent from LM Studio latency and lets
    the existing job endpoint provide progress and the final download link.
    """
    source = get_source(source_id)  # validate before acknowledging the job
    requested_id = job_id or str(uuid.uuid4())
    with _summary_job_lock:
        existing_id = _active_summary_jobs.get(source_id)
        if existing_id:
            existing = jobs.get(existing_id)
            if existing and existing.get('phase') not in {'complete', 'error'}:
                return {
                    'job_id': existing_id,
                    'source_id': source_id,
                    'title': source['title'],
                    'accepted': True,
                    'already_running': True,
                }
        if not _summary_slots.acquire(blocking=False):
            raise HTTPException(429, '요약 작업 대기열이 가득 찼습니다. 현재 작업이 끝난 뒤 다시 시도하세요.')
        _active_summary_jobs[source_id] = requested_id
        try:
            jobs.update(requested_id, phase='queued', message='요약 작업을 대기열에 추가했습니다.', progress=1, error='', result=None)
        except Exception:
            _active_summary_jobs.pop(source_id, None)
            _summary_slots.release()
            raise

    def run() -> None:
        try:
            result = summarize_source(source_id, provider_manager, provider, requested_id)
            jobs.update(requested_id, phase='complete', message='요약 파일 생성 완료', progress=100, result=result)
        except Exception as exc:
            detail = str(getattr(exc, 'detail', exc))
            jobs.update(requested_id, phase='error', message='자료 요약 실패', progress=100, error=detail[:1000])
        finally:
            _summary_slots.release()
            with _summary_job_lock:
                if _active_summary_jobs.get(source_id) == requested_id:
                    _active_summary_jobs.pop(source_id, None)

    try:
        threading.Thread(target=run, name=f'source-summary-{source_id}', daemon=True).start()
    except Exception:
        with _summary_job_lock:
            if _active_summary_jobs.get(source_id) == requested_id:
                _active_summary_jobs.pop(source_id, None)
        _summary_slots.release()
        raise
    return {'job_id': requested_id, 'source_id': source_id, 'title': source['title'], 'accepted': True, 'already_running': False}


def summary_file(source_id: int) -> Path:
    source=get_source(source_id); path=Path(source.get('summary_path') or '')
    if not path.exists() or path.parent.resolve() != SUMMARY_EXPORTS_DIR.resolve():
        raise HTTPException(404,'생성된 요약 파일을 찾을 수 없습니다.')
    return path


def make_source_pack(ids:list[int]) -> dict:
    if not ids: raise HTTPException(400,'자료를 하나 이상 선택하세요.')
    pack_name=f"gemini_notebook_pack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"; dest=SOURCE_PACKS_DIR/pack_name
    manifest=['# AI 강의 활용 Studio · Gemini Notebook 자료팩','',f'생성일: {_now()}','']
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for sid in ids:
            d=get_source(sid); manifest += [f"## {d['title']}",f"- 종류: {d['kind']}",f"- URL: {d['url'] or '-'}",f"- 요약: {d['summary'] or '미생성'}",'']
            if d.get('local_path') and Path(d['local_path']).exists(): z.write(d['local_path'],arcname=f"sources/{Path(d['local_path']).name}")
            elif d.get('extracted_text'):
                z.writestr(f"sources/source_{sid}.md",f"# {d['title']}\n\n원본: {d['url']}\n\n{d['extracted_text']}")
        z.writestr('MANIFEST.md','\n'.join(manifest))
    return {'ok':True,'filename':pack_name,'download_url':f'/api/sources/pack/{pack_name}'}
