import re
import io 
import elf 
import bin as binr
import argparse
import pe
import sys 

bs = binr.bin2str
elfh = elf.parseELFHeader
elfs = elf.parseSectionHeaderTable
peh = pe.parsePEHeader
pes = pe.parsePESectionsHeaderTable

args = sys.argv

parser = argparse.ArgumentParser(description='Find code caves in executables, inject your own code.')
# File we're working with
parser.add_argument('-f, --file', action='store', default="", dest='file_path', help='Location of file to search for code cave in (absolute path)')

# Options for if we're searching for code caves
parser.add_argument('-d, --file-headers', action='store_true', dest='fh', help='Show File Headers')
parser.add_argument('-s, --section-headers', action='store_true', dest='sh', help='Show enumerated section headers')
parser.add_argument('-S, --search', action='store', dest='search', help='Section to search for code cave inside of')
parser.add_argument('-X', action='store_true', dest='allEx', help='Search all executable sections')
parser.add_argument('-A', action='store_true', dest='allSec', help='Search all sections')
parser.add_argument('-l, --length', action='store', default='64', dest='length', help='Number of bytes that constitutes a cave (default 64)')
parser.add_argument('-b, --byte', action='store', default='0x00', dest='byte', help='Byte to be searching for.')

# Options for injecting shellcode
parser.add_argument('-t, --target-offset', action='store', dest='target', help='Target offset to inject shellcode')
parser.add_argument('-j', action='store', dest='injection_file', help='A file of raw bytes to inject')
parser.add_argument('-J', action='store', dest='injection_string', help='A string of raw bytes to inject supplied like \\xef\\xeb')
parser.add_argument('-o, --output-file', action='store', dest='outfile', help='Output file containing backdoor')

parser.add_argument('-B, --banner', action='store_true', dest='print_banner', help='Print banner')

results = parser.parse_args()


class bcolors:
    HEADER = '\033[97m'
    LB = '\033[96m'
    PR = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    TEST = '\033[89m'
    ENDC = '\033[0m'    

lstr = lambda string: "|" + "{:<86}".format(string) + "|"
sstr = lambda string, color: bcolors.HEADER+ "|" + color + "{:<40}".format(string) + bcolors.HEADER + "|"
divisor = bcolors.HEADER+ "+--------------------------------------------------------------------------------------+" +bcolors.ENDC

print bcolors.HEADER + "Caveman.py -- the Code Cave Toolkit!\n\n"

def banner():

    print """
                                          `. .`.+             .o-:`: ::            
                                          +-yoo+h+++/s-. -//sh+s/:o+/+oo:/.         
                                      `::o++.-/:++`  :ohs-`  `       `/.-/m/-       
                                       .oo::.          `:+///+`           :m-       
                                      :o`                  ```             s/       
  /ssssssssso/-                      :s           .--:.         ..`        -y       
/sso+++++++ooosso:`                 `h.            ```-:/-----:/-.-.       `s`      
oyo++++++++++oyyyyyyo-              .s+       ``-`        `````` `-     -`-/+:+      
ho+++++++++++omsssmooys+.        `:/-`        `-+s/h/.       `o `h:` .+:::s.:`y`     
d+++++++++++odhmhhyo++ooyo-     +:.              ``.-+o:` -`.:d+:d++s//`  `   o/     
d+++++++++++sdyho++++++++oss+.`s/                    ``/-::/+so:`+s `         .y     
d+++++++++++oooo+++++++++++ooyyo            `..`      .- ````    :d`   /       y.    
oy++++++++++++++++++++++++++oh-           `/y-+mh:`   `:o         sy` `s  .-+yhos    
ys+++++++++++++++++++++++++h-             .s:oMMNys:`  .         `:s+.::y/oMNm`y.   
`ys+++++++++++++++++++++++ss               `:/+++//                `/y+`...--- -s   
 `oyo+++++++++++++++++++++d.                      .o+o+              :N`       o:   
   :hso++++++++++++++++++oN                       +h.`              -d:       .h    
   .ddysso+++++++++++++++sN                       `ho-.`  /+/   `.`.m-        so    
  .dy+ `:+sso++++++++++++sN                        `:+/.  .``   .+syo         d/    
  :+      `:ssoo+++++++++sm                             ``````     `         `N.    
             -/ssoo+++++od/                      ``.-:/+//:://++:.``        :y+     
                .:+osooodo                       /o/:.`         .:+o     `:so.      
                    `-:+N`                       -`                :  .+o+:`        
                       /d                                     . ``` `+mo`           
                      /d-                                `   `+--+s/hmsys-          
                     +d-                            :-`://---:/hdhmyyyo+oyo:        
                    /d.                             .:`/ooshddddysds+o+++++ss+.     
                  .sm/``                               -+yddsyys+++oo++++++++oys:`  
                `+yo+ssoo/.`                             -d.:/ossoo++++++++++++osso/
              .+yo///+oo++sy/`                   :`       +y`   :+ssooo++++++++++++o
           `/ysoy////sddd///oy+                  h-        :h.     .-+oysoo+++++++++
      `./+ommsssh////+sss/////ss.               /o`         .h/        `-/oysoo+++++
  -osss+:````  .h////++//+ooo+/+yo/.                          /o+oooos+-`   -ohooo++
`oyo.           .h///hddy+sdddh////+ss:                                `:os+`  `:+syy
    """



def getFileType(target_file):
    bfile = io.open(target_file,'rb')
    f = bytes(bfile.read(4))
    if f == "\x7fELF":
        bfile.close()
        return "ELF"
    elif f[0:2] == "\x4d\x5a":
        bfile.close()
        return "PE"


def parseExecHeader(a, path, fh):
    a = a.upper()
    if a == "ELF":
        p = elfh(path,fh)
        return p
    elif a == "PE":
        p = peh(path,fh)
        return p
    else:
        print "Invalid file type %s" % a
        return 0

def sectionsOverView(sections,btype):
    print bcolors.FAIL +  "\nSection Headers: " + bcolors.HEADER
    print divisor
    if btype == "ELF":
        print "%s| %s[Number] %s%s %s%s %s%s %s%s%s |" % (bcolors.HEADER, bcolors.FAIL, bcolors.HEADER, "{:<18}".format('Name'),bcolors.OKGREEN, "{:<18}".format('Type'), bcolors.LB, "{:<18}".format('Addr'), bcolors.OKBLUE,"{:<18}".format('Offset'),bcolors.HEADER )
        print "%s|          %s%s %s%s %sFlags              %sAlignment          |" % (bcolors.HEADER,bcolors.PR,"{:<18}".format('Size'),bcolors.WARNING, "{:<18}".format('EntSize'), bcolors.FAIL, bcolors.HEADER )
        print divisor
        for x in range(0,len(sections)):
            section = sections[x]
            y = hex(x)
            if len(y) < 4:
                y = "0x0" + y[-1]
            string1 = "%s|%s [ %s] %s%s %s%s %s%s %s%s %s|" % (bcolors.HEADER,bcolors.FAIL, "{:<5}".format(y), bcolors.HEADER, "{:<18}".format(section['name']), bcolors.OKGREEN, "{:<18}".format(section['type']), bcolors.LB, "{:<18}".format(section['sh_addr']), bcolors.OKBLUE, "{:<18}".format(section['sh_offset']), bcolors.HEADER )
            string2 = "%s|%s          %s %s%s %s%s %s%s |" % (bcolors.HEADER,bcolors.PR,"{:<18}".format(section['sh_size']), bcolors.WARNING, "{:<18}".format(section['sh_entsize']), bcolors.FAIL, "{:<18}".format(section['parsed_flags']), bcolors.HEADER, "{:<18}".format(section['sh_addralign']))
            print string1
            print string2
            print divisor
    elif btype == "PE":
        print "%s| %s[Number] %s%s %s%s %s%s %s%s%s |" % (bcolors.HEADER, bcolors.FAIL, bcolors.HEADER, "{:<18}".format('Name'),bcolors.OKGREEN, "{:<18}".format('Size'), bcolors.LB, "{:<18}".format('Virtual Size'), bcolors.OKBLUE,"{:<18}".format('Location'),bcolors.HEADER )
        print "%s|          %s%s %s%s %s%s %s%s |" % (bcolors.HEADER,bcolors.PR,"{:<18}".format('Data Pointer'),bcolors.WARNING, "{:<18}".format('Reloc Pointer'),bcolors.FAIL, "{:<18}".format('Flags'),bcolors.HEADER,"{:<18}".format('Characteristics') )
        print divisor
        for x in range(0,len(sections)):
            section = sections[x]
            y = hex(x)
            if len(y) < 4:
                y = "0x0" + y[-1]
            string1 = "%s|%s [ %s] %s%s %s0x%s %s0x%s %s0x%s %s|" % (bcolors.HEADER,bcolors.FAIL, "{:<5}".format(y), bcolors.HEADER, "{:<18}".format(section['sh_name']), bcolors.OKGREEN, "{:<16}".format(section['sh_size']), bcolors.LB, "{:<16}".format(section['sh_vsize']), bcolors.OKBLUE, "{:<16}".format(section['sh_addr']), bcolors.HEADER )
            string2 = "%s|%s          0x%s %s0x%s %s%s %s0x%s |" % (bcolors.HEADER,bcolors.PR,"{:<16}".format(section['sh_dataPointer']), bcolors.WARNING, "{:<16}".format(section['sh_relocPointer']), bcolors.FAIL, "{:<18}".format(section['parsed_flags']), bcolors.HEADER, "{:<16}".format(section['sh_characteristics']))
            print string1
            print string2
            print divisor


def crawlSection(o, s, fl, name, path, length, enumerating):

    f = io.open(path,'rb')
    f.seek(o)
    b = f.read(s)
    seclen = len(b)
    
    cave_arr = []
    cave_offset = ""
    cave_length = 0    
    counting = False
    finished = False
    
    def check_cave(length, min_length):
        ml = int(min_length)
        if length < ml:
            #Not long enough
            return False
        elif length >= ml:
            # Long enough to be a code cave
            return True

    for i,rbyte in enumerate(b):
        hxb = hex(ord(rbyte))
        ende = (i==len(b)-1)
        #Byte is null
        if hxb == "0x0":        
            #If we aren't counting yet, we should start, this is a new cave
            if counting == False:
                cave_offset = i + o
                cave_length = 1
                counting = True
            #If we are counting, increment the cave_length
            if counting == True:
                cave_length += 1
            #If we're at the end, check to see if it's long enough to add cave
            if ende == True:
                long_enough = check_cave(cave_length,length)
                if long_enough:
                    myObj = {
                        "Starting Offset" : cave_offset,
                        "Length" : cave_length,
                        "Flags" : fl,
                        "Name" : name
                    }

                    cave_arr.append(myObj)  

        #Byte is not null
        if hxb != "0x0":
            #If we are counting, we've encountered the end
            if counting == True:  
                long_enough = check_cave(cave_length,length)
                if long_enough:
                    myObj = {
                        "Starting Offset" : cave_offset,
                        "Length" : cave_length,
                        "Flags" : fl,
                        "Name" : name
                    }

                    cave_arr.append(myObj)  
                cave_offset = ""
                cave_length = 0    
                counting = False


    if len(cave_arr) > 0 :
        return cave_arr        
    elif len(cave_arr) == 0:
        return 0

def print_caves(arr):

    for x in range(0,len(arr)):
        cave = arr[x]
        notification = "" + bcolors.HEADER
        notification += "+----------------------------------------+\n"
        notification += "|              Cave Located!             |\n"
        notification += sstr("Section: %s " % cave['Name'], bcolors.HEADER) + '\n'
        notification += sstr("Starting offset: %s " % hex(cave['Starting Offset']), bcolors.OKGREEN)+ '\n'
        notification += sstr("Ending offset: %s " % hex(int(cave['Starting Offset']) + int(cave['Length'])), bcolors.OKGREEN)+ '\n'
        notification += sstr("Cave length: %s bytes" % cave['Length'], bcolors.WARNING ) + '\n'
        notification += sstr("Flags: %s " % cave['Flags'], bcolors.FAIL) + '\n'
        notification += "+----------------------------------------+" + '\n'
        print notification

        
def main():
    global args
    global results
    path = results.file_path
    if path == '':
        path = raw_input("Input absolute path to the file to look for code caves in\n> ")
    fh = results.fh
    ftype = getFileType(path)
    sh = results.sh
    se = results.search
    sAX = results.allEx
    sA = results.allSec
    ccByte = results.byte
    caveLen = results.length
    print_banner = results.print_banner

    enumerating = False
    injecting = False
    if print_banner == True:
        banner()

    # Default behavior: Prompt for 

    e = ['-d', '--file-headers', '-s', '--section-headers', '-S', '--search', '-X', '-A', '-l', '--length', '-b', '--byte']
    for flag in e:
        if flag in args:
            enumerating = True

    i = ['-t', '--target-offset', '-j', '-J', '-o', '--output-file']
    for flag in i:
        if flag in args:
            injecting = True

    if (len(args)==1 or (len(args)==3 and path != '')):
        enumerating = True
        fh = True
        sh = True
        sA = True

    EH = parseExecHeader(ftype, path,fh)

    crawled = []

    if ftype == "ELF":

        sections = elfs(path, EH['sht'], EH['arch'], EH['endian'], EH['e_shnum'], EH['e_shentsize'], EH['e_shstrndx'], sh)
        if sh:
            sectionsOverView(sections, ftype)
        
        for sec in sections:
            if sA:
                c = crawlSection(int(sec['sh_offset'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['name'], path, caveLen,enumerating)
                if c:
                    for e in c:
                        crawled.append(e)
            elif (int(sec['sh_flags']) & 0b100) and sAX == True:
                c = crawlSection(int(sec['sh_offset'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['name'], path, caveLen,enumerating)
                if c:
                    for e in c:
                        crawled.append(e)            
            elif se and sec['name'] == se:
                c = crawlSection(int(sec['sh_offset'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['name'], path, caveLen,enumerating)
                if c:
                    for e in c:
                        crawled.append(e)
    elif ftype == "PE":
        sections = pes(path,EH['sht'],EH['endian'],EH['e_shnum'],EH['e_shentsize'],sh)
        if sh:
            sectionsOverView(sections,ftype)

#        flagStr = pfl(flags, 0x20000000, "X", flagStr)
        for sec in sections:
            if sA:
                c = crawlSection(int(sec['sh_dataPointer'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['sh_name'], path, caveLen, enumerating)
                if c:
                    for e in c:
                        crawled.append(e)
            elif (int(sec['sh_characteristics'],16) & 0x20000000) and sAX == True:
                c = crawlSection(int(sec['sh_dataPointer'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['sh_name'], path, caveLen,enumerating)
                if c:
                    for e in c:
                        crawled.append(e)
            elif se and sec['name'] == se:
                c = crawlSection(int(sec['sh_dataPointer'],16), int(sec['sh_size'],16), sec['parsed_flags'], sec['sh_name'], path, caveLen, enumerating)
                if c:
                    for e in c:
                        crawled.append(e)
    
    if enumerating == True:
        print bcolors.OKBLUE + "Done crawling for caves: Found %s" % len(crawled)
    if (len(crawled) > 0) and (enumerating == True):
        print_caves(crawled)
    # We have caves, check injection options
    if injecting == True:
        #Make sure there's a -J or -j
        binShell = None
        if results.injection_file:
            binS = io.open(results.injection_file,'rb')
            binS.read()
            binShell = bytearray.fromhex(binS)
        elif results.injection_string:
            ijstr = results.injection_string
            ijstr = ijstr.lower()
            binShell = bytearray.fromhex(ijstr)
        if binShell == None:
            print "Error: Need -j or -J flag to supply shellcode to inject"
            sys.exit(0)

        tgt = results.target

        if tgt == None:
            print "Error: Need -t flag to point to target offset (in hex)"
            sys.exit(0)
        else: 
            target_offset = int(tgt,16)

        outFile = results.outfile
        if not outFile:
            outFile = "Caveman_output"

        print "Writing shellcode (%s bytes) to offset 0x%s" % (len(binShell), tgt)
        bd = io.open(path,'r+b')
        bd.seek(target_offset)
        bd.write(binShell)
        bd.close()
        print "Shellcode written!"
main()
