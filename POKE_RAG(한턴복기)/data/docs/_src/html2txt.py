import re,html,sys
s=open(sys.argv[1],encoding="utf-8").read()
m=re.search(r'<div id="mw-content-text".*',s,re.S); b=m.group(0) if m else s
b=re.sub(r'<(script|style)[^>]*>.*?</\1>','',b,flags=re.S)
b=re.sub(r'<h([1-6])[^>]*>',lambda x:'\n\n'+'#'*int(x.group(1))+' ',b)
b=re.sub(r'</(p|tr|li|div|h\d)>','\n',b); b=re.sub(r'<br\s*/?>','\n',b)
b=re.sub(r'<[^>]+>','',b); b=html.unescape(b)
b=b.replace('[edit]','');b=re.sub(r'[ \t]+',' ',b); b=re.sub(r'\n\s*\n+','\n\n',b)
open(sys.argv[2],"w",encoding="utf-8").write(b); print(len(b))
