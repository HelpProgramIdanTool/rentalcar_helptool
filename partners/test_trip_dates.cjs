const {test}=require('node:test');
const assert=require('node:assert/strict');
const dates=require('./static/partners/trip-dates.js');

test('return calendar starts on collection date, across months and years',()=>{
 for(const [today,pickup] of [['20.11.2026','23.11.2026'],['30.11.2026','02.12.2026'],['31.12.2026','02.01.2027']]){
  assert.equal(dates.minimum(today,pickup,'10:00',true),dates.parse(pickup));
  assert.equal(dates.minimum(today,pickup,'10:00',false),dates.parse(today));
 }
});
test('last half-hour collection requires return on the next day',()=>{
 assert.equal(dates.minimum('20.11.2026','31.12.2026','23:30',true),dates.parse('01.01.2027'));
});
test('manual dates and same-day times must be ordered',()=>{
 assert.equal(dates.reversed('23.11.2026','10:00','20.11.2026','10:00'),true);
 assert.equal(dates.reversed('23.11.2026','10:00','23.11.2026','09:30'),true);
 assert.equal(dates.reversed('23.11.2026','10:00','23.11.2026','10:00'),true);
 assert.equal(dates.reversed('23.11.2026','10:00','23.11.2026','10:30'),false);
 assert.equal(dates.reversed('23.11.2026','23:30','24.11.2026','00:00'),false);
});
test('incomplete and impossible dates do not become valid calendar bounds',()=>{
 for(const value of ['','23.11.','31.02.2027','32.11.2026'])assert.equal(dates.parse(value),null);
 assert.equal(dates.minimum('20.11.2026','31.02.2027','10:00',true),dates.parse('20.11.2026'));
 assert.equal(dates.reversed('23.11.2026','10:00','','10:00'),false);
});
