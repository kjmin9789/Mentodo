const icon=(name,className="")=>`<svg class="montage-icon ${className}" aria-hidden="true" focusable="false" viewBox="0 0 24 24"><use href="assets/montage-icons.svg#${name}"></use></svg>`;
// 대화 수집은 별도 작업이며, 이 화면은 저장된 업무 데이터를 다시 읽습니다.
let tasks=[];
let profile;
try {
  const response=await fetch('./tasks.json',{cache:'no-store'});
  if(!response.ok)throw new Error('업무 데이터 불러오기 실패');
  tasks=await response.json();
  const profileResponse=await fetch('/api/profile',{cache:'no-store'});
  if(!profileResponse.ok)throw new Error('프로필 설정 불러오기 실패');
  profile=await profileResponse.json();
} catch(error) {
  document.querySelector('#tasks').textContent='개인 데이터나 프로필을 불러오지 못했습니다. python3 server.py --check로 파일을 확인한 뒤 새로고침해 주세요.';
  document.querySelector('#summary-heading').textContent='설정 파일을 확인해 주세요';
  throw error;
}
const categoryNames={mine:'내 할 일',requested:'요청한 일',question:'내가 한 질문',shared:'공유'};
const typeNames={design:'디자인',planning:'기획',review:'리뷰',marketing:'마케팅'};
let activeSource='all';
const sourceOf=t=>t.source||(['notion.com','app.notion.com','www.notion.so','notion.so'].includes(new URL(t.url).hostname)?'notion':'discord');
const sourceNames={discord:'Discord',notion:'Notion'};
let activeProject='all';
let activeType='all';
let activeCategory='all';
let activeDate='all';
let overrides={};
let stateReady=false;
let canEdit=true;
let stateRevision=-1;
let saving=false;
let refreshing=false;
let stateErrorShown=false;
let activeTab='todo';
let toastTimer;
const statusOf = t => overrides[t.id] || t.initial;
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scopedTasks=()=>tasks.filter(t=>(activeSource==='all'||sourceOf(t)===activeSource)&&(activeProject==='all'||t.project===activeProject)&&(activeType==='all'||t.type===activeType)&&(activeDate==='all'||t.date===activeDate)&&(activeCategory==='all'||t.category===activeCategory));
function counts(){ return scopedTasks().reduce((acc,t)=>{acc[statusOf(t)]++;return acc;},{todo:0,done:0,reference:0}); }
function render(){
  const expanded=[...document.querySelectorAll('details.task[open]')].map(n=>n.dataset.id);
  document.querySelectorAll('[data-type]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.type===activeType)));
  document.querySelectorAll('[data-source]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.source===activeSource)));
  const count=counts();
  document.querySelector('#nav-count').textContent=tasks.filter(t=>statusOf(t)==='todo').length;
  document.querySelector('#total-count').textContent=scopedTasks().length;
  document.querySelector('#summary-context').textContent=profile.isExample?'예시 데이터입니다. 개인 데이터를 설정하면 내 업무가 표시됩니다.':activeDate==='all'?'등록한 대화와 후속 처리 결과를 함께 관리합니다.':`${activeDate}에 작성된 대화를 보고 있습니다.`;
  for(const id of ['shared-count','shared-tab-count'])document.getElementById(id).textContent=count.reference;
  document.querySelector('#summary-heading').textContent=count.todo ? `진행 중인 일이 ${count.todo}건 있습니다` : '진행 중인 일이 없습니다';
  document.querySelector('#summary-count').textContent=String(count.todo).padStart(2,'0');
  for(const id of ['done-count','done-tab-count']) document.getElementById(id).textContent=count.done;
  document.querySelector('#todo-tab-count').textContent=count.todo;
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===activeTab)));
  document.querySelector('#list-heading').textContent={todo:'지금 확인해 주세요',done:'해결한 내용을 모았습니다',reference:'받거나 보낸 공유 내용을 모았습니다'}[activeTab];
  const visible=scopedTasks().filter(t=>statusOf(t)===activeTab);
  document.querySelector('#tasks').innerHTML=visible.length ? visible.map(t=>{
    const status=statusOf(t), cls=status==='todo'?'':status;
    const label=status==='done'?'완료':t.kind==='review'?(t.pr?'PR 리뷰':'리뷰 요청'):t.kind==='reference'?'공유':t.category==='requested'?'진행 확인':t.category==='question'?'답변 확인':'확인 요청';
    return `<details class="task" data-id="${t.id}"><summary><span class="task-type ${cls}" aria-hidden="true">${icon(t.type==='review'?'document-search':t.category==='shared'?'share':t.category==='requested'?'send':t.category==='question'?'circle-question':'list')}</span><div class="task-info"><div class="task-meta"><span class="type-badge ${cls}">${label}</span><span>${categoryNames[t.category]}</span><span>·</span><span>${sourceNames[sourceOf(t)]} · ${escape(t.channel)}</span><span>·</span><span>${t.sender.split(" → ").map(escape).join(icon("arrow-right","sender-arrow"))}</span></div><h2>${escape(t.title)}</h2><div class="task-caption"><span class="task-project">${escape(t.project)}</span><span class="task-work-type">${typeNames[t.type]}</span><span>${escape(t.caption)}</span></div></div><time class="task-time" datetime="${t.date}T${t.time}:00">${t.date.slice(5).replace("-","/")} ${t.time}</time>${icon("chevron-down","chevron")}</summary><div class="task-body"><div class="context-label">멘션 원문</div><div class="quote"><strong>${escape(t.author)}</strong>${escape(t.quote)}</div><div class="context-note">${icon("arrow-turn-down-right","context-arrow")}<div>${escape(t.note)}</div></div>${t.links?.length?`<div class="evidence-links" aria-label="본문 링크">${t.links.map(e=>`<a href="${escape(e.url)}" target="_blank" rel="noopener noreferrer">${escape(e.label)} ${icon("arrow-up-right")}</a>`).join('')}</div>`:''}${t.evidence?.length?`<div class="evidence-links">${t.evidence.map(e=>`<a href="${escape(e.url)}" target="_blank" rel="noopener noreferrer">${escape(e.label)} ${icon("arrow-up-right")}</a>`).join('')}</div>`:''}<div class="task-actions">${status!=='reference'&&canEdit?`<button ${saving||!stateReady?'disabled':''} class="complete-button ${status==='done'?'restore':''}" data-action="${status==='done'?'restore':'complete'}" data-id="${t.id}">${icon(status==='done'?'arrow-turn-down-left':'check')}${status==='done'?'할 일로 되돌리기':'완료 처리'}</button>`:''}${t.pr?`<a class="origin-link" href="${escape(t.pr)}" target="_blank" rel="noopener noreferrer">PR #${escape(t.pr.split("/").pop())} 열기 ${icon("arrow-up-right")}</a>`:''}<a class="origin-link secondary-link" href="${escape(t.url)}" target="_blank" rel="noopener noreferrer">${sourceNames[sourceOf(t)]} 원문 ${icon("arrow-up-right")}</a></div></div></details>`;
  }).join('') : `<div class="empty"><h2>이 조건에 해당하는 ${activeTab==='todo'?'진행 중인 일':activeTab==='done'?'완료한 일':'공유 내용'}이 없습니다</h2><p>프로젝트, 종류, 기간 또는 분류를 바꾸어 다른 항목을 확인할 수 있습니다.</p>${activeTab==='todo'?'<button data-show-done>완료한 일 보기</button>':''}</div>`;
  expanded.forEach(id=>{const item=document.querySelector(`details[data-id="${id}"]`);if(item)item.open=true;});
  if(!stateReady)document.querySelector('#summary-heading').textContent='저장 상태를 확인할 수 없습니다';
}
function showToast(message,undo){
  const toast=document.querySelector('#toast');
  clearTimeout(toastTimer);
  toast.hidden=false;
  toast.replaceChildren(document.createTextNode(message));
  if(undo){const button=document.createElement('button');button.textContent='실행 취소';button.onclick=undo;toast.append(button);}
  toastTimer=setTimeout(()=>{toast.hidden=true;},7000);
}
async function refreshState(){
  if(saving||refreshing)return;
  refreshing=true;
  try{
    const response=await fetch('/api/state',{cache:'no-store'});
    if(!response.ok)throw new Error('State unavailable');
    const state=await response.json();
    if(!state.statuses||typeof state.statuses!=='object'||!Number.isInteger(state.revision))throw new Error('Invalid state');
    if(!saving&&state.revision>=stateRevision){
      const changed=!stateReady||canEdit!==(state.canEdit!==false)||JSON.stringify(overrides)!==JSON.stringify(state.statuses);
      canEdit=state.canEdit!==false;
      overrides=state.statuses;stateRevision=state.revision;stateReady=true;
      if(changed)render();
    }
    stateErrorShown=false;
  }catch{
    if(!stateErrorShown)showToast('저장 상태를 불러오지 못했습니다. 로컬 서버 연결을 확인해 주세요.');
    stateErrorShown=true;
  }finally{refreshing=false;}
}
async function changeStatus(id,status,offerUndo=true){
  if(saving||!stateReady||!canEdit)return;
  const previous=statusOf(tasks.find(t=>t.id===id));
  saving=true;
  document.querySelectorAll('[data-action]').forEach(button=>{button.disabled=true;});
  try{
    const response=await fetch('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,status})});
    if(!response.ok)throw new Error('Save failed');
    const state=await response.json();
    overrides=state.statuses;stateRevision=state.revision;
    render();
    showToast(status==='done'?'완료한 일로 옮겼습니다.':'할 일로 되돌렸습니다.',offerUndo?()=>changeStatus(id,previous,false):null);
    document.querySelector('[data-tab][aria-selected="true"]').focus();
  }catch{
    showToast('저장하지 못했습니다. 상태는 변경하지 않았습니다. 로컬 서버 연결을 확인해 주세요.');
  }finally{
    saving=false;
    document.querySelectorAll('[data-action]').forEach(button=>{button.disabled=!stateReady;});
  }
}
document.querySelector('.tabs').addEventListener('click',e=>{const tab=e.target.closest('[data-tab]');if(tab){activeTab=tab.dataset.tab;render();}});
document.querySelector('.tabs').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=['todo','done','reference'];let index=tabs.indexOf(activeTab);index=e.key==='Home'?0:e.key==='End'?2:(index+(e.key==='ArrowRight'?1:2))%3;activeTab=tabs[index];render();document.querySelector(`[data-tab="${activeTab}"]`).focus();});
document.querySelector('#tasks').addEventListener('click',e=>{const action=e.target.closest('[data-action]');if(action)changeStatus(action.dataset.id,action.dataset.action==='complete'?'done':'todo');if(e.target.closest('[data-show-done]')){activeTab='done';render();}});
document.querySelector('.source-group').addEventListener('click',e=>{const button=e.target.closest('[data-source]');if(button){activeSource=button.dataset.source;render();}});
document.querySelector('#today-nav').onclick=()=>{activeTab='todo';activeSource='all';activeCategory='all';activeDate='all';activeProject='all';activeType='all';document.querySelector('#project-filter').value='all';document.querySelector('#category-filter').value='all';document.querySelector('#date-filter').value='all';render();};
document.querySelector('#category-filter').onchange=e=>{activeCategory=e.target.value;if(activeCategory==='shared')activeTab='reference';else if(activeTab==='reference'&&activeCategory!=='all')activeTab='todo';render();};
document.querySelector('#date-filter').onchange=e=>{activeDate=e.target.value;render();};
document.querySelector('#workspace-title').textContent=`${profile.name}님의 업무함`;
document.querySelector('#profile-name').textContent=profile.name;
document.querySelector('#profile-role').textContent=profile.role;
document.querySelectorAll('.profile-photo').forEach(image=>{image.src=profile.avatar;image.alt=`${profile.name} 프로필 사진`;});
document.querySelector('.source-note').textContent=profile.isExample?'예시 데이터':'로컬 데이터';
document.querySelector('.eyebrow').textContent=new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',weekday:'long'}).format(new Date());
function rebuildFilters(){
  for(const [selector,values,allLabel,selected] of [
    ['#project-filter',[...new Set(tasks.map(task=>task.project))],'전체 프로젝트',activeProject],
    ['#date-filter',[...new Set(tasks.map(task=>task.date))].sort().reverse(),'전체 기간',activeDate]
  ]){
    const select=document.querySelector(selector);
    select.replaceChildren(new Option(allLabel,'all'),...values.map(value=>new Option(value,value)));
    select.value=values.includes(selected)?selected:'all';
    if(selector==='#project-filter')activeProject=select.value;else activeDate=select.value;
  }
}
rebuildFilters();
document.querySelector('#project-filter').onchange=e=>{activeProject=e.target.value;render();};
let refreshingTasks=false;
async function refreshTasks(){
  if(refreshingTasks)return;
  refreshingTasks=true;
  try{
    const response=await fetch('./tasks.json',{cache:'no-store'});
    if(!response.ok)throw new Error('Task refresh failed');
    const next=await response.json();
    if(Array.isArray(next)&&JSON.stringify(next)!==JSON.stringify(tasks)){
      tasks=next;rebuildFilters();render();
    }
  }catch{ /* 다음 확인 때 재시도하고, 표시 중인 데이터는 유지합니다. */ }
  finally{refreshingTasks=false;}
}
window.addEventListener('focus',()=>refreshTasks());
setInterval(()=>{if(!document.hidden)refreshTasks();},60000);
document.querySelector('.type-filters').addEventListener('click',e=>{const button=e.target.closest('[data-type]');if(button){activeType=button.dataset.type;render();}});
await refreshState();
render();
window.addEventListener('focus',()=>refreshState());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshState();});
// 브라우저 간 완료 상태만 확인합니다. 새 대화·멘션 수집 주기와는 별개입니다.
setInterval(()=>{if(!document.hidden)refreshState();},5000);


const updateButton=document.querySelector('#update-button');
let updatePolling=false,updateSubmitting=false,lastUpdateResult='';
async function refreshUpdate(){
  if(updatePolling)return;
  updatePolling=true;
  try{
    const response=await fetch('/api/update',{cache:'no-store'});
    if(!response.ok)throw new Error('Update status unavailable');
    const state=await response.json();
    updateButton.hidden=!canEdit;
    updateButton.disabled=updateSubmitting||state.status==='running';
    updateButton.textContent=state.status==='running'?'업데이트 중…':'업데이트';
    updateButton.setAttribute('aria-busy',String(state.status==='running'));
    const result=JSON.stringify(state);
    if(state.status==='done'&&result!==lastUpdateResult){
      await Promise.all([refreshTasks(),refreshState()]);
      showToast('업무 수집을 완료했습니다. 최신 목록을 반영했습니다.');
    }else if(state.status==='error'&&result!==lastUpdateResult){showToast(state.error);}
    lastUpdateResult=result;
  }catch{ /* 다음 상태 확인에서 재시도합니다. */ }
  finally{updatePolling=false;}
}
updateButton.onclick=async()=>{
  if(updateSubmitting)return;
  updateSubmitting=true;updateButton.disabled=true;updateButton.textContent='업데이트 중…';
  try{
    const response=await fetch('/api/update',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const state=await response.json();
    if(!response.ok)throw new Error(state.error||'수집을 시작하지 못했습니다.');
    showToast('새 대화·멘션과 미완료 항목을 확인합니다.');
  }catch(error){showToast(error.message);}
  finally{updateSubmitting=false;updateButton.disabled=false;updateButton.textContent='업데이트';await refreshUpdate();}
};
await refreshUpdate();
window.addEventListener('focus',()=>refreshUpdate());
setInterval(()=>{if(!document.hidden)refreshUpdate();},3000);
