import {test} from 'node:test';
import assert from 'node:assert/strict';
import {datePresets,dateBounds} from '../assets/date-range.js';
test('오늘과 월요일~일요일 주간 범위',()=>{
  assert.deepEqual(datePresets(new Date(2026,9,23)).today,['2026-10-23','2026-10-23']);
  assert.deepEqual(datePresets(new Date(2026,9,25)).week,['2026-10-19','2026-10-25']);
  assert.deepEqual(datePresets(new Date(2026,10,1)).week,['2026-10-26','2026-11-01']);
});
test('한 달은 28·29·30·31일과 연도 경계를 처리',()=>{
  for(const [year,month,last] of [[2026,1,28],[2024,1,29],[2026,3,30],[2026,11,31]]){
    const range=datePresets(new Date(year,month,15)).month;
    assert.equal(range[0],`${year}-${String(month+1).padStart(2,'0')}-01`);
    assert.equal(range[1],`${year}-${String(month+1).padStart(2,'0')}-${last}`);
  }
  assert.equal(dateBounds(new Date(2026,0,31)).min,'2025-12-01');
  assert.equal(dateBounds(new Date(2026,9,23)).min,'2026-08-24');
});
