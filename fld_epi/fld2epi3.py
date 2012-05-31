# fld2epi3
# 2012.05.31
#
#
import sys,string,re

if len(sys.argv) != 2:
 print """
  usage: fld2epi3.py  FILE
 """
 sys.exit()



################################################################
def EXISTS(s):
 return( (len(s)>0) )

def CHKCMD(s):
 return( EXISTS(s) and (s[0:1]=='%') )

def QESTXT(s):
 result= False
 if EXISTS(s):
  mQ= re.search(r"^[%\?\$\!]", s)
  mF= re.search(r"^[a-z][a-z0-9]*\s+[Ccnd]\s+\d+\s+\d+\s", s, re.I)
  result= (mQ is None) and (mF is None)
 return( result )

def FLDDEF(s):
 result= False
 if EXISTS(s):
  if re.search(r"^[a-z][a-z0-9]*\s+[Ccnd]\s+\d+\s+\d+\s", s, re.I) is not None:
   result= True
 return( result )

def CLVCMD(s):
 result= False
 if EXISTS(s):
  if re.search(r"^[\?\$\!][^=]", s) is not None:
   result= True
 return( result )

def CLUCMD(s):
 result= False
 if EXISTS(s):
  if re.search(r"^\?=", s) is not None:
   result= True
 return( result )


################################################################
def make_de(t,w,n):	# make data entry field string given type,width & n.dec
 result= ""
 if t == 'c':
  result= '_'*w

 elif t == 'C':
  result= '<A' + '_'*(w-1) + '>'

 elif t == 'n' or t == 'N':
  result= '#' * w
  if 0 < n and n < w:	# insert decimal point (if possible)
   a= result[1:-n]
   b= result[-n:]
   result= a + "." + b

 elif t == 'd' or t == 'D':
   result= '<dd/mm/yyyy>'
 return(result)

################################################################
# make_pf -- make combined 'prompt and filler' string.
# Given a prompt string and a data entry field string,
# return a string combining prompt text and sufficient filler space to
# achieve correct right-alignment of the data entry field.
#
# (need to handle some pesky special cases)
#
def make_pf(fprompt, de_fld):
 LINESIZE= 80
 extras= ''
 if de_fld[:1] == "<": extras= ' '*2	# fields in angle brackets need more filler
 filler= ' '*(LINESIZE - (len(fprompt) + len(de_fld) + 10 + 1 + 1))
 if fprompt[:1] == "[" :
  result= filler + extras + fprompt	# right align prompt string when it starts with [
 else:
  result= fprompt + extras + filler
 return(result)


def do_qes(s, n):
 s= s.rstrip()
 global fromtop
 if re.search(r"^\[\]", line) is not None:	# we have a 'page-align' request
  fromtop= qnum	# save current QES line number (but we dont print the line itself)
 else:
  n += 1
  qes.write( "%10s %s\n" % (' ', s) )
 return( n )

def do_chk(s):
 s= s.rstrip()
 chk.write( "%s\n" % (s[1:]) )
 return()

def do_fld(s,n):
 global flist
 global fromtop
 s= s.rstrip()
 mF= re.search(r"^([a-z][a-z0-9]*)\s+([Ccnd])\s+(\d+)\s+(\d+)\s+(.*$)", s, re.I)
 if mF is not None:
  fname= mF.group(1)
  ftype= mF.group(2)
  fwidth=int(mF.group(3))
  fndec= int(mF.group(4))
  fprompt=mF.group(5)
  de_fld= make_de(ftype, fwidth, fndec)
  fprompt= make_pf(fprompt, de_fld)
  flist[fnum]= [fname, fprompt, de_fld]
  chk.write( "\n%s\n" % (fname) )
  if n == 1:
   chk.write( " key unique\n" )
 return()

def do_clv(s, n):
 s= s.rstrip()
 global vlist
 global jlist
 mV= re.search(r"^([\?\$\!])(\d*)\s+(\S.*)", s)
 if mV is not None:
  if len(mV.group(2)) > 0:
   n= int(mV.group(2))

  mJ= re.search(r"(.*)\s+>>([a-z][a-z0-9]*)", mV.group(3), re.I)
  if mJ is None:	# check for alternative (deprecated) jump form "? name"
   mJ= re.search(r"(.*)\s+\?\s*([a-z][a-z0-9]*)", mV.group(3), re.I)
 
  if mJ is not None:
    vlabel= mJ.group(1)
    jlist[ n ] = mJ.group(2)
  else:
    vlabel= mV.group(3)
  vlist[n]= [ mV.group(1), vlabel ]
 return(n+1)

def do_clu(s):
 s= s.rstrip()
 mU= re.search(r"^\?=\s*([a-z][a-z0-9]*)(.*)", s, re.I)
 if mU is not None:
  chk.write( " type comment maroon\n" )
  chk.write( " comment legal use %s\n" % (mU.group(1)) )
  jspec= mU.group(2).strip()
  if len(jspec) > 0:
   jspecs= re.split(r"[>\s]+", jspec)
   for i in range(0, len(jspecs), 2):
    jlist[ int(jspecs[i]) ]= jspecs[ i+1 ]
 return()


################################################################



inp= file(sys.argv[1]+".fld", 'r')
qes= file(sys.argv[1]+".qes", 'w')
chk= file(sys.argv[1]+".chk", 'w')
flist= dict()
vlist= dict()
jlist= dict()
fnum= 0
qnum= 0
fromtop= 0

line=inp.readline()

while CHKCMD(line):
 do_chk(line)
 line=inp.readline()

while EXISTS(line):
 
 if CHKCMD(line):
  while CHKCMD(line):
   do_chk(line)
   line=inp.readline()
 #end if CHKCMD

 if QESTXT(line):
  while QESTXT(line):
   qnum= do_qes(line, qnum)
   line=inp.readline()
 #end if QESTXT

 if FLDDEF(line):
  fnum += 1
  vlist= dict()
  jlist= dict()
  do_fld(line, fnum)
  line=inp.readline()

  while EXISTS(line) and not  FLDDEF(line) and not QESTXT(line):
   if CLVCMD(line):
    VVAL= 1
    while CLVCMD(line):
     VVAL= do_clv(line, VVAL)
     line=inp.readline()
   #end if CLVCMD

   elif CLUCMD(line):
    do_clu(line)
    line=inp.readline()
   #end if CLUCMD

   elif CHKCMD(line):
    while CHKCMD(line):
     do_chk("% "+line[1:])
     line=inp.readline()
   #end if CHKCMD
  #end while

  if len(vlist) > 0:
   chk.write( " type comment maroon\n" )
   chk.write( " comment legal\n" )
   s= vlist.keys()
   s.sort()
   for k in s:
    chk.write( "  %d \"%s\"\n" % (k, vlist[k][1]) )
   chk.write( " end\n")

  if len(jlist) > 0:
   chk.write( " jumps\n" )
   s= jlist.keys()
   s.sort()
   for k in s:
    chk.write( "  %d %s\n" % (k, jlist[k]) )
   chk.write( " end\n")
 
  # if necessary, insert answer options into QES before the D.E. field line...
  if len(vlist) > 0:
   s= vlist.keys()
   s.sort()
   for k in s:
    if vlist[k][0] == "$":
     qnum += 1
     qes.write( "%10s   (%d)  %s\n" % (' ', k, vlist[k][1]) )
  qes.write( "%-10s %s %s\n" % (flist[fnum][0], flist[fnum][1], flist[fnum][2]) )

  # CHK file entry is almost complete...
  if fromtop > 0:
   chk.write( " topofscreen %d\n" % (qnum-fromtop+1) )
   fromtop= 0
  chk.write("END\n")

 #end if FLDDEF
 

sys.exit()
