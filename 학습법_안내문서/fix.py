import zipfile,re,sys
src,dst=sys.argv[1],sys.argv[2]
zi=zipfile.ZipFile(src); zo=zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED)
for i in zi.infolist():
    d=zi.read(i.filename)
    if i.filename=='word/fontTable.xml':
        d=re.sub(rb'w:fontKey="\{([^}]*)\}"',lambda m:b'w:fontKey="{'+m.group(1).upper()+b'}"',d)
    zo.writestr(i,d)
zo.close()
