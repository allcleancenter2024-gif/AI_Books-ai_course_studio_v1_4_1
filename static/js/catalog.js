import {api, post, esc} from './api.js';

const $ = id => document.getElementById(id);

export async function loadProducts() {
  const data = await api('/api/products');
  $('products').innerHTML = `<div class="table-wrap"><table><thead><tr><th>제품</th><th>현재 정보</th><th>기준일</th><th>변경 상태</th><th>공식 확인일</th><th>공식 웹페이지</th></tr></thead><tbody>${data.map(item => { const changed = Boolean(item.has_changes), label = changed ? '변경 사항 있음' : '변경 사항 없음'; return `<tr><td><b>${esc(item.current_name)}</b><br><span class="small">${esc(item.company)}</span></td><td>${esc(item.current_version)}<br><span class="small">${esc(item.features)}</span></td><td>${esc(item.release_date)}</td><td><span class="change-state"><i class="change-dot ${changed ? 'changed' : 'unchanged'}" aria-hidden="true"></i>${label}</span><br><span class="small">${esc(item.change_note)}</span></td><td>${esc(item.checked_date)} · ${esc(item.source_level)}</td><td><a class="official-link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">공식 웹페이지 열기 ↗</a></td></tr>`; }).join('')}</tbody></table></div>`;
}

function changesMarkdown(rows) {
  const lines = ['# 주요한 정보변경사항', '', `- 생성일: ${new Date().toISOString().slice(0, 10)}`, '', '| 제품명 | 기준일 정보 | 변경된 정보 | 참고해야 하는 중요사항 |', '| --- | --- | --- | --- |'];
  for (const item of rows) lines.push(`| ${item.current_name} | ${item.baseline_info} | ${item.changed_info} | ${item.important_notes} |`);
  return lines.join('\n');
}

function downloadChangesMarkdown(rows) {
  const blob = new Blob([changesMarkdown(rows)], {type: 'text/markdown;charset=utf-8'}), url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = 'major_information_changes.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export async function loadChanges() {
  const [rows, books] = await Promise.all([api('/api/products/changes'), api('/api/books')]);
  const majorCount = rows.filter(item => item.is_major).length;
  const bookOptions = books.length ? books.map(book => `<option value="${book.id}">#${book.id} · ${esc(book.weeks)}주 · ${esc(book.audience)} · ${esc(String(book.created_at || '').slice(0, 16))}</option>`).join('') : '<option value="">저장된 교재가 없습니다</option>';
  $('changesList').innerHTML = rows.length ? `<div class="changes-dashboard-head"><div><span class="changes-dashboard-kicker">CHANGE REVIEW</span><h3>수업 반영 전 변화 요약</h3><p>기준일 정보와 현재 확인 정보를 나란히 비교하세요.</p></div><div class="changes-dashboard-stats"><span><b>${rows.length}</b>개 변경</span>${majorCount ? `<span class="major"><b>${majorCount}</b>개 큰 변화</span>` : ''}</div></div><div class="changes-book-target"><label for="changesBookSelect">반영할 교재</label><select id="changesBookSelect" ${books.length ? '' : 'disabled'}>${bookOptions}</select><button id="changesBookRepair" class="secondary" type="button" ${books.length ? '' : 'disabled'}>교재 구조 복구</button><span id="changesBookRepairOut">${books.length ? '카드의 추가 버튼으로 변경사항을 반영하거나, 구조 복구로 깨진 생성 항목을 안전하게 정리할 수 있습니다.' : '먼저 전체·구간 교재 또는 1주 교재를 생성하세요.'}</span></div><div class="changes-dashboard-grid">${rows.map(item => `<article class="change-dashboard-card ${item.is_major ? 'is-major' : ''}"><div class="change-card-head"><div>${item.is_major ? '<span class="change-major-check" title="수업 내용에 큰 영향을 주는 변화" aria-label="큰 변화">✓</span>' : ''}<div><h4>${esc(item.current_name)}</h4><span>기준일 ${esc(item.release_date)} · 변경일 ${esc(item.changed_date || item.checked_date)}</span></div></div><span class="change-status-label">${item.is_major ? '큰 변화' : '정보 갱신'}</span></div><div class="change-compare"><div class="change-compare-box before"><span>이전 기준</span><p>${esc(item.baseline_info)}</p></div><span class="change-arrow" aria-hidden="true">→</span><div class="change-compare-box after"><span>변경 후</span><p>${esc(item.changed_info)}</p></div></div><div class="change-card-note"><b>수업 반영 전 확인</b><p>${esc(item.important_notes)}</p></div><div class="change-card-actions"><div class="change-add-control"><button class="change-add-button" type="button" data-change-add="${esc(item.product_name)}" ${books.length ? '' : 'disabled'}>교재에 추가</button><span class="change-add-status" aria-live="polite"></span></div><a class="official-link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">공식 웹페이지 확인 ↗</a></div><div class="change-apply-out" aria-live="polite"></div></article>`).join('')}</div>` : '<div class="notice">기준일 이후 표시할 주요 변경사항이 없습니다.</div>';
  $('changesDownload').disabled = !rows.length;
  $('changesDownload').onclick = () => downloadChangesMarkdown(rows);
  const toggle = $('changesToggle'), dashboard = $('changesDashboard');
  toggle.disabled = !rows.length;
  toggle.onclick = () => { const show = dashboard.hidden; dashboard.hidden = !show; toggle.setAttribute('aria-expanded', String(show)); toggle.textContent = show ? '변경사항 숨기기' : '변경사항 보기'; };
  $('changesBookRepair').onclick = async () => { const bookId = $('changesBookSelect').value, out = $('changesBookRepairOut'); if (!bookId) return; try { out.textContent = '교재 구조를 검사하고 복구하는 중입니다...'; const result = await post(`/api/books/${bookId}/repair`, {}); out.innerHTML = result.repaired_weeks ? `구조 복구 완료: ${result.repaired_weeks}개 주차를 정리했습니다. <a href="${esc(result.view_url)}" target="_blank" rel="noopener noreferrer">교재 보기 ↗</a>` : '구조 검사 완료: 복구할 항목이 없습니다.'; } catch (error) { out.textContent = `구조 복구 실패: ${error.message}`; } };
  document.querySelectorAll('[data-change-add]').forEach(button => button.addEventListener('click', async () => {
    const bookId = $('changesBookSelect').value, card = button.closest('.change-dashboard-card'), output = card.querySelector('.change-apply-out'), status = card.querySelector('.change-add-status');
    if (!bookId) return;
    button.disabled = true; status.textContent = '반영 중'; status.className = 'change-add-status working'; output.textContent = '선택한 교재의 Markdown 파일과 저장 기록을 갱신하는 중입니다...'; output.className = 'change-apply-out';
    try { const result = await post(`/api/books/${bookId}/changes/${encodeURIComponent(button.dataset.changeAdd)}`, {}); status.innerHTML = '<i aria-hidden="true">✓</i> 성공'; status.className = 'change-add-status success'; output.innerHTML = `${esc(result.message)} <a href="${esc(result.view_url)}" target="_blank" rel="noopener noreferrer">갱신된 교재 보기 ↗</a>`; output.className = 'change-apply-out success'; }
    catch (error) { const unavailable = error.message === 'Not Found'; const help = unavailable ? '서버가 최신 교재 반영 API를 아직 적용하지 않았습니다. Studio를 완전히 종료한 뒤 다시 실행하고, 이 버튼을 다시 누르세요.' : `반영하지 못했습니다: ${error.message} 선택한 교재 파일이 삭제·이동되지 않았는지 확인한 뒤 다시 시도하세요.`; status.innerHTML = '<i aria-hidden="true">✕</i> 실패'; status.className = 'change-add-status error'; output.textContent = help; output.className = 'change-apply-out error'; }
    finally { button.disabled = false; }
  }));
}
