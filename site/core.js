// Small, testable study engine. Intervals are transparent heuristics, not FSRS.
export const VERSION = 'clat-studio-1';
export const DAY = 86400000;
export function dayKey(date = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);
}
export function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value+'T00:00:00Z');
  return !Number.isNaN(+d) && d.toISOString().slice(0,10) === value;
}
export function addDays(date, n) {
  if (!validDate(date) || !Number.isInteger(n)) throw new Error('Invalid calendar date');
  return new Date(Date.parse(date+'T00:00:00Z')+n*DAY).toISOString().slice(0,10);
}
export function daysBetween(start, end) {
  if (!validDate(start)||!validDate(end)) throw new Error('Invalid calendar date');
  return Math.round((Date.parse(end+'T00:00:00Z')-Date.parse(start+'T00:00:00Z'))/DAY);
}
export function newCardLimit(minutes, today, exam) {
  const left=daysBetween(today,exam);
  return left<=3 ? 0 : minutes<=90?4:minutes<=180?8:12;
}
export function freshState() {
  return {schema:1,contentVersion:VERSION,settings:{examDate:'2026-12-06',startDate:'2026-11-17',minutes:180},
    cards:{},attempts:[],repairs:{},notes:{},readTopics:[],doneTasks:{},quizResults:[],quizDraft:null};
}
export function rateCard(previous, rating, now=Date.now(), exam='2026-12-06') {
  if (!['again','hard','good','easy'].includes(rating)||!Number.isFinite(now)||!validDate(exam)) throw new Error('Invalid review');
  const today=dayKey(new Date(now)), p=previous||{};
  let interval;
  if (rating==='again') interval=0;
  else if(rating==='hard') interval=1;
  else if(rating==='easy') interval=Math.max(3,Math.ceil((p.interval||1)*2.5));
  else interval=p.interval>=7?Math.ceil(p.interval*2):p.interval>=3?7:p.interval>=1?3:1;
  let dueDate=addDays(today,interval), dueAt=now+interval*DAY;
  if(rating==='again') {dueAt=now+10*60000;dueDate=dayKey(new Date(dueAt));}
  else if(exam>today) {
    dueDate=dueDate>=exam?addDays(exam,-1):dueDate;
    // A successful final-day review should not create an endless ten-minute loop.
    dueAt=dueDate===today?Date.parse(today+'T23:59:59+05:30'):Date.parse(dueDate+'T00:00:00+05:30');
  }
  return {interval, dueDate, dueAt, introduced:p.introduced||today, lastReviewed:today,
    reviews:(p.reviews||0)+1,lapses:(p.lapses||0)+(rating==='again'?1:0),lastRating:rating};
}
export function cardQueue(cards, state, now=Date.now(), limit=null) {
  const today=dayKey(new Date(now));
  const max=limit??newCardLimit(state.settings.minutes,today,state.settings.examDate);
  const introduced=Object.values(state.cards).filter(c=>c.introduced===today).length;
  const due=cards.filter(c=>state.cards[c.id] && state.cards[c.id].dueAt<=now)
    .sort((a,b)=>state.cards[a.id].dueAt-state.cards[b.id].dueAt);
  const fresh=cards.filter(c=>!state.cards[c.id]).slice(0,Math.max(0,max-introduced));
  return [...due,...fresh];
}
export function scoreAnswers(questions, answers) {
  let correct=0,wrong=0,skipped=0;
  questions.forEach((q,i)=>{if(answers[i]===null||answers[i]===undefined)skipped++;else if(answers[i]===q.correctIndex)correct++;else wrong++;});
  return {correct,wrong,skipped,net:correct-.25*wrong};
}
export function shuffle(items, random=Math.random) {
  const a=[...items];for(let i=a.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;
}
export function weakTopics(modules, attempts) {
  const recent=attempts.slice(-100),counts={};
  for(const a of recent) {counts[a.topicId]??={n:0,wrong:0};counts[a.topicId].n++;counts[a.topicId].wrong+=a.correct?0:1;}
  return modules.filter(m=>counts[m.id]?.wrong).sort((a,b)=>(counts[b.id].wrong/counts[b.id].n)-(counts[a.id].wrong/counts[a.id].n)||counts[b.id].wrong-counts[a.id].wrong);
}
const isObject=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const string=(v,max=20000)=>typeof v==='string'&&v.length<=max;
const integer=(v,min=0,max=1e7)=>Number.isInteger(v)&&v>=min&&v<=max;
const timestamp=v=>Number.isFinite(v)&&v>=0&&v<=4102444800000;
export function validateState(s,catalog=null) {
  const fail=error=>({ok:false,error});
  if(!isObject(s)||s.schema!==1||s.contentVersion!==VERSION)return fail('This is not a compatible Study Studio backup.');
  if(!isObject(s.settings)||!validDate(s.settings.examDate)||!validDate(s.settings.startDate)||s.settings.examDate<=s.settings.startDate||!integer(s.settings.minutes,30,600))return fail('Check the plan dates and daily minutes.');
  for(const name of ['cards','repairs','notes','doneTasks'])if(!isObject(s[name])||Object.keys(s[name]).length>10000)return fail('Invalid '+name+' data.');
  if(!Array.isArray(s.attempts)||s.attempts.length>50000||!Array.isArray(s.readTopics)||s.readTopics.length>500||!Array.isArray(s.quizResults)||s.quizResults.length>5000)return fail('Invalid history.');
  for(const [id,c] of Object.entries(s.cards)) {
    if(!string(id,120)||!isObject(c)||!timestamp(c.dueAt)||!validDate(c.dueDate)||!validDate(c.introduced)||!validDate(c.lastReviewed)||!integer(c.interval,0,100000)||!integer(c.reviews)||!integer(c.lapses)||!['again','hard','good','easy'].includes(c.lastRating))return fail('Invalid card history.');
    if(catalog&&!catalog.cardIds.has(id))return fail('Unknown flashcard in backup.');
  }
  for(const a of s.attempts) {
    if(!isObject(a)||!string(a.id,120)||!string(a.questionId,120)||!string(a.topicId,80)||typeof a.correct!=='boolean'||!integer(a.choice,0,3)||!['low','medium','high'].includes(a.confidence)||!timestamp(a.at)||!string(a.reason,80))return fail('Invalid question history.');
    if(catalog&&!catalog.questionIds.has(a.questionId))return fail('Unknown question in backup.');
  }
  for(const [id,n] of Object.entries(s.notes))if(!string(id,80)||!string(n))return fail('Invalid topic note.');
  for(const [id,r] of Object.entries(s.repairs))if(!string(id,120)||!isObject(r)||!string(r.rule)||!string(r.reason,100)||typeof r.fixed!=='boolean')return fail('Invalid repair note.');
  if(s.readTopics.some(v=>!string(v,80)||(catalog&&!catalog.topicIds.has(v))))return fail('Unknown lesson in backup.');
  if(new Set(s.readTopics).size!==s.readTopics.length)return fail('Duplicate lesson records.');
  for(const [id,v] of Object.entries(s.doneTasks))if(!string(id,150)||typeof v!=='boolean')return fail('Invalid task history.');
  for(const r of s.quizResults)if(!isObject(r)||!string(r.id,120)||!string(r.title,200)||!timestamp(r.at)||!integer(r.correct)||!integer(r.wrong)||!integer(r.skipped)||!Number.isFinite(r.net)||r.net!==r.correct-.25*r.wrong)return fail('Invalid quiz results.');
  if(s.quizDraft!==null) {
    const q=s.quizDraft;
    if(!isObject(q)||!Array.isArray(q.ids)||!q.ids.length||q.ids.length>200||q.ids.some(id=>!string(id,120)||(catalog&&!catalog.questionIds.has(id)))||!Array.isArray(q.answers)||q.answers.length!==q.ids.length||q.answers.some(v=>v!==null&&!integer(v,0,3))||!Array.isArray(q.confidences)||q.confidences.length!==q.ids.length||q.confidences.some(v=>v!==null&&!['low','medium','high'].includes(v))||!Array.isArray(q.committed)||q.committed.length!==q.ids.length||q.committed.some(v=>typeof v!=='boolean')||!integer(q.index,0,Math.max(0,q.ids.length-1))||!Number.isFinite(q.deadline)||!string(q.title,200)||!string(q.id,120)||typeof q.simulation!=='boolean'||(q.passageId!==null&&!string(q.passageId,120)))return fail('Invalid in-progress quiz.');
  }
  return {ok:true};
}
export function planFor(date, settings, topicIds) {
  const total=daysBetween(settings.startDate,settings.examDate),index=daysBetween(settings.startDate,date),left=daysBetween(date,settings.examDate);
  if(index<0)return {phase:'Before your plan',focus:topicIds.slice(0,2),left,index,total};
  if(left<=0)return {phase:left===0?'Exam day':'Plan complete',focus:[],left,index,total};
  const fraction=index/Math.max(1,total-3);
  const phase=left<=3?'Consolidate':fraction<.55?'Build foundations':'Mix and repair';
  const focus=[topicIds[(index*2)%topicIds.length],topicIds[(index*2+1)%topicIds.length]].filter(Boolean);
  return {phase,focus,left,index,total};
}
