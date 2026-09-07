# SearXNG + Firecrawl 롤백

## 안전한 중지

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_searxng.ps1
```

이 작업은 별도 SearXNG 컨테이너와 네트워크만 중지합니다. 기존 Studio·DB 컨테이너와 데이터는 변경하지 않습니다.

## 코드 복구

1. 진행 중인 교재 생성을 완료하거나 Studio를 정상 종료합니다.
2. `backups/searxng_firecrawl_pre_20260829_0325.zip`을 별도 폴더에 풉니다.
3. 백업에 들어 있는 기존 파일만 동일한 프로젝트 경로로 복사합니다.
4. 새로 추가된 파일은 즉시 삭제하지 않고 별도 보관한 뒤 구버전 실행을 검증합니다.
5. `run_windows.bat`로 서버를 시작하고 `/api/health`를 확인합니다.

## 설정만 비활성화

전체 코드 복구 없이 웹 검색만 끄려면 실제 `.env`에 다음을 설정하고 Studio를 재시작합니다.

```env
AI_COURSE_STUDIO_WEB_SEARCH_PROVIDER=disabled
FIRECRAWL_ENABLED=false
```

## 데이터베이스

- 기존 사용자 데이터와 근거팩을 삭제하지 않습니다.
- 추가된 `web_api_usage` 테이블은 독립적인 요청 카운터이므로 남아 있어도 기존 버전에 영향을 주지 않습니다.
- 롤백 과정에서 SQLite DB를 삭제·초기화하지 않습니다.

## SearXNG 볼륨

기본 롤백에서는 캐시 볼륨을 삭제하지 않습니다. 디스크 정리가 필요하면 정상 복구 확인 후 별도 승인을 받아 처리합니다.
