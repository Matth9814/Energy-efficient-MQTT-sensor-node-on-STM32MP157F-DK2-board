################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (10.3-2021.10)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
/home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco.c \
/home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco_bus.c \
/home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco_stpmic1.c 

OBJS += \
./Drivers/BSP/stm32mp15xx_disco.o \
./Drivers/BSP/stm32mp15xx_disco_bus.o \
./Drivers/BSP/stm32mp15xx_disco_stpmic1.o 

C_DEPS += \
./Drivers/BSP/stm32mp15xx_disco.d \
./Drivers/BSP/stm32mp15xx_disco_bus.d \
./Drivers/BSP/stm32mp15xx_disco_stpmic1.d 


# Each subdirectory must supply rules for building sources it contributes
Drivers/BSP/stm32mp15xx_disco.o: /home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco.c Drivers/BSP/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DCORE_CM4 -DUSE_FULL_LL_DRIVER -DNO_ATOMIC_64_SUPPORT -DUSE_HAL_DRIVER -DSTM32MP157Cxx -DMETAL_INTERNAL -DMETAL_MAX_DEVICE_REGIONS=2 -DVIRTIO_SLAVE_ONLY -D__LOG_TRACE_IO_ -c -I../../../Inc -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -I../../../../../../../../Drivers/BSP/STM32MP15xx_DISCO -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc/Legacy -I../../../../../../../../Drivers/CMSIS/Device/ST/STM32MP1xx/Include -I../../../../../../../../Drivers/CMSIS/Include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -Og -ffunction-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"
Drivers/BSP/stm32mp15xx_disco_bus.o: /home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco_bus.c Drivers/BSP/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DCORE_CM4 -DUSE_FULL_LL_DRIVER -DNO_ATOMIC_64_SUPPORT -DUSE_HAL_DRIVER -DSTM32MP157Cxx -DMETAL_INTERNAL -DMETAL_MAX_DEVICE_REGIONS=2 -DVIRTIO_SLAVE_ONLY -D__LOG_TRACE_IO_ -c -I../../../Inc -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -I../../../../../../../../Drivers/BSP/STM32MP15xx_DISCO -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc/Legacy -I../../../../../../../../Drivers/CMSIS/Device/ST/STM32MP1xx/Include -I../../../../../../../../Drivers/CMSIS/Include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -Og -ffunction-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"
Drivers/BSP/stm32mp15xx_disco_stpmic1.o: /home/matteo/STM32MPU_workspace/STM32MP1-Ecosystem-v5.0.0/Developer-Package/STM32Cube_FW_MP1_V1.6.0/Drivers/BSP/STM32MP15xx_DISCO/stm32mp15xx_disco_stpmic1.c Drivers/BSP/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DCORE_CM4 -DUSE_FULL_LL_DRIVER -DNO_ATOMIC_64_SUPPORT -DUSE_HAL_DRIVER -DSTM32MP157Cxx -DMETAL_INTERNAL -DMETAL_MAX_DEVICE_REGIONS=2 -DVIRTIO_SLAVE_ONLY -D__LOG_TRACE_IO_ -c -I../../../Inc -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -I../../../../../../../../Drivers/BSP/STM32MP15xx_DISCO -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc -I../../../../../../../../Drivers/STM32MP1xx_HAL_Driver/Inc/Legacy -I../../../../../../../../Drivers/CMSIS/Device/ST/STM32MP1xx/Include -I../../../../../../../../Drivers/CMSIS/Include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/open-amp/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/libmetal/lib/include -I../../../../../../../../Middlewares/Third_Party/OpenAMP/virtual_driver -Og -ffunction-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Drivers-2f-BSP

clean-Drivers-2f-BSP:
	-$(RM) ./Drivers/BSP/stm32mp15xx_disco.cyclo ./Drivers/BSP/stm32mp15xx_disco.d ./Drivers/BSP/stm32mp15xx_disco.o ./Drivers/BSP/stm32mp15xx_disco.su ./Drivers/BSP/stm32mp15xx_disco_bus.cyclo ./Drivers/BSP/stm32mp15xx_disco_bus.d ./Drivers/BSP/stm32mp15xx_disco_bus.o ./Drivers/BSP/stm32mp15xx_disco_bus.su ./Drivers/BSP/stm32mp15xx_disco_stpmic1.cyclo ./Drivers/BSP/stm32mp15xx_disco_stpmic1.d ./Drivers/BSP/stm32mp15xx_disco_stpmic1.o ./Drivers/BSP/stm32mp15xx_disco_stpmic1.su

.PHONY: clean-Drivers-2f-BSP

