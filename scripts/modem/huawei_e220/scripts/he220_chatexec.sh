#!/bin/sh
# Sourced from http://wwwu.uni-klu.ac.at/agebhard/HuaweiE220/
# IMPORTANT: Set +x permission on this file for all users

# call the preparation chat script (with pin and if this fails without pin)
/usr/sbin/chat -V -f /etc/chatscripts/{=chatfile_pre}
# wait to switch between GPRS/UMTS
sleep 15
# the final chat script:
/usr/sbin/chat -V -f /etc/chatscripts/{=chatfile_post}