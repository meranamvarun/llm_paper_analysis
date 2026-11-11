import json,sys,hashlib,math
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageDraw,ImageFont
r=Path('data/text_quality/20261111'); source=Path('question_paper (1).pdf');pdf=pdfium.PdfDocument(str(source))
qs={q['question_id']:q for q in map(json.loads,(r/'screening/questions.jsonl').read_text(encoding='utf8').splitlines())}
pages={p['pdf_page']:p for p in map(json.loads,Path('data/extraction/runs/20261110T043421397159Z/pages.jsonl').read_text(encoding='utf8').splitlines())}
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
for folder in sorted(r.glob('luna_*')):
 flags=[json.loads(l) for l in (folder/'input.jsonl').read_text(encoding='utf8').splitlines()]; groups={};unmapped=[]
 for f in flags:
  q=qs[f['record_id']];full=f['full_field_text'];base=q['raw_text'].find(full);target=base+f['start'] if base>=0 else -1
  cursor=0;anchor=None
  for e in q['evidence']:
   line=next((l for l in pages[e['pdf_page']]['lines'] if l['line_id']==e['line_id']),None)
   if line is None:continue
   if cursor<=target<cursor+len(line['text'])+1:anchor=(e['pdf_page'],e['line_id']);break
   cursor+=len(line['text'])+1
  if anchor is None:
   # Exact token/context fallback within evidence; never invent source match.
   matches=[]
   for e in q['evidence']:
    line=next((l for l in pages[e['pdf_page']]['lines'] if l['line_id']==e['line_id']),None)
    if line and f['text'] in line['text']:matches.append((e['pdf_page'],e['line_id']))
   if len(matches)==1:anchor=matches[0]
  if anchor is None:unmapped.append(f['flag_id']);continue
  groups.setdefault(anchor,[]).append(f)
 crops=[];mapping=[]
 cache={}
 for (p,lineid),fs in sorted(groups.items()):
  if p not in cache:
   obj=pdf[p-1];cache[p]=obj.render(scale=1.8).to_pil().convert('RGB');obj.close()
  lines=pages[p]['lines'];idx=next(i for i,l in enumerate(lines) if l['line_id']==lineid)
  y0=max(0,min(l['bbox'][1] for l in lines[max(0,idx-1):idx+2])-3);y1=max(l['bbox'][3] for l in lines[max(0,idx-1):idx+2])+3
  im=cache[p].crop((0,int(y0*1.8),cache[p].width,min(cache[p].height,int(y1*1.8))))
  im.thumbnail((1100,300)); canvas=Image.new('RGB',(1120,im.height+66),'white');d=ImageDraw.Draw(canvas)
  ids=','.join(f['flag_id'] for f in fs);d.text((8,3),f'PDF {p} {lineid}  {ids[:105]}',font=font,fill='black')
  label=' | '.join(f['text'] for f in fs);d.text((8,27),label[:110],font=font,fill='black');canvas.paste(im,(10,60));crops.append(canvas)
  mapping.append({'pdf_page':p,'line_id':lineid,'flag_ids':[f['flag_id'] for f in fs],'source_mapping':'raw_text_offset_or_unique_token','crop_index':len(crops)-1})
 sheetdir=folder/'flag_crops';sheetdir.mkdir(exist_ok=False);sheets=[]
 for start in range(0,len(crops),8):
  batch=crops[start:start+8];height=sum(c.height for c in batch)+10*(len(batch)+1);sheet=Image.new('RGB',(1140,height),'#dddddd');y=10
  for c in batch:sheet.paste(c,(10,y));y+=c.height+10
  path=sheetdir/f'sheet_{start//8+1:03d}.jpg';sheet.save(path,quality=90);sheets.append(str(path))
  for m in mapping[start:start+8]:m['sheet_path']=str(path)
 (folder/'crop_mapping.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mapping':mapping,'unmapped_flags':unmapped,'sheet_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sheetdir.iterdir()}},indent=2),encoding='utf8')
 print(folder.name,len(groups),'line crops',len(sheets),'sheets',len(unmapped),'unmapped')
pdf.close()
