#!/bin/sh
# Executed by the service under /etc/systemd/system/comm_setup.service
# Send a message to the M4 to let it know the address of the A7
# Communication over Virtual UART (over RPMsg) won't work without this step

# Interface to read M4 state
rproc_state="/sys/class/remoteproc/remoteproc0/state"
# Maximum time waited for M4 to start 
timeout=5

# Wait until M4 is running
start_time=$(date +%s)
while [ $(cat $rproc_state) != "running" ]
do 
  curr_time=$(date +%s)
  if [ $(( curr_time-start_time )) -ge $timeout ]
  then
    echo "[ERROR] $timeout seconds timeout elapsed" >&2
    echo -e "[INFO] Send any message on /dev/ttyRPMSGx to be able\n       to receive data from Cortex M4"
    exit 1
  fi 
done

# Find RPMsg interface
#ttyRPMSGx=$(find /dev -regex ".*/ttyRPMSG[0-9]\{1,\}$")
#echo $ttyRPMSGx

ttyRPMSGx="/dev/ttyRPMSG0"

# Let the M4 know the A7 address
# Threshold transmission format: <low_thr>(mV);<high_thr>(mV)
echo -n "0;2900" > $ttyRPMSGx
