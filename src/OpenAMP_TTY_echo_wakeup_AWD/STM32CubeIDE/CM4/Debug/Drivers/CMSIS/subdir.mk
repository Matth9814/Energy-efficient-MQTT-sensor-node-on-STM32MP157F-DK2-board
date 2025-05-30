################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (10.3-2021.10)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
/home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Projects/STM32MP157C-DK2/Applications/OpenAMP/OpenAMP_TTY_echo_wakeup_AWD/Src/system_stm32mp1xx.c 

OBJS += \
./Drivers/CMSIS/system_stm32mp1xx.o 

C_DEPS += \
./Drivers/CMSIS/system_stm32mp1xx.d 


# Each subdirectory must supply rules for building sources it contributes
Drivers/CMSIS/system_stm32mp1xx.o: /home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Projects/STM32MP157C-DK2/Applications/OpenAMP/OpenAMP_TTY_echo_wakeup_AWD/Src/system_stm32mp1xx.c Drivers/CMSIS/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DCORE_CM4 -DUSE_FULL_LL_DRIVER -DNO_ATOMIC_64_SUPPORT -DUSE_HAL_DRIVER -DSTM32MP157Cxx -DMETAL_INTERNAL -DMETAL_MAX_DEVICE_REGIONS=2 -DVIRTIO_SLAVE_ONLY -D__LOG_TRACE_IO_ -c -I../../../Inc -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -I../../../../../../../../Drivers/BSP/STM32MP15xx_DISCO -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc/Legacy -I../../../../../../../../Drivers/CMSIS/Device/ST/STM32MP1xx/Include -I../../../../../../../../Drivers/CMSIS/Include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -Og -ffunction-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Drivers-2f-CMSIS

clean-Drivers-2f-CMSIS:
	-$(RM) ./Drivers/CMSIS/system_stm32mp1xx.cyclo ./Drivers/CMSIS/system_stm32mp1xx.d ./Drivers/CMSIS/system_stm32mp1xx.o ./Drivers/CMSIS/system_stm32mp1xx.su

.PHONY: clean-Drivers-2f-CMSIS

