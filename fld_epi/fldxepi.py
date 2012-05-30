# fld2epi --parse a FLD spec file as series of 'blocks', generate EPIDATA .QES and .CHK files 
# 
#pending:
# - vary behaviour when "$", detected on (any?) comment-legal value line
# - NOTE: "$" causes output to QES, but this upsets counting of QES lines, and means page-align doesnt work right
# - vary behaviour when "!", detected on (any?) comment-legal value line
# - ?investigate whether feasible to allow CHK-block lines intermixed in FLD (i.e accept positions other than imm. after FLD block)
#
#==============================================================================
# Syntax of FLD spec file is a sequence of blocks of lines. Blocks can be of different types:
# - CHK : 1 or more lines of EpiData 'chk' commands 
# - FLD : 1 or more lines of "field-specification" data
# - QES : 1 or more lines of any line-type which is not classified as belonging to any of above block types
# 
# The allowable/expected sequence of blocks in an input .fld file is:
#  CHK       	optional: block of CHK commands 
#  QES		Questionnaire text, ie. text which will appear as-is in the QES file (but does not contain D.E. fields)
#  FLD		Field specification lines, including field name, text for creating comment-legal and jump instructions
#  CHK		optional: CHK commands specific to FIELD just processed (eg mustenter, after entry, before entry etc
#  : :		... any number of groups of the above 3 block types (preserving order QES-FLD-CHK)
# 
# QES blocks only provide info for the .QES file. CHK blocks only provide info for the .CHK file.
# FLD blocks contain info which involves writing to both QES and CHK files.
# 
# FLD blocks may contain a mixture of line-types (sort of sub-blocks within it), but must start with the
# definition of the field consiting of: name  type  width  decimals  prompt-string (eg "weight n 4 1 Height in cm").
# This may then be followed by either:
#  a series of lines where we provide values label strings for a COMMENT LEGAL block, and if needed we may also
#  provide (for each label) a field to JUMP to.
# or:
#  a single line referencing a predefined label set, and if needed, associated jumps for different values
#
# Examples:
#  +---------------------------------------------+
#  |Podria hablar con NOMBRE DE PACIENTE?        |
#  |inicio n 1 0 [ inicio de entrevista ]        |
#  |? Si >>siproxy                               |
#  |? NO, por DEFUNCION >>f01                    |
#  |? NO, por DISCAPACIDAD >>proxy               |
#  |? NO, Continua ingresado/enfermo >>x96       |
#  |? NO, no disponible en este momento >>x98    |
#  |?9 NS/NC                                     |
#  |%mustenter                                   |
#  |                                             |
#  |                                             |
#  |proxy n 1 0 Podria hablar con algun familiar?|
#  |?=si1no2 1>>siproxy 2>>x97                   |
#  |%mustenter                                   |
#  +---------------------------------------------+
# 
# feb 2010
#
#!!python fld2epi.py test
#
import sys,string,re

if len(sys.argv) != 2:
 print """
  usage: fld2epi.py  FILE

  Parse a file called FILE.fld, and use info obtained from it create
  two outputs:  FILE.qes  and  FILE.chk
 """
 sys.exit()



def IGREP (s, p):
############################################################
# Search string 's' for pattern 'p', ignoring case.
# Return a list containing matched strings corresponding to
# the parenthesized groups in 'p'.
#
# e.g. the call:
#   X= IGREP('ID - 999', r"(^(..)\D+(\d+)")
# returns the list 
#   ['ID', '999'] as the value of X
#
############################################################
 mlist= []
 if s is not None:
  MM= re.search(p, s, re.I)
  if MM != None:
   mlist= MM.groups()
 return(mlist)

################################################################
def EXISTS(s):
 return( (len(s)>0) )

################################################################
def FLDSPEC(s):
 result= False
 if EXISTS(s):
  if re.search(r"^[a-z][a-z0-9]*\s+[Ccnd]\s+\d+\s+\d+\s+\S", s, re.I) is not None: result= True
  if re.search(r"^[\?\$\!][\s\d=]\s*\S", s, re.I) is not None: result= True
 return( result )

################################################################
def CHKCOMMAND(s):
 result= False
 if EXISTS(s):
  if re.search(r"^%", s) is not None: result= True
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
################################################################


inp= file(sys.argv[1]+".fld", 'r')
qes= file(sys.argv[1]+".qes", 'w')
chk= file(sys.argv[1]+".chk", 'w')

line=inp.readline()	# get first

bnum= 0			# count blocks
qnum= 0			# 'global' screen-line enumeration in QES
fnum= 0			# 'global' fields enumeration
bname= ''
enumbase= 1		# default to enumerate value-labels starting from 1
fromtop= None		# use to count lines between a page-align and a field def. so appropriate TOPOFSCREEN can be generated 
vbase= None
flist= dict()		# dict to store field-spec details of each identfied data-entry field

while CHKCOMMAND(line):	# optional leading block of chk commands
 line= line.rstrip()
 chk.write( "%s\n" % (line[1:]) )
 line=inp.readline()	# ignore current, get next

while EXISTS(line):				# repeat while scan for ... ended successfully
 bnum += 1		# count new block
 blen= 0		# new block starting now
 bname= line.strip()	# "name" of the block 

 while EXISTS(line) and not FLDSPEC(line) and not CHKCOMMAND(line):	# look for start of a fldspec or "free" chk block
  # process current
  line= line.rstrip()
  blen += 1
  if re.search(r"^\[\]", line) is not None:	# we have a 'page-align' request
   fromtop= qnum	# save current QES line number (but we dont print the line itself)
  else:
   qnum += 1
   qes.write( "%-10s %s\n" % (' ', line) )

  # get next
  line=inp.readline()

 # end-of-block specific stuff...
 blen= 0
 

 if FLDSPEC(line):
  line= line.rstrip()
  fnum += 1
  vnum= enumbase
  vlist= dict()
  jlist= dict()
  mF= IGREP(line, r"^([a-z][a-z0-9]*)\s+([Ccnd])\s+(\d+)\s+(\d+)\s+(\S.*)")
  if len(mF) != 0:	# dataentry field spec line
   fname= mF[0]
   ftype= mF[1]
   fwidth= int(mF[2])
   fndec = int(mF[3])
   fprompt= mF[4]
   de_fld= make_de(ftype, fwidth, fndec)
   fprompt= make_pf(fprompt, de_fld)
   flist[fnum]= [ fname, fprompt, de_fld ]
   #qnum += 1
   #qes.write( "%-10s %s %s\n" % (fname, fprompt, de_fld) )
   chk.write( "\n%s\n" % (fname) )
   if fnum == 1:
    chk.write( " key unique\n" )
   #if fromtop is not None:
   # chk.write( " topofscreen %d\n" % (qnum-fromtop) )
   # fromtop= None
   
  while FLDSPEC(line):	# process field-specs, ie scan for line which can't be part of a field-spec
   line= line.rstrip()
   blen += 1

   # check for item to be treated as a single comment-legal legal value (maybe with one jump-specification)
   mV= IGREP(line, r"^([\?\!\$])([\d]?)\s+(\S.*)$")
   if len(mV) != 0:
    vtype=  mV[0]
    vbase=  mV[1]
    if len(vbase) > 0: vnum= int(vbase)
    vlabel= mV[2]
    vjump=  ''
    mJ= IGREP(vlabel, r"(>>)([a-z][a-z0-9]*)\s*$")	# vlabel part ends with '>>name' (Preferred form)
    if len(mJ) == 0:	# if not, try old (deprecated) form 
     mJ= IGREP(vlabel, r"(\?)([a-z][a-z0-9]*)\s*$")	# vlabel part ends with '?name'
    if len(mJ) != 0:
     vjump=  mJ[1]
     p= len(vjump)+len(mJ[0])	# total length of the jump-spec we have identified, incl. its leading punctuation
     vlabel= vlabel[:-p]	# retain part before the jump-spec as new value of vlabel
     vjump= vjump.rstrip()	# remove any trailing space
     jlist[vnum]= vjump
     vlabel= vlabel.rstrip()
    vlist[vnum]= vlabel
    vnum += 1

   # check for item to be treated as a comment-legal-use-name, which may have 1 or more jumps associated
   mV= IGREP(line, r"^(\?)(=)([a-z][a-z0-9]*)\s*(.*)$")
   if len(mV) != 0:
    vlist= dict()
    vtype=  mV[0]
    vbase=  mV[1]
    vlabel= mV[2]
    vjump=  mV[3]
    if len(vjump) > 0:
     jelement= re.split(r"[\s>]+", vjump)
     for i in range(0,len(jelement),2): 
      jlist[ int(jelement[i]) ]= jelement[i+1]


   # get next
   line=inp.readline()
  #end-while

  # end-of-FLD specific stuff...
  if len(vlist) > 0: 
   chk.write( " type comment maroon\n" )
   chk.write( " comment legal\n" )
   s= vlist.keys()
   s.sort()
   for vnum in s:
    chk.write( "  %d \"%s\"\n" % (vnum, vlist[vnum]) )
   #end-for
   chk.write( " end\n" )
 
  if vbase is not None:
   if vbase == '=':
    chk.write( " type comment maroon\n" )
    chk.write( " comment legal use %s\n" % (vlabel) )
    vbase= None
 
  if len(jlist) > 0:
   chk.write( " jumps\n" )
   s= jlist.keys()
   s.sort()
   for vnum in s:
    chk.write( "  %d %s\n" % (vnum, jlist[vnum]) )
   #end-for
   chk.write( " end\n" )

  if CHKCOMMAND(line):	
   while EXISTS(line) and CHKCOMMAND(line):
    line= line.rstrip()
    blen += 1
    chk.write( " %s\n" % (line[1:]) )
 
    # get next
    line=inp.readline()
   #end-while
  #end-if
 
  # end-of-CHK specific stuff...
  if len(vlist) > 0 and vtype == "$":	# show comment-legal values in QES file too
   s= vlist.keys()
   s.sort()
   for vnum in s:
    qnum += 1
    qes.write( "%-10s  (%d) %s\n" % (' ', vnum, vlist[vnum]) )
   #end-for
   #qes.write( "\n" )
  qnum += 1
  qes.write( "%-10s %s %s\n" % (fname, fprompt, de_fld) )
 
  if fromtop is not None:
    chk.write( " topofscreen %d\n" % (qnum-fromtop) )
    fromtop= None
  chk.write( "END\n" )

 #end-if (fldspec)


 if EXISTS(line) and  CHKCOMMAND(line):		# optional "free" block of chk commands
  while EXISTS(line) and CHKCOMMAND(line):	# copy as-is
   line= line.rstrip()
   chk.write( "%s\n" % (line[1:]) )
   line=inp.readline()	# ignore current, get next
  #end-while
 #end-if


#end-while

sys.exit()
