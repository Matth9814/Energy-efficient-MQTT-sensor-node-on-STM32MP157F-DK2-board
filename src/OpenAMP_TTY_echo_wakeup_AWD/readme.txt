/**
  @page OpenAMP_TTY_echo_wakeup OpenAMP TTY echo wake up example

  @verbatim
  ******************************************************************************
  * @file    OpenAMP/OpenAMP_TTY_echo_wakeup/readme.txt
  * @author  MCD Application Team
  * @brief   Description of the OpenAMP TTY echo wake up Application.
  ******************************************************************************
  *
  * Copyright (c) 2021 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  *
  ******************************************************************************
  @endverbatim

@par Application Description

How to use OpenAMP MW to enter in different power system operating mode (Run, Stop and Standby).
 
This project deals with CPU2 (Cortex-M4) firmware and requires Linux OS running on CPU1 (Cortex-A7)
OpenAMP MW uses the following HW resources
    * IPCC peripheral for event signal (mailbox) between CPU1(CA7) and CPU2(CM4)
    * MCUSRAM peripheral for buffer communications (virtio buffers) between CPU1(CA7) and CPU2(CM4)
            Reserved shared memeory region for this example: SHM_ADDR=0x10040000 and SHM_SIZE=128k.
            It is defined in platform_info.c file

In this example:
  - CPU1(CA7 aka Master processor) loads and powers on CPU2(CM4 aka Remote processor)
                through remoteproc framework in Linux OS. System clock
                configuration is done only once by CPU1(CA7)
    - CPU2(CM4) initializes OPenAMP MW which initializes/configures IPCC peripheral
                through HAL and setup openamp-rpmsg framwork infrastructure
                (1st level of communication btween CPU1(CA7) and CPU2(CM4)
    - CPU2(CM4) configures ADC to convert a single channel, in single conversion
                mode, from HW trigger: timer peripheral.
                DMA is configured to transfer conversion data in an array, in circular mode.
                A timer is configured in time base and to generate TRGO events.
                From the start, the ADC converts the selected channel at each trig from timer.
                DMA transfers conversion data to the array, DMA transfer complete interruption occurs.
                Results array is updated indefinitely (DMA in circular mode).
                LED7 is turned on when the DMA transfer is completed (results array full)
                and turned off at next DMA half-transfer (result array first half updated).
    - CPU2(CM4) User push button is used to increase DAC voltage in 4 circular steps.
                DAC voltage is used to feed ADC.
    - CPU2(CM4) creates an rpmsg channel for the virtual UART instance UART0
    - CPU2(CM4) is waiting for messages from CPU1(CA7) on this channel
        *  When CPU2(CM4) receives a message on the Virtual UART instance/rpmsg channel,
           it sends the message back to CPU1(CA7) on that Virtual UART instance
    - Some messages are handled specifically by CM4:
        - "*stop"    : upon reception of this message, CM4 goes to CStop mode and only allow entering System Stop mode
        - "*standby" : upon reception of this message, CM4 goes to CStop mode and allow entering System Stop or Standby mode.
        - "*delay"   : CM4 sends a RPMsg message to CA7 after a 20 second delay. It is a Wakeup source for CA7


    Notes:
    - It requires Linux console to start & run example.
    - CPU2(CM4) logging is redirected in Shared memory in MCUSRAM and can be displayed in Linux console for verdict
      using following command:
          cat /sys/kernel/debug/remoteproc/remoteproc0/trace0

    Following command should be done in Linux console on CA7 to run the example :

    > ./fw_cortex_m4.sh start
    > stty -onlcr -echo -F /dev/ttyRPMSG0
    > cat /dev/ttyRPMSG0 &
    > echo "Hello Virtual UART0" >/dev/ttyRPMSG0

    You should get "Hello Virtual UART0" in Linux console

    > ./fw_cortex_m4.sh stop
      For this example, on Stop the Cortex-A7 send a shutdown request through IPCC peripheral to the Cortex-M4 so that it is able to take necessary actions to stop ADC and DMA before stopping the example.

----------------------------------------------
- The following operating mode can be tested -
----------------------------------------------


1)  System Run Mode with CA7 in CRun and CM4 in CStop
    -------------------------------------------------
    Objective: Testing CM4 CStop low power mode and CM4 wakes up with Exti line 62 (IPCC interrupt CPU2)

    1.0 - CM4 firmware has configured Exti line 62 (IPCC interrupt CPU2) as a wake up source

    1.1 - Move CM4 in CStop mode
          > echo "*stop" >/dev/ttyRPMSG0

          On reception of this message, CM4 backs up PLL3/PLL4 and MCU clock
          configuration. Finally MCU calls HAL_PWR_EnterSTOPMode(PWR_MAINREGULATOR_ON,
          PWR_STOPENTRY_WFI) and goes into CStop mode.
          LED7 stops toggling as CM4 subsystem peripherals clock is stalled and therefore
          ADC conversions are stopped

    1.2 - Move CM4 in CRun mode using Exti line 62 (IPCC interrupt CPU2)
          > echo "wakeup" >/dev/ttyRPMSG0
          Sending a new message wakes up CM4 with Exti line 62 (IPCC interrupt CPU2) 

          LED7 toggles as CM4 subsystem peripherals clock is resumed
          and therefore ADC conversions are resumed

    Note: you can check CM4 logs :
          > cat /sys/kernel/debug/remoteproc/remoteproc0/trace0


2)  System Run Mode with CA7 in CStop and CM4 in CRun
    -------------------------------------------------
    Objective: Testing CA7 CStop low power mode and CA7 wakes up with source Exti line 61 (IPCC interrupt CPU1)

    2.0 - Set Exti line 61 (IPCC interrupt CPU1) as source of wakeup.
          > echo enabled > /sys/devices/platform/soc/4c001000.mailbox/power/wakeup

          Note: This commands allows CA7 mailbox wakeup capability. EXTI->IMR2(61) will be configured
          only when Linux command to move CA7 in low power mode will be done.

    2.1 - Configure CM4 to wakeup CA7 after 20 seconds
          > echo "*delay" >/dev/ttyRPMSG0

         On reception of this message, CM4 waits for 20 seconds before sending a message
         to CA7 which will activate Exti line 61 (IPCC interrupt CPU1)

    2.2 - Move CA7 in CStop mode before 20 seconds delay expiration
          > systemctl suspend

          In that case, this command moves CA7 in CStop mode keeping System on Run Mode
          as CM4 is still on CRun
          LED8 stops toggling (Linux heartbeat)

    2.3 - Move CA7 in CRun mode using Exti line 61 (IPCC interrupt CPU1)
          After a 20 second delay, you get "*delay" in Linux console as configured 
          in step 2.1

          LED8 toggles (Linux heartbeat)

    Note: you can check CM4 logs :
          > cat /sys/kernel/debug/remoteproc/remoteproc0/trace0


3) System Stop Mode with CA7 in CStop and CM4 in CStop - CA7 wakes up first
   -----------------------------------------------------------------------
    Objective: Testing System Stop Mode with CA7 in charge of re-configuring
               oscillators PLL3/PLL4, MCU Clock Mux and MCU DIV prescaller
               CA7 wakes up with Wake up button which raises Exti line WKUP1 (PIN PA0)

    3.0 - CA7 firmware has configured Exti line WKUP1 as wake up source
          CM4 firmware has configured Exti line 62 (IPCC interrupt CPU2) as a wake up source

    3.1 - Move CM4 in CStop mode
          > echo "*stop" >/dev/ttyRPMSG0

          On reception of this message, CM4 backs up PLL3/PLL4 and MCU clock
          configuration. Finally MCU calls HAL_PWR_EnterSTOPMode(PWR_MAINREGULATOR_ON,
          PWR_STOPENTRY_WFI) and goes into CStop mode.
          LED7 stops toggling as CM4 subsystem peripherals clock is stalled and therefore
          ADC conversions are stopped

    3.2 - Move CA7 in CStop mode
          > systemctl suspend

          In that case, this command moves CA7 in CStop mode  and we enter in System Stop Mode
          as CM4 is in CStop.
          LED8 stops toggling (Linux heartbeat)

    3.3 - Move CA7 in CRun mode using Wake up button which raises Exti line WKUP1 (PIN PA0)

          CA7 firmware re-configures oscillators PLL3/PLL4, MCU Clock Mux, MCU DIV prescaller
          LED8 toggles (Linux heartbeat)

    3.4 - Move CM4 in CRun mode using Exti line 62 (IPCC interrupt CPU2)
          > echo "wakeup" >/dev/ttyRPMSG0
          Sending a new message wakes up CM4 with Exti line 62 (IPCC interrupt CPU2)

          CA7 firmware has re-configured oscillators PLL3/PLL4, MCU Clock Mux, MCU DIV prescaller
          in step 3.3.
          Thus, LED7 toggles as CM4 subsystem peripherals clock is resumed
          and therefore ADC conversions are resumed

    Note: you can check CM4 logs :
          > cat /sys/kernel/debug/remoteproc/remoteproc0/trace0

    Note: As system was on platform STOP mode CM4 will try to restore PLL3/PLL4, MCU
          Clock Mux and MCU DIV prescaller after waking up. This reconfiguration
          doesn't disturb previous CA7 configuration.

4) System Stop Mode with CA7 in CStop and CM4 in CStop - CM4 wakes up first
   -----------------------------------------------------------------------
    Objective: Testing System Stop Mode with CM4 in charge of re-configuring
               oscillators PLL3/PLL4, MCU Clock Mux and MCU DIV prescaller
               CA7 wakes up with Wake up button which raises Exti line WKUP1 (PIN PA0)


    4.0 - CA7 firmware has configured Exti line WKUP1 as wake up source
          CM4 firmware has configured Exti line 62 (IPCC interrupt CPU2) as a wake up source

    4.1 - Move CM4 in CStop mode
          > echo "*stop" >/dev/ttyRPMSG0

          On reception of this message, CM4 backs up PLL3/PLL4 and MCU clock
          configuration. Finally MCU calls HAL_PWR_EnterSTOPMode(PWR_MAINREGULATOR_ON,
          PWR_STOPENTRY_WFI) and goes into CStop mode.
          LED7 stops toggling as CM4 subsystem peripherals clock is stalled and therefore
          ADC conversions are stopped

    4.2 - Move CA7 in CStop mode
          > systemctl suspend

          In that case, this command moves CA7 in CStop mode and we enter in System Stop Mode
          as CM4 is in CStop.
          LED8 stops toggling (Linux heartbeat)

    4.3 - Move CM4 in CRun mode using User push button (PA14)

          CM4 firmware re-configures oscillators PLL3/PLL4 (if allocated to CM4),
          MCU Clock Mux and MCU DIV prescaller.
          Thus, LED7 toggles quickly and therefore ADC conversions are resumed
          If PLL3 restore was not done, LED7 would toggle slowly as timer clock will be
          slower as before (based on HSI instead of PLL3)

    4.4 - Move CA7 in CRun mode using Wake up button which raises Exti line WKUP1 (PIN PA0)

          LED8 toggles (Linux heartbeat)

    Note: you can check CM4 logs :
          > cat /sys/kernel/debug/remoteproc/remoteproc0/trace0

    Note: As system was on System STOP mode, CA7 will try to restore PLL3/PLL4, MCU
          Clock Mux and MCU DIV prescaller after waking up. This reconfiguration
          doesn't disturb previous CM4 configuration.


5) System Standby Mode
   -------------------
    Objective: Testing Standby Mode with CA7 in charge of re-configuring SOC.
               CA7 wakes up with Wake up button WKUP1 pin (PIN PA0)
               !!!NOTE!!!: after this test 5), there is no more M4 firmware running.

    5.0 - CA7 firmware has configured WKUP1 as wake up source. Make sure
          that there is no wakeup source configured which will forbid standby mode (Eg.: IPCC wake up).
          Run this command:
          > echo disabled > /sys/devices/platform/soc/4c001000.mailbox/power/wakeup

    5.1 - Move CM4 in CStop mode allowing Standby System Mode
          > echo "*standby" >/dev/ttyRPMSG0

          On reception of this message, CM4 calls HAL_PWR_EnterSTANDBYMode()
          and goes into CStop mode allowing System Standby Mode.
          LED7 stops toggling as CM4 subsystem peripherals clock is stalled and therefore
          ADC conversions are stopped

    5.2 - Move CA7 in CStop mode allowing Standby System Mode
          > systemctl suspend

          In that case, this command moves CA7 in CStop mode allowing System
          Standby Mode.
          LED8 stops toggling (Linux heartbeat).
          System enters into System Standby Mode.
          VDD is off

    5.3 - Move CA7 in CRun mode using Wake up button WKUP1 pin (PIN PA0)

          WKUP1 pin wakes up system. A system reset is generated and CA7 firmware
          restarts from scratch.

    Note: After reset on console you'll see "Reset reason (0x810)" and "System
          exits from STANDBY" messages, showing system was on System Standby mode.


Connection needed:
	None, if ADC channel and DAC channel are selected on the same GPIO.
	Otherwise, connect a wire between DAC channel output and ADC input.

Other peripherals used:
  1 GPIO for LED
  DAC
  1 GPIO for push button
  DMA
  Timer

Board settings:
 - ADC is configured to convert ADC2_CHANNEL_16.
 - The voltage input on ADC channel is provided from DAC (DAC_CHANNEL_1).
   Same pin is used, thus no connection is required, it is done internally.
 - Voltage is increasing at each click on User push-button, from 0 to
   maximum range in 4 steps. Clicks on User push-button follow circular cycles:
   At clicks counter maximum value reached, counter is set back to 0.bu


STM32MP157C-DK2 board LED7 is be used to monitor the program execution status:
 - Normal operation: LED7 is turned-on/off in function of ADC conversion
   result.
    - Toggling: "On" upon conversion completion (full DMA buffer filled)
                "Off" upon half conversion completion (half DMA buffer filled)
 - Error: In case of error, LED7 is toggling twice at a frequency of 1Hz.


@note Care must be taken when using HAL_Delay(), this function provides accurate
      delay (in milliseconds) based on a variable incremented in SysTick ISR.
      This implies that if HAL_Delay() is called from a peripheral ISR process, then
      the HAL time base interrupt must have higher priority (numerically lower) than
      the peripheral interrupt. Otherwise the caller ISR process will be blocked.
      To change the HAL time base interrupt priority you have to use HAL_NVIC_SetPriority()
      function.
      In STM32Cube firmware packages, the SysTick timer is used as default time base,
      but it can be changed by user by utilizing other time base IPs such as a
      general-purpose timer, keeping in mind that the time base duration must be
      kept at 1/10/100 ms since all PPP_TIMEOUT_VALUEs are defined and handled
      in milliseconds. Functions affecting time base configurations are declared
      as __Weak to allow different implementations in the user file.

@note The application needs to ensure that the HAL time base is always set to 1 millisecond
      to have correct HAL operation.


@par Directory contents
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/main.h                 Main program header file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/mbox_ipcc.h            mailbox_ipcc_if.c MiddleWare configuration header file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/openamp.h              User OpenAMP init header file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/openamp_conf.h         Configuration file for OpenAMP MW
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/rsc_table.h            Resource_table for OpenAMP header file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/stm32mp1xx_hal_conf.h  HAL Library Configuration file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/stm32mp1xx_it.h        Interrupt handlers header file
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/main.c                 Main program
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/mbox_ipcc.c            mailbox_ipcc_if.c MiddleWare configuration
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/openamp.c              User OpenAMP init
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/rsc_table.c            Resource_table for OpenAMP
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/stm32mp1xx_it.c        Interrupt handlers
    - OpenAMP/OpenAMP_TTY_echo_wakeup/Src/system_stm32mp1xx.c    STM32MP1xx system clock configuration file


@par Hardware and Software environment

  - This example runs on STM32MP157CACx devices.

  - This example has been tested with STM32MP157C-DK2 board and can be
    easily tailored to any other supported device and development board.

@par How to use it ?

In order to make the program work, you must do the following:
 - Open your preferred toolchain
 - Rebuild all files and load your image into target memory
 - Run the example


 * <h3><center>&copy; COPYRIGHT STMicroelectronics</center></h3>
 */
