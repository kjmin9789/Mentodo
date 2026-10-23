export const dayKey=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
export const asDate=key=>new Date(`${key}T12:00:00`);
export function datePresets(today=new Date()){
  const y=today.getFullYear(),m=today.getMonth(),d=today.getDate();
  const monday=new Date(y,m,d-(today.getDay()+6)%7,12);
  return {
    today:[dayKey(today),dayKey(today)],
    week:[dayKey(monday),dayKey(new Date(monday.getFullYear(),monday.getMonth(),monday.getDate()+6,12))],
    month:[dayKey(new Date(y,m,1,12)),dayKey(new Date(y,m+1,0,12))]
  };
}
export function dateBounds(today=new Date()){
  const y=today.getFullYear(),m=today.getMonth(),d=today.getDate();
  const earliest=new Date(y,m-2,Math.min(d,new Date(y,m-1,0).getDate())+1,12);
  const presets=datePresets(today);
  return {min:dayKey(earliest),max:[presets.week[1],presets.month[1]].sort().at(-1)};
}
