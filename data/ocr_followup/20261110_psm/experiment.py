import hashlib,json,subprocess,os,sys
from pathlib import Path
import pypdfium2 as pdfium
sys.path.insert(0,str(Path.cwd()))
from extraction.run import ocr_page
root=Path('data/ocr_followup/20261110_psm')
source=Path('question_paper (1).pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan={'status':'exploratory_unreviewed','pages':[330,339,405,414],'dpi':300,'psms':[3,6,11], 'purpose':'Compare layout modes on known failures; do not replace baseline or select global defaults','source_sha256':sha(source),'baseline':'20261110T043421397159Z','reference':'AI source-image check only, no human ground truth'}
(root/'plan.json').write_text(json.dumps(plan,indent=2))
baseline=Path('data/extraction/runs')/plan['baseline']
before={p.name:sha(p) for p in baseline.iterdir() if p.is_file()}
results=[]
pdf=pdfium.PdfDocument(source)
for n in plan['pages']:
    page=pdf[n-1]
    im=root/f'page_{n:04d}.png'
    page.render(scale=300/72).to_pil().save(im)
    for psm in plan['psms']:
        result=ocr_page(n,im,r'C:\Program Files\Tesseract-OCR\tesseract.exe',300,{'pdf_page':n},root/f'page_{n:04d}_psm{psm}.json',psm)
        results.append({'pdf_page':n,'psm':psm,'words':len(result.get('ocr_words',[])),'lines':len(result['lines']),'issues':result['issues']})
        print(n,psm,len(result.get('ocr_words',[])),flush=True)
assert before=={p.name:sha(p) for p in baseline.iterdir() if p.is_file()}
assert plan['source_sha256']==sha(source)
(root/'results.json').write_text(json.dumps({'results':results,'baseline_unchanged':True,'source_unchanged':True},indent=2))
(root/'artifact_hashes.json').write_text(json.dumps({p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name!='artifact_hashes.json'},indent=2))
