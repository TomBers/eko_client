from ovotemplate import Ovotemplate
import sys
import os
from os import path

CHATDIR = "build/etc/chatscripts/"
PEERDIR = "build/etc/ppp/peer/"
SHDIR = "build/usr/sbin/"

def main(modem, operator, apn, username, password="", level="0"):
    dict = {'OperatorName':operator, 'APN': apn, 'username': username, 'password': password}
    dict['ipcpRetryStuff'] = False
    dict['lcpRetryStuff'] = False
    dict['GprsOnly'] = False
    dict['ThreeGPreferred'] = True
    dict['UseBasic'] = False
    
    if level == "1":
        dict['ipcpRetryStuff'] = True
        dict['lcpRetryStuff'] = True
    elif level == "2":
        dict['ipcpRetryStuff'] = True
        dict['lcpRetryStuff'] = True
        dict['GprsOnly'] = True
    elif level == "3":
        dict['lcpRetryStuff'] = True
        dict['GprsOnly'] = True
    elif level == "4":
        dict['UseBasic'] = True
    
    if modem == "he220":
        fileprefix = "he220.%s.%s" % (operator, level)
        dict['chatexec'] = fileprefix + "_chat.sh"
        dict['chatfile_pre'] = fileprefix + "_prep.chat"
        dict['chatfile_post'] = fileprefix + "_call.chat"
        dict['peerfile'] = fileprefix + ".peer"
        dict['USBDevice'] = 'ttyUSB0'
        build_huawei_scripts(dict)
    elif modem == "mf112":
        fileprefix = "mf112.%s" % (operator,)
        dict['chatfile'] = fileprefix + ".chat"
        dict['peerfile'] = fileprefix + ".peer"
        dict['USBDevice'] = 'ttyUSB2'
        build_zte_scripts(dict)
    else:
        print "Invalid modem %s specified: he220, mf112 supported" % modem

def build_makedirs():
    if not path.exists(CHATDIR):
        os.makedirs(CHATDIR)
    if not path.exists(PEERDIR):
        os.makedirs(PEERDIR)
    if not path.exists(SHDIR):
        os.makedirs(SHDIR)

def build_huawei_scripts(dict):
    build_makedirs()
    f = open('huawei_e220/chatscripts/he220_prep.chat.template', 'rb')
    tpl_prepchat = f.read()
    f.close()
    f = open('huawei_e220/chatscripts/he220_call.chat.template', 'rb')
    tpl_callchat = f.read()
    f.close()
    if dict['UseBasic']:
        peerfile = 'huawei_e220/peers/mtnrw.he220.bas.peer.template'
    else:
        peerfile = 'huawei_e220/peers/mtnrw.he220.adv.peer.template'
    f = open(peerfile, 'rb')
    tpl_peer = f.read()
    f.close()
    
    f = open('huawei_e220/scripts/he220_chatexec.sh', 'rb')
    tpl_shscript = f.read()
    f.close()
    
    build_template(tpl_prepchat, CHATDIR + dict['chatfile_pre'], dict)
    build_template(tpl_callchat, CHATDIR + dict['chatfile_post'], dict)
    build_template(tpl_peer, PEERDIR + dict['peerfile'], dict)
    build_template(tpl_shscript, SHDIR + dict['chatexec'], dict)
    print "All tasks done."

def build_zte_scripts(dict):
    build_makedirs()
    f = open('zte_mf112/chatscripts/mf112.chat.template', 'rb')
    tpl_chat = f.read()
    f.close()

    f = open('zte_mf112/peers/gen.mf112.peer.template', 'rb')
    tpl_peer = f.read()
    f.close()
    
    f = open('huawei_e220/scripts/he220_chatexec.sh', 'rb')
    tpl_shscript = f.read()
    f.close()
    
    print "!! Levels have no effect for this modem."
    
    build_template(tpl_chat, CHATDIR + dict['chatfile'], dict)
    build_template(tpl_peer, PEERDIR + dict['peerfile'], dict)
    print "All tasks done."

def build_template(template_text, output_path, dict):
    print "Building Template to %s..." % output_path
    ovotemp = Ovotemplate(template_text)
    result = ovotemp.render(dict)
    f = open(output_path, 'wb')
    f.write(result)
    f.close()
    
if __name__=="__main__":
    if len(sys.argv) < 5:
        print "Usage: ppp_script_gen.py MODEM OPERATOR APN USERNAME [COMPLEXITY] [PASSWORD]"
        print "   MODEM: he220 || mf112"
        print "   OPERATOR, APN, USERNAME: ..."
        print "   COMPLEXITY: 0 to 4 where 0 is most basic, 3 is all settings"
        print "   PASSWORD: ..."
        print ""
        print "Output will be placed in ./build/"
        sys.exit(0)
    modem = sys.argv[1]
    operator = sys.argv[2]
    apn = sys.argv[3]
    uname = sys.argv[4]
    
    print "Building scripts for modem: %s with operator %s (%s)..." % (modem, operator, apn)
    
    if modem not in ['he220', 'mf112']:
        print "Invalid modem specified. Use he220 or mf112."
    
    if len(sys.argv) >= 6:
        level = sys.argv[5]
        print "Creating level %s script." % level
    else:
        level = "0"
    
    if len(sys.argv) == 7:
        password = sys.argv[6]
        print "Password set to: %s" % password
    else:
        password = ""
    
    main(modem, operator, apn, uname, password, level)
    