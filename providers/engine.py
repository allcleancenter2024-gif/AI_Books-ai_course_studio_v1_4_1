from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Any
import json
import os
import re
import time
import base64
import mimetypes
from pathlib import Path
from threading import RLock, Thread

import httpx


@dataclass
class ProviderConfig:
    name: str
    model: str
    base_url: str
    api_key_env: str = ""
    api_key: str = ""
    timeout: float = 120.0

    def public(self) -> dict[str, Any]:
        d = asdict(self)
        d["api_key"] = ""
        d["has_key"] = bool(self.api_key or (self.api_key_env and os.getenv(self.api_key_env)))
        return d


LOCAL_PROVIDERS = ("lmstudio", "ollama")

DEFAULTS: dict[str, ProviderConfig] = {
    "lmstudio": ProviderConfig(
        name="lmstudio",
        model="",
        base_url="http://127.0.0.1:12345/v1",
        api_key="lm-studio",
        # A local course stage should fail visibly rather than holding a job
        # at one percentage point for fifteen minutes.
        timeout=180.0,
    ),
    "ollama": ProviderConfig(
        name="ollama",
        # Never pin a large local model as the application default.  The
        # auto-connect flow inspects the models that are actually installed
        # and chooses a resource-conscious general model.
        model="",
        base_url="http://127.0.0.1:11434/v1",
        api_key="ollama",
        timeout=900.0,
    ),
}


class ProviderError(RuntimeError):
    pass


class ProviderManager:
    """One interface for the two supported local AI runtimes."""

    def __init__(self) -> None:
        self.configs = {k: ProviderConfig(**asdict(v)) for k, v in DEFAULTS.items()}
        self._failover_lock = RLock()
        self._failover_events: list[dict[str, str]] = []

    def get(self, name: str) -> ProviderConfig:
        if name not in self.configs:
            raise ProviderError(f"지원하지 않는 Provider입니다: {name}")
        return self.configs[name]

    def list_public(self) -> list[dict[str, Any]]:
        return [self.configs[k].public() for k in LOCAL_PROVIDERS]

    def configure(
        self,
        name: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        cfg = self.get(name)
        if model is not None:
            cfg.model = model.strip()
        if base_url is not None and base_url.strip():
            cfg.base_url = base_url.strip().rstrip("/")
        if api_key is not None:
            # runtime memory only; blank means use environment variable/default
            cfg.api_key = api_key.strip()
        if timeout is not None:
            cfg.timeout = max(30.0, min(float(timeout), 3600.0))
        return cfg.public()

    @staticmethod
    def _recommended_model(models: list[str], current: str = "") -> str:
        """Keep the current model, otherwise use the server's first chat model.

        Local runtimes normally put the loaded/default model first. Preserving
        that order avoids unexpectedly loading a much larger model.
        """
        if current and current in models:
            return current
        candidates = [m for m in models if not re.search(r"embed|embedding|rerank", m, re.I)] or models
        return candidates[0]

    @staticmethod
    def _ollama_native_url(base_url: str, path: str) -> str:
        """Translate an OpenAI-compatible Ollama URL to its native API URL."""
        root = re.sub(r"/v1/?$", "", base_url.rstrip("/"), flags=re.I)
        return f"{root}/{path.lstrip('/')}"

    def _ollama_models(self, cfg: ProviderConfig) -> list[dict[str, Any]]:
        """Return Ollama model metadata, including on-disk size."""
        response = httpx.get(self._ollama_native_url(cfg.base_url, "/api/tags"), timeout=httpx.Timeout(15.0))
        response.raise_for_status()
        data = response.json()
        rows = data.get("models", []) if isinstance(data, dict) else []
        return [row for row in rows if isinstance(row, dict) and (row.get("model") or row.get("name"))]

    def _lmstudio_models(self, cfg: ProviderConfig) -> list[dict[str, Any]]:
        """Return native LM Studio model metadata."""
        root = re.sub(r"/v1/?$", "", cfg.base_url.rstrip("/"), flags=re.I)
        response = httpx.get(f"{root}/api/v1/models", timeout=httpx.Timeout(15.0))
        response.raise_for_status()
        data = response.json()
        rows = data.get("models", []) if isinstance(data, dict) else []
        return [row for row in rows if isinstance(row, dict) and row.get("key")]

    def ensure_lmstudio_model_loaded(self, model: str, context_length: int = 8192) -> None:
        """Load one LM Studio model before issuing a parallel generation batch.

        LM Studio can auto-load a model for a single request, but several cold
        requests arriving together may race while the model instance is being
        created.  Explicit loading makes model failover deterministic.
        """
        cfg = self.get("lmstudio")
        rows = self._lmstudio_models(cfg)
        row = next((item for item in rows if str(item.get("key")) == model), None)
        if row is None:
            raise ProviderError(f"LM Studio에 설치된 모델을 찾지 못했습니다: {model}")
        if row.get("loaded_instances"):
            return
        max_context = int(row.get("max_context_length") or context_length)
        body = {
            "model": model,
            "context_length": max(2048, min(int(context_length), max_context)),
            "echo_load_config": False,
        }
        root = re.sub(r"/v1/?$", "", cfg.base_url.rstrip("/"), flags=re.I)
        headers = {"Content-Type": "application/json"}
        key = self._key(cfg)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        try:
            response = httpx.post(
                f"{root}/api/v1/models/load",
                headers=headers,
                json=body,
                timeout=httpx.Timeout(cfg.timeout),
            )
            self._raise(response, "LM Studio 모델 로드")
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ProviderError(f"LM Studio 모델 로드 중 연결이 끊겼습니다: {model}") from exc

    @staticmethod
    def _recommended_lmstudio_models(rows: list[dict[str, Any]], current: str = "") -> list[str]:
        """Order safe chat LLMs and never route generation to embeddings."""
        usable = [
            row for row in rows
            if row.get("type") == "llm"
            and not re.search(r"embed|embedding|rerank|code|coder", str(row.get("key") or ""), re.I)
        ]
        target = 3 * 1024**3
        usable.sort(key=lambda row: (
            int(row.get("size_bytes") or 0) > 8 * 1024**3,
            row.get("format") != "gguf",
            abs(int(row.get("size_bytes") or 0) - target),
        ))
        names = [str(row.get("key")) for row in usable]
        if current in names:
            names.remove(current)
            names.insert(0, current)
        return names

    def model_candidates(self, provider: str, current: str = "") -> list[str]:
        cfg = self.get(provider)
        selected = current or cfg.model
        if provider == "lmstudio":
            try:
                candidates = self._recommended_lmstudio_models(self._lmstudio_models(cfg), selected)
                if candidates:
                    if selected and selected not in candidates:
                        candidates.insert(0, selected)
                    return candidates
            except Exception:
                pass
        models = self.list_models(provider, strict=False)
        usable = [model for model in models if not re.search(r"embed|embedding|rerank", model, re.I)]
        if selected and selected not in usable:
            usable.insert(0, selected)
        elif selected in usable:
            usable.remove(selected)
            usable.insert(0, selected)
        return usable

    def _record_failover(self, previous: str, selected: str, reason: str) -> None:
        if not previous or previous == selected:
            return
        with self._failover_lock:
            self._failover_events.append({"from": previous, "to": selected, "reason": reason[:240]})

    def consume_failovers(self) -> list[dict[str, str]]:
        with self._failover_lock:
            events, self._failover_events = self._failover_events, []
        unique: list[dict[str, str]] = []
        for event in events:
            if not any(item["from"] == event["from"] and item["to"] == event["to"] for item in unique):
                unique.append(event)
        return unique

    @staticmethod
    def _recommended_ollama_model(rows: list[dict[str, Any]], current: str = "") -> str:
        """Prefer an explicitly selected model, otherwise a safe general model.

        Prefer a roughly 3 GiB general model for interactive course generation.
        Inference also needs KV cache and runtime memory, and this workflow makes
        three structured calls per week. Users can still explicitly select a
        larger installed model when quality matters more than generation time.
        """
        names = [str(row.get("model") or row.get("name") or "") for row in rows]
        if current and current in names:
            return current
        usable = [
            row for row in rows
            if not re.search(r"embed|embedding|rerank", str(row.get("model") or row.get("name") or ""), re.I)
        ] or rows
        general = [
            row for row in usable
            if not re.search(r"code|coder|opencode", str(row.get("model") or row.get("name") or ""), re.I)
        ] or usable
        balanced = [row for row in general if 2 * 1024**3 <= int(row.get("size") or 0) <= 6 * 1024**3]
        safe = [row for row in general if 0 < int(row.get("size") or 0) <= 8 * 1024**3]
        pool = balanced or safe or general
        chosen = min(pool, key=lambda row: abs(int(row.get("size") or 0) - 3 * 1024**3))
        return str(chosen.get("model") or chosen.get("name"))

    def auto_connect(self, provider: str) -> dict[str, Any]:
        """Detect a local server, choose a model and verify generation."""
        cfg = self.get(provider)
        candidates = [cfg.base_url]
        if provider == "lmstudio":
            candidates += ["http://127.0.0.1:1234/v1", "http://localhost:1234/v1", "http://127.0.0.1:12345/v1"]
        else:
            candidates += ["http://127.0.0.1:11434/v1", "http://localhost:11434/v1"]
        errors: list[str] = []
        original_url, original_model = cfg.base_url, cfg.model
        for base_url in dict.fromkeys(candidates):
            cfg.base_url = base_url.rstrip("/")
            try:
                ollama_rows = self._ollama_models(cfg) if provider == "ollama" else []
                lmstudio_rows = []
                if provider == "lmstudio":
                    try:
                        lmstudio_rows = self._lmstudio_models(cfg)
                    except Exception:
                        lmstudio_rows = []
                models = ([str(row.get("model") or row.get("name")) for row in ollama_rows]
                          if ollama_rows else self._recommended_lmstudio_models(lmstudio_rows, original_model)
                          if lmstudio_rows else self.list_models(provider, strict=True))
                if not models:
                    errors.append(f"{base_url}: 실행 가능한 모델 없음")
                    continue
                cfg.model = (self._recommended_ollama_model(ollama_rows, original_model)
                             if ollama_rows else models[0] if lmstudio_rows else self._recommended_model(models, original_model))
                checked = self.test(provider)
                selected_row = next((row for row in ollama_rows if (row.get("model") or row.get("name")) == cfg.model), {})
                return {
                    **checked,
                    "base_url": cfg.base_url,
                    "models": models,
                    "model_count": len(models),
                    "automatic": True,
                    "selected_model_size": int(selected_row.get("size") or 0),
                }
            except Exception as exc:
                errors.append(f"{base_url}: {str(exc)[:180]}")
        cfg.base_url, cfg.model = original_url, original_model
        label = "LM Studio" if provider == "lmstudio" else "Ollama"
        raise ProviderError(f"{label} 자동 연결에 실패했습니다. 앱과 로컬 서버를 실행한 뒤 다시 시도하세요. " + " | ".join(errors))

    def _key(self, cfg: ProviderConfig) -> str:
        if cfg.api_key:
            return cfg.api_key
        if cfg.api_key_env:
            return os.getenv(cfg.api_key_env, "")
        return ""

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        """Small bounded backoff for temporary provider failures."""
        return 0.75 * (2 ** attempt)

    def _post_json_with_retry(self, url: str, *, headers: dict[str, str], body: dict[str, Any], timeout: httpx.Timeout, label: str) -> dict[str, Any]:
        """Retry only failures that are normally transient, never auth/validation errors."""
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, headers=headers, json=body)
                if response.status_code in (408, 409, 429, 500, 502, 503, 504):
                    last_error = ProviderError(f"{label} API 일시 오류 ({response.status_code})")
                    if attempt < 2:
                        time.sleep(self._retry_delay(attempt))
                        continue
                self._raise(response, label)
                data = response.json()
                if isinstance(data, dict):
                    return data
                raise ProviderError(f"{label} API가 JSON 객체가 아닌 응답을 반환했습니다.")
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(self._retry_delay(attempt))
                    continue
                raise ProviderError(f"{label} 연결이 반복해서 시간초과되거나 끊겼습니다. 잠시 후 다시 시도하세요.") from exc
        raise ProviderError(f"{label} API가 일시 오류 후 복구되지 않았습니다. 잠시 후 다시 시도하세요.") from last_error

    @staticmethod
    def _post_with_total_timeout(url: str, *, headers: dict[str, str], body: dict[str, Any], timeout: httpx.Timeout, total_seconds: float) -> httpx.Response:
        """Bound wall-clock time even when a server sends intermittent bytes.

        httpx's read timeout is intentionally reset after every received byte.
        Local model servers can therefore keep a synchronous generation alive
        indefinitely while streaming internal progress. Closing this dedicated
        client on expiry releases the socket and lets the course fallback run.
        """
        client=httpx.Client(timeout=timeout)
        outcome: dict[str, Any]={}
        def request() -> None:
            try: outcome['response']=client.post(url,headers=headers,json=body)
            except BaseException as exc: outcome['error']=exc
        worker=Thread(target=request,name='local-ai-request',daemon=True)
        worker.start(); worker.join(total_seconds)
        close = getattr(client, "close", None)
        if worker.is_alive():
            if close: close()
            worker.join(2)
            raise httpx.ReadTimeout(f'local model total timeout after {total_seconds:.0f}s')
        if close: close()
        if 'error' in outcome: raise outcome['error']
        return outcome['response']

    def generate(
        self,
        provider: str,
        system: str,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 6000,
        temperature: float = 0.3,
        json_mode: bool = False,
        allow_failover: bool = True,
    ) -> str:
        cfg = self.get(provider)
        chosen_model = (model or cfg.model).strip()
        if not chosen_model and provider in ("lmstudio", "ollama"):
            if provider == "ollama":
                rows = self._ollama_models(cfg)
                if rows:
                    cfg.model = chosen_model = self._recommended_ollama_model(rows)
            else:
                models = self.model_candidates(provider)
                if models:
                    cfg.model = chosen_model = models[0]
        if not chosen_model:
            label = "LM Studio" if provider == "lmstudio" else "Ollama" if provider == "ollama" else provider
            raise ProviderError(f"{label}에서 실행 가능한 모델을 찾지 못했습니다. 모델을 먼저 불러오고 '모델 찾기'를 누르세요.")

        if provider == "openai":
            return self._openai(cfg, chosen_model, system, prompt, max_tokens, temperature)
        if provider == "gemini":
            return self._gemini(cfg, chosen_model, system, prompt, max_tokens, temperature)
        if provider == "claude":
            return self._claude(cfg, chosen_model, system, prompt, max_tokens, temperature)
        if provider == "ollama":
            return self._ollama_chat(cfg, chosen_model, system, prompt, max_tokens, temperature, json_mode=json_mode)
        if provider == "lmstudio":
            candidates = (self.model_candidates(provider, chosen_model) or [chosen_model]) if allow_failover else [chosen_model]
            errors: list[str] = []
            for candidate in candidates:
                try:
                    text = self._lmstudio_chat(cfg, candidate, system, prompt, max_tokens, temperature, json_mode=json_mode)
                    if candidate != chosen_model:
                        self._record_failover(chosen_model, candidate, errors[-1] if errors else "이전 모델 생성 실패")
                    cfg.model = candidate
                    return text
                except ProviderError as exc:
                    errors.append(f"{candidate}: {exc}")
            raise ProviderError("LM Studio 사용 가능 모델이 모두 생성에 실패했습니다. " + " | ".join(errors))
        raise ProviderError(f"지원하지 않는 Provider입니다: {provider}")

    def describe_image(self, provider: str, image_path: str, prompt: str) -> str:
        cfg = self.get(provider)
        model = cfg.model.strip()
        if not model:
            raise ProviderError("이미지 분석에 사용할 모델을 선택하세요.")
        p = Path(image_path)
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        key = self._key(cfg)
        try:
            if provider == "openai":
                if not key: raise ProviderError("OpenAI API 키가 없습니다.")
                body={"model":model,"instructions":"이미지에서 확인되는 내용만 교육자료용으로 설명하세요.","input":[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:{mime};base64,{b64}"}]}],"max_output_tokens":1400}
                r=httpx.post(cfg.base_url.rstrip("/")+"/responses",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=body,timeout=httpx.Timeout(cfg.timeout)); self._raise(r,"OpenAI"); data=r.json()
                if data.get("output_text"): return data["output_text"]
                texts=[]
                for item in data.get("output",[]):
                    for c in item.get("content",[]):
                        if isinstance(c,dict) and isinstance(c.get("text"),str): texts.append(c["text"])
                if texts:return "\n".join(texts)
            elif provider == "gemini":
                if not key: raise ProviderError("Gemini API 키가 없습니다.")
                url=f"{cfg.base_url.rstrip('/')}/models/{model}:generateContent"
                body={"contents":[{"role":"user","parts":[{"text":prompt},{"inlineData":{"mimeType":mime,"data":b64}}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":1400}}
                r=httpx.post(url,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=body,timeout=httpx.Timeout(cfg.timeout)); self._raise(r,"Gemini"); data=r.json(); texts=[part.get("text","") for c in data.get("candidates",[]) for part in c.get("content",{}).get("parts",[]) if isinstance(part,dict) and part.get("text")];
                if texts:return "\n".join(texts)
            elif provider == "claude":
                if not key: raise ProviderError("Claude API 키가 없습니다.")
                body={"model":model,"max_tokens":1400,"temperature":0.2,"messages":[{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":mime,"data":b64}},{"type":"text","text":prompt}]}]}
                r=httpx.post(cfg.base_url.rstrip("/")+"/messages",headers={"x-api-key":key,"anthropic-version":"2023-06-01","Content-Type":"application/json"},json=body,timeout=httpx.Timeout(cfg.timeout)); self._raise(r,"Claude"); data=r.json(); texts=[x.get("text","") for x in data.get("content",[]) if isinstance(x,dict) and x.get("type")=="text"];
                if texts:return "\n".join(texts)
            elif provider in ("lmstudio","ollama"):
                url=cfg.base_url.rstrip("/")+"/chat/completions"; body={"model":model,"messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}]}],"temperature":0.2,"max_tokens":1400,"stream":False}
                r=httpx.post(url,headers={"Authorization":f"Bearer {self._key(cfg) or 'local'}","Content-Type":"application/json"},json=body,timeout=httpx.Timeout(connect=8,read=max(cfg.timeout,300),write=60,pool=10)); self._raise(r,"LM Studio" if provider=="lmstudio" else "Ollama"); data=r.json(); text=data.get("choices",[{}])[0].get("message",{}).get("content","");
                if text:return text
        except httpx.HTTPError as e:
            raise ProviderError(f"이미지 분석 연결 오류: {e}") from e
        raise ProviderError("선택한 모델이 이미지 분석을 지원하지 않거나 텍스트 응답을 반환하지 않았습니다.")

    def test(self, provider: str) -> dict[str, Any]:
        cfg = self.get(provider)
        if provider in ("lmstudio", "ollama") and not cfg.model:
            models = self.list_models(provider, strict=True)
            if models:
                cfg.model = models[0]
        text = self.generate(
            provider,
            "짧고 정확하게 답하세요.",
            "연결 확인입니다. 정확히 '연결 성공'이라고만 답하세요.",
            max_tokens=256,
            temperature=0,
        )
        return {"ok": True, "provider": provider, "model": cfg.model, "response": text.strip()[:200]}

    def list_models(self, provider: str, strict: bool = False) -> list[str]:
        cfg = self.get(provider)
        timeout = httpx.Timeout(15.0)
        try:
            if provider in ("lmstudio", "ollama"):
                if provider == "ollama":
                    return [str(row.get("model") or row.get("name")) for row in self._ollama_models(cfg)]
                url = cfg.base_url.rstrip("/") + "/models"
                headers = {"Authorization": f"Bearer {self._key(cfg) or 'local'}"}
                r = httpx.get(url, headers=headers, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            if provider == "openai":
                key = self._key(cfg)
                if not key:
                    return []
                r = httpx.get(cfg.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                return sorted([m.get("id", "") for m in data.get("data", []) if m.get("id")])
        except Exception as exc:
            if strict:
                label = "LM Studio" if provider == "lmstudio" else "Ollama" if provider == "ollama" else provider
                raise ProviderError(f"{label} 모델 목록을 가져오지 못했습니다. 서버 실행 여부와 Base URL({cfg.base_url})을 확인하세요: {exc}") from exc
            return []
        return []

    def _openai(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float) -> str:
        key = self._key(cfg)
        if not key:
            raise ProviderError("OpenAI API 키가 없습니다. 환경변수 OPENAI_API_KEY 또는 설정 화면에 입력하세요.")
        url = cfg.base_url.rstrip("/") + "/responses"
        body: dict[str, Any] = {
            "model": model,
            "instructions": system,
            "input": prompt,
            "max_output_tokens": max_tokens,
        }
        # Some reasoning models may reject temperature; only send when non-default model families allow it.
        if not model.startswith("gpt-5.6"):
            body["temperature"] = temperature
        try:
            data = self._post_json_with_retry(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body=body, timeout=httpx.Timeout(cfg.timeout), label="OpenAI")
            if isinstance(data.get("output_text"), str) and data["output_text"]:
                return data["output_text"]
            texts: list[str] = []
            for item in data.get("output", []):
                for c in item.get("content", []) if isinstance(item, dict) else []:
                    if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                        t = c.get("text")
                        if isinstance(t, str):
                            texts.append(t)
            if texts:
                return "\n".join(texts)
            raise ProviderError("OpenAI 응답에서 텍스트를 찾지 못했습니다.")
        except httpx.HTTPError as e:
            raise ProviderError(f"OpenAI 연결 오류: {e}") from e

    def _gemini(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float) -> str:
        key = self._key(cfg)
        if not key:
            raise ProviderError("Gemini API 키가 없습니다. 환경변수 GEMINI_API_KEY 또는 설정 화면에 입력하세요.")
        # generateContent remains supported and is intentionally used here for a small, dependency-light local app.
        url = f"{cfg.base_url.rstrip('/')}/models/{model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        try:
            data = self._post_json_with_retry(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, body=body, timeout=httpx.Timeout(cfg.timeout), label="Gemini")
            texts: list[str] = []
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        texts.append(part["text"])
            if texts:
                return "\n".join(texts)
            raise ProviderError("Gemini 응답에서 텍스트를 찾지 못했습니다.")
        except httpx.HTTPError as e:
            raise ProviderError(f"Gemini 연결 오류: {e}") from e

    def _claude(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float) -> str:
        key = self._key(cfg)
        if not key:
            raise ProviderError("Claude API 키가 없습니다. 환경변수 ANTHROPIC_API_KEY 또는 설정 화면에 입력하세요.")
        url = cfg.base_url.rstrip("/") + "/messages"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        try:
            data = self._post_json_with_retry(url, headers=headers, body=body, timeout=httpx.Timeout(cfg.timeout), label="Claude")
            texts = [x.get("text", "") for x in data.get("content", []) if isinstance(x, dict) and x.get("type") == "text"]
            text = "\n".join([t for t in texts if t])
            if text:
                return text
            raise ProviderError("Claude 응답에서 텍스트를 찾지 못했습니다.")
        except httpx.HTTPError as e:
            raise ProviderError(f"Claude 연결 오류: {e}") from e

    def _openai_compatible(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float, *, json_mode: bool = False) -> str:
        url = cfg.base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            # LM Studio/Ollama OpenAI-compatible servers commonly support JSON mode.
            # If a particular model/server rejects it, we retry once without this hint.
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._key(cfg) or 'local'}", "Content-Type": "application/json"}
        label = "LM Studio" if cfg.name == "lmstudio" else "Ollama"
        # Local LLMs can take several minutes to load a model and produce a large structured lesson.
        # Keep connection failures fast, but allow a long read window for generation.
        # Honor the timeout configured in the Studio UI.  The previous 900 s
        # floor made a 30–300 s operational limit ineffective and left a
        # course job apparently stuck even though the user had lowered it.
        timeout = httpx.Timeout(connect=8.0, read=cfg.timeout, write=60.0, pool=10.0)
        last_error = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout) as client:
                    r = client.post(url, headers=headers, json=body)
                    if json_mode and r.status_code in (400, 404, 422) and "response_format" in body:
                        fallback_body = dict(body)
                        fallback_body.pop("response_format", None)
                        r = client.post(url, headers=headers, json=fallback_body)
                    self._raise(r, label)
                    data = r.json()
                text = self._compatible_text(data)
                if text:
                    return text
                if attempt == 0:
                    # A reasoning model can spend the entire first budget before
                    # emitting visible content.  The old max(512, max_tokens)
                    # expression never increased a normal generation budget.
                    body["max_tokens"] = min(max(max_tokens * 2, 4096), 12_000)
                    body["messages"][-1]["content"] = prompt + "\n\n내부 추론만 하지 말고 최종 답변을 반드시 일반 텍스트로 출력하세요."
                    body.pop("response_format", None)
                    continue
                finish = ""
                if isinstance(data.get("choices"), list) and data["choices"]:
                    finish = str(data["choices"][0].get("finish_reason") or "")
                raise ProviderError(f"{label}가 빈 답변을 반환했습니다{f' (종료 사유: {finish})' if finish else ''}. 모델의 최대 출력 토큰을 늘리거나 다른 모델을 선택하세요.")
            except httpx.ConnectTimeout as e:
                raise ProviderError(
                    f"{label} 서버에 8초 안에 연결하지 못했습니다. 서버가 실행 중인지, Base URL({cfg.base_url})과 포트를 확인하세요."
                ) from e
            except httpx.ConnectError as e:
                raise ProviderError(
                    f"{label} 서버에 연결할 수 없습니다. 서버 실행 여부와 Base URL({cfg.base_url})을 확인하세요."
                ) from e
            except httpx.ReadTimeout as e:
                last_error = e
                if attempt == 0:
                    continue
                raise ProviderError(
                    f"{label} 모델이 15분 안에 생성을 끝내지 못했습니다. 더 작은/빠른 모델을 선택하거나 LM Studio의 컨텍스트·GPU 설정을 확인하세요."
                ) from e
            except httpx.ReadError as e:
                if cfg.name == "ollama":
                    raise ProviderError(
                        f"Ollama가 '{model}' 생성 중 연결을 강제로 종료했습니다. "
                        "대형 모델의 RAM/VRAM 부족으로 모델 프로세스가 재시작되었을 가능성이 큽니다. "
                        "Ollama 자동 연결을 다시 실행해 더 가벼운 모델을 선택하세요."
                    ) from e
                raise ProviderError(f"{label}가 생성 중 연결을 종료했습니다. 로컬 모델 서버 로그와 메모리 사용량을 확인하세요.") from e
            except httpx.HTTPError as e:
                raise ProviderError(f"{label} 연결 오류: {type(e).__name__}: {e}") from e
        raise ProviderError(f"{label} 생성 중 알 수 없는 오류가 발생했습니다: {last_error}")

    @staticmethod
    def _lmstudio_native_url(base_url: str) -> str:
        """Translate an OpenAI-compatible LM Studio URL to native v1 chat."""
        root = re.sub(r"/v1/?$", "", base_url.rstrip("/"), flags=re.I)
        return f"{root}/api/v1/chat"

    @staticmethod
    def _lmstudio_message_text(data: dict[str, Any]) -> str:
        """Return visible messages while deliberately ignoring reasoning items."""
        texts: list[str] = []
        output = data.get("output", []) if isinstance(data, dict) else []
        for item in output if isinstance(output, list) else []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())
        return "\n".join(texts)

    def _lmstudio_chat(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float, *, json_mode: bool = False) -> str:
        """Use LM Studio's native API so reasoning cannot consume all output."""
        url = self._lmstudio_native_url(cfg.base_url)
        body: dict[str, Any] = {
            "model": model,
            "input": prompt,
            "system_prompt": system,
            "stream": False,
            "store": False,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "reasoning": "off",
        }
        timeout = httpx.Timeout(connect=8.0, read=cfg.timeout, write=60.0, pool=10.0)
        headers = {"Authorization": f"Bearer {self._key(cfg) or 'local'}", "Content-Type": "application/json"}
        try:
            response = self._post_with_total_timeout(url, headers=headers, body=body, timeout=timeout, total_seconds=cfg.timeout)
            # Some non-reasoning models reject the reasoning option even
            # though the native endpoint itself is available.
            if response.status_code in (400, 422):
                retry_body = dict(body)
                retry_body.pop("reasoning", None)
                response = self._post_with_total_timeout(url, headers=headers, body=retry_body, timeout=timeout, total_seconds=cfg.timeout)
                # LM Studio before 0.4 has no native v1 endpoint. Preserve
                # support through the existing OpenAI-compatible endpoint.
                if response.status_code in (404, 405):
                    return self._openai_compatible(
                        cfg, model, system, prompt, max_tokens, temperature, json_mode=json_mode
                    )
            # Older LM Studio releases return 404/405 immediately because
            # the native v1 endpoint does not exist; use the legacy endpoint.
            if response.status_code in (404, 405):
                return self._openai_compatible(cfg, model, system, prompt, max_tokens, temperature, json_mode=json_mode)
            self._raise(response, "LM Studio")
            data = response.json()
            text = self._lmstudio_message_text(data)
            if text:
                return text
            stats = data.get("stats", {}) if isinstance(data, dict) else {}
            reasoning_tokens = int(stats.get("reasoning_output_tokens") or 0) if isinstance(stats, dict) else 0
            total_tokens = int(stats.get("total_output_tokens") or 0) if isinstance(stats, dict) else 0
            detail = f" (추론 {reasoning_tokens} / 전체 {total_tokens} 토큰)" if total_tokens else ""
            if total_tokens and reasoning_tokens >= max(1, int(total_tokens * 0.9)):
                raise ProviderError(
                    f"LM Studio reasoning_budget_exhausted: '{model}'이(가) 본문 대신 추론에 출력 예산을 모두 사용했습니다{detail}. "
                    "이 모델은 구조화 교재 생성 후보에서 제외합니다. reasoning을 끈 비추론 모델을 선택하세요."
                )
            raise ProviderError(
                f"LM Studio가 '{model}'에서 본문 없는 응답을 반환했습니다{detail}. "
                "LM Studio를 최신 버전으로 업데이트하거나 비추론 모델을 선택하세요."
            )
        except httpx.ConnectTimeout as exc:
            raise ProviderError(
                f"LM Studio 서버에 8초 안에 연결하지 못했습니다. 서버가 실행 중인지, Base URL({cfg.base_url})과 포트를 확인하세요."
            ) from exc
        except httpx.ConnectError as exc:
            raise ProviderError(
                f"LM Studio 서버에 연결할 수 없습니다. 서버 실행 여부와 Base URL({cfg.base_url})을 확인하세요."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise ProviderError(
                "LM Studio 모델이 제한 시간 안에 생성을 끝내지 못했습니다. 더 작은 모델을 선택하거나 Context Length를 확인하세요."
            ) from exc
        except httpx.ReadError as exc:
            raise ProviderError("LM Studio가 생성 중 연결을 종료했습니다. 로컬 서버 로그와 메모리 사용량을 확인하세요.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"LM Studio 연결 오류: {type(exc).__name__}: {exc}") from exc

    def _ollama_chat(self, cfg: ProviderConfig, model: str, system: str, prompt: str, max_tokens: int, temperature: float, *, json_mode: bool = False) -> str:
        """Use Ollama's native API so thinking and output limits are deterministic."""
        url = self._ollama_native_url(cfg.base_url, "/api/chat")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            # Keep the selected model warm for the staged workflow, but release
            # its RAM/VRAM sooner after an idle job. Set this to "0" when
            # immediate unloading is more important than speed.
            "keep_alive": os.getenv("AI_COURSE_STUDIO_OLLAMA_KEEP_ALIVE", "5m"),
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            body["format"] = "json"
        timeout = httpx.Timeout(connect=8.0, read=cfg.timeout, write=60.0, pool=10.0)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers={"Content-Type": "application/json"}, json=body)
            self._raise(response, "Ollama")
            data = response.json()
            message = data.get("message", {}) if isinstance(data, dict) else {}
            text = message.get("content", "") if isinstance(message, dict) else ""
            if isinstance(text, str) and text.strip():
                return text.strip()
            reason = str(data.get("done_reason") or "") if isinstance(data, dict) else ""
            raise ProviderError(
                f"Ollama가 '{model}'에서 본문 없는 응답을 반환했습니다"
                f"{f' (종료 사유: {reason})' if reason else ''}. 자동 연결로 권장 모델을 다시 선택하세요."
            )
        except httpx.ConnectTimeout as exc:
            raise ProviderError(
                f"Ollama 서버에 8초 안에 연결하지 못했습니다. 서버가 실행 중인지, Base URL({cfg.base_url})과 포트를 확인하세요."
            ) from exc
        except httpx.ConnectError as exc:
            raise ProviderError(
                f"Ollama 서버에 연결할 수 없습니다. 서버 실행 여부와 Base URL({cfg.base_url})을 확인하세요."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise ProviderError(
                "Ollama 모델이 제한 시간 안에 생성을 끝내지 못했습니다. 자동 연결로 더 빠른 권장 모델을 선택하세요."
            ) from exc
        except httpx.ReadError as exc:
            raise ProviderError(
                f"Ollama가 '{model}' 생성 중 연결을 강제로 종료했습니다. "
                "RAM/VRAM 부족으로 모델 프로세스가 재시작되었을 가능성이 큽니다. Ollama 자동 연결로 더 가벼운 모델을 선택하세요."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama 연결 오류: {type(exc).__name__}: {exc}") from exc

    @staticmethod
    def _compatible_text(data: dict[str, Any]) -> str:
        """Accept OpenAI-compatible response variants used by LM Studio/Ollama."""
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        candidates = [message.get("content"), message.get("text"), choice.get("text"), data.get("response")]
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                parts = []
                for part in value:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
                if any(x.strip() for x in parts):
                    return "\n".join(parts).strip()
        return ""

    @staticmethod
    def _raise(r: httpx.Response, label: str) -> None:
        if r.is_success:
            return
        detail = ""
        try:
            data = r.json()
            detail = data.get("error", data)
            if isinstance(detail, dict):
                detail = detail.get("message", json.dumps(detail, ensure_ascii=False))
        except Exception:
            detail = str(getattr(r, "text", ""))[:500]
        raise ProviderError(f"{label} API 오류 ({r.status_code}): {detail}")


def _json_candidates(text: str) -> list[str]:
    cleaned = text.strip().lstrip("\ufeff")
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        outer = cleaned[start:end + 1]
        if outer != cleaned:
            candidates.append(outer)
    return candidates


def _conservative_json_repair(text: str) -> str:
    """Repair only common local-LLM JSON punctuation mistakes.

    This intentionally avoids aggressive rewriting. It handles trailing commas,
    missing commas between line-separated members/items, and raw control chars.
    """
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove ASCII control characters that are invalid inside JSON text.
    s = "".join(ch for ch in s if ch in "\n\t" or ord(ch) >= 32)
    # Remove trailing commas before a closing brace/bracket.
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Insert a comma when one complete JSON value/member is followed on the next
    # line by another member/item and the model forgot the delimiter.
    patterns = [
        (r'("(?:[^"\\]|\\.)*")\s*\n\s*(")', r'\1,\n\2'),
        (r'([}\]])\s*\n\s*(")', r'\1,\n\2'),
        (r'([}\]])\s*\n\s*([\[{])', r'\1,\n\2'),
        (r'(true|false|null|-?\d+(?:\.\d+)?)\s*\n\s*(")', r'\1,\n\2'),
    ]
    for pat, repl in patterns:
        s = re.sub(pat, repl, s)
    return s


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort parser for local-LLM structured output.

    Order: exact JSON -> outer object -> conservative punctuation repair ->
    optional json_repair package (when installed). Never leak JSONDecodeError;
    callers always receive ProviderError on unrecoverable malformed output.
    """
    errors: list[str] = []
    for candidate in _json_candidates(text):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as e:
            errors.append(f"exact:{e.msg}@{e.lineno}:{e.colno}")

        repaired = _conservative_json_repair(candidate)
        try:
            data = json.loads(repaired)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as e:
            errors.append(f"repair:{e.msg}@{e.lineno}:{e.colno}")

        try:
            from json_repair import repair_json  # optional dependency
            repaired2 = repair_json(candidate, return_objects=True)
            if isinstance(repaired2, dict):
                return repaired2
        except Exception as e:
            errors.append(f"json_repair:{type(e).__name__}")

    hint = "; ".join(errors[-3:])
    raise ProviderError(f"AI 응답의 구조화 형식을 복구하지 못했습니다. ({hint})")
