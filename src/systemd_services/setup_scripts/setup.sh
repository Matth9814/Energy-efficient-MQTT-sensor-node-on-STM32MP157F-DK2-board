#!/bin/sh
# Executed by the service under etc/systemd/system/setup.service

# Enable mailbox as wakeup source
echo enabled > /sys/devices/platform/soc/4c001000.mailbox/power/wakeup

# Flash M4
#cd /usr/local/Cube-M4-examples/STM32MP157C-DK2/Applications/OpenAMP/OpenAMP_TTY_echo_wakeup
cd /home/root/OpenAMP_TTY_echo_wakeup_CM4/
./fw_cortex_m4.sh start
