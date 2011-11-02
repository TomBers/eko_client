#!/bin/sh

# Boot strap the eko-logger scripts

# turn on the led display
i2cset -y 2 0x20 0x00 0x00
i2cset -y -m 0xF8 2 0x20 0x09 0xF8

# get the userbutton
echo 4 > /sys/class/gpio/export

# sleep for 2 seconds
sleep 2

# turn off the led display
i2cset -y -m 0xF8 2 0x20 0x09 0x00

# user has 10 seconds to hit button
SECONDS=0

echo "Press the user button down for a few seconds in order to enter testing mode..."

TEST_MODE=0
LIGHT_STATUS=0

while [ $SECONDS -lt 10 ]; do
    sleep 1
    
    let SECONDS=$SECONDS+1
    
    if [ $LIGHT_STATUS -eq 1 ] ; then
        i2cset -y -m 0xF8 2 0x20 0x09 0x00
        LIGHT_STATUS=0
    else
        i2cset -y -m 0xF8 2 0x20 0x09 0xFF
        LIGHT_STATUS=1
    fi
    BTN=`cat /sys/class/gpio/gpio4/value`
    if [ $BTN -eq 1 ] ; then
        TEST_MODE=1
        # set half the leds on
        i2cset -y -m 0xF8 2 0x20 0x09 0x0F
        break
    fi
    
    echo "Entering test mode $SECONDS/10"
done

if [ $TEST_MODE -eq 1 ] ; then
    i2cset -y -m 0xF8 2 0x20 0x09 0x0F
    # bring the usb hub up
    modprobe ehci_hcd
    echo "Entering test mode!"
    sleep 10
    ifconfig usb0 192.168.1.100
    echo "Network waiting on 192.168.1.100"
    route add default gw 192.168.1.1
    echo "Network Up. Now blocking indefinitely."
    SECONDS=0
    while [ $SECONDS -lt 500 ]; do
        sleep 6
        
        let SECONDS=$SECONDS+1
        if [ $LIGHT_STATUS -eq 1 ] ; then
            i2cset -y -m 0xF8 2 0x20 0x09 0x00
            LIGHT_STATUS=0
        else
            i2cset -y -m 0xF8 2 0x20 0x09 0xFF
            LIGHT_STATUS=1
        fi
    done
else
    echo "Launching scripts"
    /usr/bin/python /home/root/eko_client/eko_logger.py
fi