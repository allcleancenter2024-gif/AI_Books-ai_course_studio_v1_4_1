import {api, post} from './api.js';

const $ = id => document.getElementById(id);

/** Owns the login gate and server-backed browser session lifecycle. */
export function initSessionAccess(onStudioReady) {
  let studioStarted = false;
  function startStudio(accessName = '로컬 사용자') {
    if (studioStarted) return;
    studioStarted = true;
    const gate = $('loginGate'), app = $('studioApp'), nameLabel = $('sessionUserName');
    if (nameLabel) nameLabel.textContent = accessName;
    app.hidden = false;
    gate.classList.add('is-leaving');
    window.setTimeout(() => gate.remove(), 300);
    onStudioReady();
  }
  $('logoutButton')?.addEventListener('click', async () => {
    if (!window.confirm('이 PC의 Studio 접속을 종료할까요?')) return;
    try { await post('/api/auth/logout', {}); } catch (_) {}
    window.location.reload();
  });
  const form = $('loginForm'), name = $('loginName'), password = $('loginPassword');
  const remember = $('loginRemember'), error = $('loginError'), toggle = $('passwordToggle');
  toggle.addEventListener('click', () => {
    const visible = password.type === 'text';
    password.type = visible ? 'password' : 'text';
    toggle.textContent = visible ? '표시' : '숨김';
    toggle.setAttribute('aria-label', visible ? '접속 암호 표시' : '접속 암호 숨김');
    toggle.setAttribute('aria-pressed', String(!visible));
    password.focus();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const username = name.value.trim();
    if (!username) { error.textContent = '이름 또는 이메일을 입력하세요.'; name.focus(); return; }
    if (!password.value) { error.textContent = '접속 암호를 입력하세요.'; password.focus(); return; }
    error.textContent = '';
    const submit = form.querySelector('[type=submit]');
    submit.disabled = true; submit.textContent = '접속 확인 중…';
    try {
      const result = await post('/api/auth/login', {username, password: password.value, remember: remember.checked});
      password.value = '';
      startStudio(result.user.username);
    } catch (reason) {
      error.textContent = reason.message;
      password.focus();
    } finally {
      submit.disabled = false;
      submit.innerHTML = 'Studio 시작하기 <span aria-hidden="true">→</span>';
    }
  });
  api('/api/auth/session').then(result => startStudio(result.user.username)).catch(() => name.focus());
}
