"""Run from the repository root; front pages publish average prices, not dollar volume."""
import csv,json,re,hashlib
from pathlib import Path
import pymupdf
import argparse
parser = argparse.ArgumentParser(description="Independently compare district CSV totals with PDF front pages and page 3.")
parser.add_argument('csv', type=Path)
path = parser.parse_args().csv
rows=list(csv.DictReader(path.open()))
assert list(rows[0])==['ym','house_type','region','sales','dollar_volume','average_price','median_price','new_listings','snlr_trend','active_listings','moi_trend','avg_sp_lp','avg_ldom','avg_pdom','source_pdf','source_pdf_sha256']
report=[]
for r in rows:
 if r['house_type']!='all_types' or r['region']!='All TRREB Areas':continue
 pdf=Path('data/raw/trreb')/r['source_pdf'];assert hashlib.sha256(pdf.read_bytes()).hexdigest()==r['source_pdf_sha256']
 with pymupdf.open(pdf) as d:
  front=d[0];year=r['ym'][:4];blocks=front.get_text('blocks')
  header=next(b for b in blocks if b[4].strip()==year+'\n'+str(int(year)-1))
  current=next(w for w in front.get_text('words') if w[4]==year and abs(w[1]-header[1])<2)
  xc=(current[0]+current[2])/2
  vals={}
  for title in ['Sales','Average Price']:
   label=next(b for b in blocks if b[4].strip()==title and b[1]>header[1])
   words=[w for w in front.get_text('words') if abs(w[1]-label[1])<3 and abs((w[0]+w[2])/2-xc)<20 and re.fullmatch(r'\$?[\d,]+',w[4])]
   assert len(words)==1,(pdf,title,words)
   vals[title]=int(words[0][4].replace('$','').replace(',',''))
  assert vals['Sales']==int(r['sales']),(pdf,vals,r)
  assert vals['Average Price']==int(r['average_price']),(pdf,vals,r)
  page=d[2];label=page.search_for('All TRREB Areas')[0]
  text=page.get_text(clip=pymupdf.Rect(0,label.y0-1,page.rect.width,label.y1+1))
  dollars=re.findall(r'\$[\d,]+',text)
  assert int(dollars[0][1:].replace(',',''))==int(r['dollar_volume']),(pdf,dollars,r)
  assert abs(int(r['dollar_volume'])/int(r['sales'])-vals['Average Price'])<=0.500001
  report.append({'ym':r['ym'],'front_sales':vals['Sales'],'front_average_price':vals['Average Price'],'page3_dollar_volume':int(r['dollar_volume'])})
assert len(report)==len({r['ym'] for r in rows}), 'Missing all-types total for a month'
audit = Path('data/audit') / (path.stem + '-audit.json')
audit.parent.mkdir(parents=True, exist_ok=True)
audit.write_text(json.dumps({'csv':str(path),'rows':len(rows),'checks':report},indent=2))
print('PASS',len(rows),f'rows; all {len(report)} front-page sales and average prices match; exact dollar volumes match page 3')
print(report[0],report[-1])
