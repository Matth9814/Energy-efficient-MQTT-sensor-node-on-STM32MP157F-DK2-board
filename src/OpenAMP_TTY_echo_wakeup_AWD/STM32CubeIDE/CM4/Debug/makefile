################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (10.3-2021.10)
################################################################################

-include ../makefile.init

RM := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include Middlewares/OpenAMP/virtual_driver/subdir.mk
-include Middlewares/OpenAMP/open-amp/virtio/subdir.mk
-include Middlewares/OpenAMP/open-amp/rpmsg/subdir.mk
-include Middlewares/OpenAMP/open-amp/remoteproc/subdir.mk
-include Middlewares/OpenAMP/libmetal/generic/template/subdir.mk
-include Middlewares/OpenAMP/libmetal/generic/subdir.mk
-include Middlewares/OpenAMP/libmetal/subdir.mk
-include Drivers/STM32MP1xx_HAL_Driver/subdir.mk
-include Drivers/CMSIS/subdir.mk
-include Drivers/BSP/subdir.mk
-include Application/User/subdir.mk
-include Application/Startup/subdir.mk
-include objects.mk

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(S_DEPS)),)
-include $(S_DEPS)
endif
ifneq ($(strip $(S_UPPER_DEPS)),)
-include $(S_UPPER_DEPS)
endif
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
endif

-include ../makefile.defs

OPTIONAL_TOOL_DEPS := \
$(wildcard ../makefile.defs) \
$(wildcard ../makefile.init) \
$(wildcard ../makefile.targets) \


BUILD_ARTIFACT_NAME := OpenAMP_TTY_echo_wakeup_CM4
BUILD_ARTIFACT_EXTENSION := elf
BUILD_ARTIFACT_PREFIX :=
BUILD_ARTIFACT := $(BUILD_ARTIFACT_PREFIX)$(BUILD_ARTIFACT_NAME)$(if $(BUILD_ARTIFACT_EXTENSION),.$(BUILD_ARTIFACT_EXTENSION),)

# Add inputs and outputs from these tool invocations to the build variables 
EXECUTABLES += \
OpenAMP_TTY_echo_wakeup_CM4.elf \

MAP_FILES += \
OpenAMP_TTY_echo_wakeup_CM4.map \

SIZE_OUTPUT += \
default.size.stdout \

OBJDUMP_LIST += \
OpenAMP_TTY_echo_wakeup_CM4.list \

OBJCOPY_HEX += \
OpenAMP_TTY_echo_wakeup_CM4.hex \


# All Target
all: main-build

# Main-build Target
main-build: OpenAMP_TTY_echo_wakeup_CM4.elf secondary-outputs

# Tool invocations
OpenAMP_TTY_echo_wakeup_CM4.elf OpenAMP_TTY_echo_wakeup_CM4.map: $(OBJS) $(USER_OBJS) ../stm32mp15xx_m4.ld makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-gcc -o "OpenAMP_TTY_echo_wakeup_CM4.elf" @"objects.list" $(USER_OBJS) $(LIBS) -mcpu=cortex-m4 -T"../stm32mp15xx_m4.ld" --specs=nosys.specs -Wl,-Map="OpenAMP_TTY_echo_wakeup_CM4.map" -Wl,--gc-sections -static --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -Wl,--start-group -lc -lm -Wl,--end-group
	@echo 'Finished building target: $@'
	@echo ' '

default.size.stdout: $(EXECUTABLES) makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-size  $(EXECUTABLES)
	@echo 'Finished building: $@'
	@echo ' '

OpenAMP_TTY_echo_wakeup_CM4.list: $(EXECUTABLES) makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-objdump -h -S $(EXECUTABLES) > "OpenAMP_TTY_echo_wakeup_CM4.list"
	@echo 'Finished building: $@'
	@echo ' '

OpenAMP_TTY_echo_wakeup_CM4.hex: $(EXECUTABLES) makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-objcopy  -O ihex $(EXECUTABLES) "OpenAMP_TTY_echo_wakeup_CM4.hex"
	@echo 'Finished building: $@'
	@echo ' '

# Other Targets
clean:
	-$(RM) OpenAMP_TTY_echo_wakeup_CM4.elf OpenAMP_TTY_echo_wakeup_CM4.hex OpenAMP_TTY_echo_wakeup_CM4.list OpenAMP_TTY_echo_wakeup_CM4.map default.size.stdout
	-@echo ' '

secondary-outputs: $(SIZE_OUTPUT) $(OBJDUMP_LIST) $(OBJCOPY_HEX)

fail-specified-linker-script-missing:
	@echo 'Error: Cannot find the specified linker script. Check the linker settings in the build configuration.'
	@exit 2

warn-no-linker-script-specified:
	@echo 'Warning: No linker script specified. Check the linker settings in the build configuration.'

.PHONY: all clean dependents main-build fail-specified-linker-script-missing warn-no-linker-script-specified

-include ../makefile.targets
