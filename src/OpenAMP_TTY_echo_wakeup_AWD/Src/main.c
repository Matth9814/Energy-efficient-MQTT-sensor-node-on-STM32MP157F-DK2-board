/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    OpenAMP/OpenAMP_TTY_echo_wakeup/Inc/main.c
  * @author  MCD Application Team
  * @brief   Main program body.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2021 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef enum{
	ERR = -1,
	THR,
	DATA_ACK,
	WAIT_THR,
	WAIT_SUSP
} Msg_t;

typedef uint32_t sensorData_t;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* Data transmission constants */
#define MAX_BUFFER_SIZE 			RPMSG_BUFFER_SIZE
#define MAX_ADC_BUFFER_SIZE 		8
#define MIN_TRANSM_ELEMS 			1

/* Time to wait before transmitting when A7 is suspending */
#define WAIT_SUSP_DATA				10000 // unit: ms
#define WAIT_SUSP_NODATA			5000 // unit: ms

/* ADC AWD constants */
#define DEFAULT_THR_HIGH           (__LL_ADC_DIGITAL_SCALE(LL_ADC_RESOLUTION_12B) * 5 /8) /* Threshold high: 5/8 of full range (4095 <=> Vdda=2.9V): 2559 <=> 2.06V */
#define DEFAULT_THR_LOW            (__LL_ADC_DIGITAL_SCALE(LL_ADC_RESOLUTION_12B) * 1 /8) /* Threshold low: 1/8 of full range (4095 <=> Vdda=2.9V): 512 <=> 0.41V */


#define MSG_STOP "*stop"
#define MSG_STANDBY "*standby"
#define MSG_DELAY "*delay"
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
IPCC_HandleTypeDef hipcc;
DAC_HandleTypeDef hdac1;
TIM_HandleTypeDef htim2;

/* USER CODE BEGIN PV */
/* Private variables ---------------------------------------------------------*/
/* EXTI handler declaration */
EXTI_HandleTypeDef hexti14;
/* ADC handler declaration */
ADC_HandleTypeDef    hadc2;
/* RCC MCU clock configuration backup variable */
RCC_MCUInitTypeDef  RCC_MCUInit;
/* RCC Peripheral clock configuration backup variable*/
RCC_PeriphCLKInitTypeDef  PeriphClk;

/* ADC data variable */
__IO sensorData_t ADCxData;

/* ADC data buffer */
sensorData_t ADCxDataBuffer[MAX_ADC_BUFFER_SIZE];
__IO uint16_t OutOfWindowData = 0;		// Points to the first free slot (#elements in the buffer)
//const uint8_t delimADCdata = ';';
// Flags that the previously sent out of window data have already been processed
__IO FlagStatus prevTrProcessed = SET;

/* ADC Analog Watchdogs and threshold management variables */
ADC_AnalogWDGConfTypeDef AnalogWDGConfig = {0};
uint32_t highThr = (__LL_ADC_DIGITAL_SCALE(LL_ADC_RESOLUTION_12B) * 0);
uint32_t lowThr = (__LL_ADC_DIGITAL_SCALE(LL_ADC_RESOLUTION_12B) * 0);
const char delimThr = ';'; // Thresholds delimiter when received as single string

/* A7-M4 messages */
const char* thrSet_ack = "thr_Set";			// The thresholds are correctly set [to A7]
const char* thrWait_msg = "thr_Wait";		// Start listening for new thresholds [from A7]
const char* trProc_ack = "tr_Rdy";			// Can send new out window data [from A7]
const char* waitSusp_msg = "susp_Wait";		/* A7 is starting the suspension procedure,
 	 	 	 	 	 	 	 	 	 	 	   do not send any more data [from A7]*/
const char* rdy_msg = "op_Rdy";             /* Signals the A7 that there are no new data to
 	 	 	 	 	 	 	 	 	 	 	   read so it can proceed [to A7] */

/* Variable to manage push button on board: interface between ExtLine interruption and main program */
__IO FlagStatus ubUserButtonClickEvent = RESET;  /* Event detection: Set after User Button interrupt */

/* Virtual UART */
VIRT_UART_HandleTypeDef huart0;

__IO FlagStatus VirtUart0RxMsg = RESET;
uint8_t VirtUart0ChannelBuffRx[MAX_BUFFER_SIZE];
uint16_t VirtUart0ChannelRxSize = 0;

/* Power management */
uint16_t Shutdown_Req = 0;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_IPCC_Init(void);
static void MX_DAC1_Init(void);
static void MX_TIM2_Init(void);

/* USER CODE BEGIN PFP */
/* Private function prototypes -----------------------------------------------*/
static void EXTI14_IRQHandler_Config(void);
static void Exti14FallingCb(void);
static void Configure_ADC(void);
static void Generate_waveform_SW_update_Config(void);
static void Generate_waveform_SW_update(void);
static HAL_StatusTypeDef RCC_restoreClocks(void);
static void RCC_backupClocks(void);

void VIRT_UART0_RxCpltCallback(VIRT_UART_HandleTypeDef *huart);
void Check_Delay(uint8_t *BuffRx, uint16_t BuffSize);
void Check_Sleep(uint8_t *BuffRx);
Msg_t ParseMsg(uint8_t *msg);
void ConfigPVD(void);
void HAL_PWR_PVDCallback(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */
  EXTI_ConfigTypeDef EXTI_ConfigStructure;
  /* EXTI handler declaration */
  EXTI_HandleTypeDef hexti62;
  /* Debug variable for VIRT_UART transmission */
  VIRT_UART_StatusTypeDef res;
  /* Return value of message parsing */
  Msg_t msgType;
  /* Transmissions suspension after "waitSusp_msg" */
  uint32_t waitSuspTime;

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initialize the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */
  if(IS_ENGINEERING_BOOT_MODE())
  {
	/* Configure the system clock */
    SystemClock_Config();

    /* Configure PMIC */
    BSP_PMIC_Init();
    BSP_PMIC_InitRegulators();

    /* Configure VREFBUF */
    __HAL_RCC_VREF_CLK_ENABLE();
    HAL_SYSCFG_VREFBUF_HighImpedanceConfig(SYSCFG_VREFBUF_HIGH_IMPEDANCE_DISABLE);
    HAL_SYSCFG_EnableVREFBUF();
  }

  log_info("Cortex-M4 boot successful with STM32Cube FW version: v%ld.%ld.%ld \r\n",
                                            ((HAL_GetHalVersion() >> 24) & 0x000000FF),
                                            ((HAL_GetHalVersion() >> 16) & 0x000000FF),
                                            ((HAL_GetHalVersion() >> 8) & 0x000000FF));
  /* USER CODE END Init */

  /* IPCC initialisation */
   MX_IPCC_Init();
  /* OpenAmp initialisation ---------------------------------*/
  MX_OPENAMP_Init(RPMSG_REMOTE, NULL);

  /* Shutdown mechanism initialisation  */
  CoproSync_Init();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_DAC1_Init();
  //MX_TIM2_Init();
  /* USER CODE BEGIN 2 */
  /*
   * Create Virtual UART device
   * defined by a rpmsg channel attached to the remote device
   */
  log_info("Virtual UART0 OpenAMP-rpmsg channel creation\r\n");
  if (VIRT_UART_Init(&huart0) != VIRT_UART_OK) {
    log_err("VIRT_UART_Init UART0 failed.\r\n");
    Error_Handler();
  }

  /*Need to register callback for message reception by channels*/
  if(VIRT_UART_RegisterCallback(&huart0, VIRT_UART_RXCPLT_CB_ID, VIRT_UART0_RxCpltCallback) != VIRT_UART_OK)
  {
   Error_Handler();
  }

  /* Wait for the endpoint to have both the local address and the destination address set.
   * In that case it is ready to send. */
  log_info("Waiting for ADC monitored window thresholds\n");
  log_info("Format: <low_thr>;<high_thr> (unit: mVolts)\n");
  log_info("ADC resolution: 12 bits\n");
  log_info("ADC reference voltage: %lu\n",VDDA_APPLI);
  log_dbg("Send a message on /dev/ttyRPMsgx to let the M4 know the A7 RPMsg address\n");
  OPENAMP_Wait_EndPointready(&huart0.ept);
  VirtUart0RxMsg = RESET;
  /* If the initialization is not performed correctly the following M4-A7 interactions will
   * probably cause the system to hang or not work as expected. */
  if(ParseMsg(VirtUart0ChannelBuffRx) != THR){Error_Handler();}
  log_dbg("Initializing threshold values\n");
  /* highThr = lowThr = 0 in case the string is not formatted correctly, hence 0;0
   * is not considered a valid couple of inputs */

  /* Initialize LED on board */
  BSP_LED_Init(LED7);
  BSP_LED_Init(LED5);
  /*
   * -2- Configure EXTI14 (connected to PA.14 pin) in interrupt mode.
   * It could be used to wakeup the M4 from CStop mode when user button
   * is pressed.
   */
  EXTI14_IRQHandler_Config();

  /*
   * -3- Set configuration of Exti line 62 (IPCC interrupt CPU2). It could be used to wakeup the
   * M4 from CStop mode when RPMsg received from Cortex-A7
   */
  EXTI_ConfigStructure.Line = EXTI_LINE_62;
  EXTI_ConfigStructure.Mode = EXTI_MODE_C2_INTERRUPT;
  PERIPH_LOCK(EXTI);
  HAL_EXTI_SetConfigLine(&hexti62, &EXTI_ConfigStructure);
  PERIPH_UNLOCK(EXTI);
  
  /* Configure ADC */
  /* Note: This function configures the ADC but does not enable it.           */
  /*       Only ADC internal voltage regulator is enabled by function         */
  /*       "HAL_ADC_Init()".                                                  */
  /*       To activate ADC (ADC enable and ADC conversion start), use         */
  /*       function "HAL_ADC_Start_xxx()".                                    */
  /*       This is intended to optimize power consumption:                    */
  /*       1. ADC configuration can be done once at the beginning             */
  /*          (ADC disabled, minimal power consumption)                       */
  /*       2. ADC enable (higher power consumption) can be done just before   */
  /*          ADC conversions needed.                                         */
  /*          Then, possible to perform successive ADC activation and         */
  /*          deactivation without having to set again ADC configuration.     */
  Configure_ADC();
  log_info("Initial ADC threshold values: [High] %u | [Low] %u\n", (unsigned int) AnalogWDGConfig.HighThreshold, (unsigned int) AnalogWDGConfig.LowThreshold );

  /* Run the ADC linear calibration in single-ended mode */
  if (HAL_ADCEx_Calibration_Start(&hadc2,ADC_CALIB_OFFSET_LINEARITY, ADC_SINGLE_ENDED) != HAL_OK)
  {
    /* Calibration Error */
    Error_Handler();
  }

  /* Configure the DAC peripheral and generate a constant voltage of Vdda/2.  */
  /* The DAC is set to a value and then started
   * (check stm32mp1xx_hal_dac.c for more info on operational modes) */
  Generate_waveform_SW_update_Config();

  log_info("Starting DAC value: %u\n",(unsigned int) HAL_DAC_GetValue(&hdac1,DAC_CHANNEL_1));

  /*## Enable Timer ########################################################*/
  /*if (HAL_TIM_Base_Start(&htim2) != HAL_OK)
  {
    // Counter enable error
    Error_Handler();
  }*/
  
  /*## Enable PVD ###############################################*/
  /* TODO: The system goes in hard fault when it tries to write the PWR register
   * to enable/configure the PVD */
  //HAL_PWR_EnablePVD();

  /*## Configure PVD ###############################################*/
  //ConfigPVD();

    /*## Start ADC conversions ###############################################*/
  /* Start ADC group regular conversion*/
  if (HAL_ADC_Start(&hadc2) != HAL_OK)
  {
    /* ADC conversion start error */
    Error_Handler();
  }  

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (!Shutdown_Req)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	OPENAMP_check_for_message();
	/* Message received */
    /*if (VirtUart0RxMsg) {
      VirtUart0RxMsg = RESET;
      Check_Delay(VirtUart0ChannelBuffRx, VirtUart0ChannelRxSize);
      VIRT_UART_Transmit(&huart0, VirtUart0ChannelBuffRx, VirtUart0ChannelRxSize);
      Check_Sleep(VirtUart0ChannelBuffRx);
    }*/
	if (VirtUart0RxMsg) {
	  VirtUart0RxMsg = RESET;
	  msgType = ParseMsg(VirtUart0ChannelBuffRx);
	  //log_dbg("msgType: %d\n",msgType);
	  switch(msgType){
	  	case THR: // Set new thresholds
			log_dbg("Setting new thresholds\n");
			HAL_ADC_Stop(&hadc2);
			// Other parameters were already set in ConfigureADC()
			AnalogWDGConfig.HighThreshold = highThr;
			AnalogWDGConfig.LowThreshold = lowThr;
			log_info("New ADC threshold values: [High] %u | [Low] %u\n", (unsigned int) AnalogWDGConfig.HighThreshold, (unsigned int) AnalogWDGConfig.LowThreshold );
			if (HAL_ADC_AnalogWDGConfig(&hadc2, &AnalogWDGConfig) != HAL_OK) {Error_Handler();}
			// Send acknowledge to A7 after correctly setting the thresholds
			/* This acknowledge is needed to prevent the A7 from sending multiple thresholds
			 * in sequence, potentially breaking the execution flow.
			 * This solution seems more clean and user friendly (supposing the user is not interacting directly with the M4)
			 * than simply deactivating the VIRT_UART rx interrupts while setting the new threshold.
			 * Moreover, it is very useful to signal to the A7 a problem with the threshold setup instead
			 * of just entering the error handler and doing nothing. This solution allows to forward the error
			 * to a user that may not directly access the board to check its status.
			 * NOTE: a possible better and more general solution to signal a problem of the M4 could be to
			 * send some kind of error message to the A7 directly in the error handler. Obviously, a suitable
			 * protocol that correctly interacts with other A7-M4 communications has to be defined. */
			if(VIRT_UART_Transmit(&huart0, thrSet_ack, strlen(thrSet_ack)) != VIRT_UART_OK)
			  {Error_Handler();}
			if (HAL_ADC_Start(&hadc2) != HAL_OK) {Error_Handler();}
			break;
	  	case DATA_ACK: // Ack from A7 (out of window data processed)
	  		prevTrProcessed = SET;
	  		break;
	  	case WAIT_THR: // Listen for threshold (no transmission to A7)
	  		if(prevTrProcessed == SET){ // There are no unprocessed data
	  		  if(VIRT_UART_Transmit(&huart0, rdy_msg, strlen(rdy_msg)) != VIRT_UART_OK)
	  		  	  {Error_Handler();}
	  		  prevTrProcessed = RESET; // Stop the M4 from sending new data
	  		}
	  		break;
	  	case WAIT_SUSP:
	  		if(prevTrProcessed == SET){ // There are no unprocessed data
	  		  if(VIRT_UART_Transmit(&huart0, rdy_msg, strlen(rdy_msg)) != VIRT_UART_OK)
	  			{Error_Handler();}
	  		  prevTrProcessed = RESET; // Stop the M4 from sending new data
	  		  waitSuspTime = WAIT_SUSP_NODATA;
	  		} else {
	  		  /* There are data on the channel so the CM4 inactivity interval is reset */
	  		  break;
	  		}
	  		/* Differently from the WAIT_THR case, the M4 does not wait for a message from the A7,
	  		 * so it needs another way to re-enable the out of window data transmission. This is
	  		 * simply done by waiting some time. */
	  		/* TODO: This can be done more effectively with a timer since it would not stop the MCU */
	  		//log_dbg("Waiting for MPU suspension\n");
	  		HAL_Delay(waitSuspTime);
	  		//log_dbg("Resuming normal activity\n");
	  		prevTrProcessed = SET;
	  		break;
	  	default: // ERR
	  		// Syntax reference: https://stackoverflow.com/questions/256218/the-simplest-way-of-printing-a-portion-of-a-char-in-c
	  		log_err("Invalid (%.*s) message received\n",MAX_BUFFER_SIZE,VirtUart0ChannelBuffRx);
	  }
	}

	/* Value out of window*/
	/* Before transmitting check that:
	 * - Any previous transmission has already been processed
	 * - The number of elements in the buffer is >= than the minimum number of elements
	 * allowed in a single transmission. */
	if (OutOfWindowData > MIN_TRANSM_ELEMS-1 && prevTrProcessed == SET){
	    /* The ADC is stopped so that AWD interruptions do not interfere with the data transmission.
		 * This does not need to be done before checking the number of elements in the buffer. In fact,
		 * even if an OutOfWindow callback were to be called the number of elements would increase, not
		 * decrease. */
		HAL_ADC_Stop(&hadc2);
		//log_dbg("Starting out of window values transmission\n");
		// Out of window data (uint32_t ADCxData) sent to the A7
		/* Mark as not processed before actually transmitting to avoid the A7 acknowledge to arrive
		 * before setting the transmission as not processed. */
		prevTrProcessed = RESET;
		res = VIRT_UART_Transmit(&huart0, ADCxDataBuffer, OutOfWindowData*sizeof(sensorData_t));
		if(res != VIRT_UART_OK){
			log_err("Error during out of window values transmission\n");
			/* Check the 'res' variable inside VIRT_UART_Transmit and the error macros in
			 * rpmsg.h to know the nature of the problem */
		}

		//HAL_Delay(500); // To slow the transmission rate if it's too fast

		// Buffer variables update
		OutOfWindowData = 0;
		//BSP_LED_Off(LED7);
		if (HAL_ADC_Start(&hadc2) != HAL_OK) {Error_Handler();}
    }

    /* Note: Variable "ubUserButtonClickEvent" is set into push button        */
    /*       IRQ handler, refer to function "Exti14FallingCb()".       */
    if ((ubUserButtonClickEvent) == SET)
    {
      /* Modifies modifies the voltage level, to generate a waveform circular,  */
      /* shape of ramp: Voltage is increasing at each press on push button,     */
      /* from 0 to maximum range (Vdda) in 4 steps, then starting back from 0V. */
      /* Voltage is updated incrementally at each call of this function.        */
      Generate_waveform_SW_update();

      /* Reset variable for next loop iteration (with debounce) */
      HAL_Delay(200);

      log_info("New DAC value: %u\n",(unsigned int) HAL_DAC_GetValue(&hdac1,DAC_CHANNEL_1));

      ubUserButtonClickEvent = RESET;
    }

    /* The M4 does not go to sleep when:
     * - It is waiting an acknowledge from the A7:
     * 		this happens after sending data or while waiting for a new threshold
     * - It needs to send new data
     * The communication is asynchronous so it may still be convenient to sleep while
     * waiting for the ack/threhsold. */
    if(prevTrProcessed == SET && OutOfWindowData < MIN_TRANSM_ELEMS){
		// Enter CSleep state until an interrupt wakes up the CM4
		log_info("Going to sleep...\n");
		/* Turn off the SysTick interrupt to avoid immediately exiting CSleep*/
		HAL_SuspendTick();
		//SysTick->CTRL &= ~(SysTick_CTRL_ENABLE_Msk << SysTick_CTRL_ENABLE_Pos); // Disable SysTick counter
		HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON,PWR_SLEEPENTRY_WFI);
		/* Enable the SysTick interrupt */
		HAL_ResumeTick();
		//SysTick->CTRL |= (SysTick_CTRL_ENABLE_Msk << SysTick_CTRL_ENABLE_Pos); // Enable SysTickCounter
		log_info("Woke up from sleep!!!\n");
    }

  }

  /* Deinit the peripherals */
  HAL_ADC_Stop(&hadc2);

  //HAL_TIM_Base_Stop(&htim2);
  BSP_LED_DeInit(LED7);
  BSP_LED_DeInit(LED5);
  //HAL_PWR_DisablePVD();

  PERIPH_LOCK(EXTI);
  HAL_EXTI_ClearConfigLine(&hexti62);
  PERIPH_UNLOCK(EXTI);

  VIRT_UART_DeInit(&huart0);

  /* When ready, notify the remote processor that we can be shut down */
  HAL_IPCC_NotifyCPU(&hipcc, COPRO_SYNC_SHUTDOWN_CHANNEL, IPCC_CHANNEL_DIR_RX);

  log_info("Cortex-M4 boot successful shutdown\n");

  while(1);
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /**Configure LSE Drive Capability
    */
  HAL_PWR_EnableBkUpAccess();
  __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_MEDIUMHIGH);

    /**Initializes the CPU, AHB and APB busses clocks
    */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI|RCC_OSCILLATORTYPE_HSE
                              |RCC_OSCILLATORTYPE_LSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS_DIG;
  RCC_OscInitStruct.LSEState = RCC_LSE_ON;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = 16;
  RCC_OscInitStruct.HSIDivValue = RCC_HSI_DIV1;

    /**PLL1 Config
    */
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLL12SOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 3;
  RCC_OscInitStruct.PLL.PLLN = 81;
  RCC_OscInitStruct.PLL.PLLP = 1;
  RCC_OscInitStruct.PLL.PLLQ = 1;
  RCC_OscInitStruct.PLL.PLLR = 1;
  RCC_OscInitStruct.PLL.PLLFRACV = 0x800;
  RCC_OscInitStruct.PLL.PLLMODE = RCC_PLL_FRACTIONAL;
  RCC_OscInitStruct.PLL.RPDFN_DIS = RCC_RPDFN_DIS_DISABLED;
  RCC_OscInitStruct.PLL.TPDFN_DIS = RCC_TPDFN_DIS_DISABLED;

    /**PLL2 Config
    */
  RCC_OscInitStruct.PLL2.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL2.PLLSource = RCC_PLL12SOURCE_HSE;
  RCC_OscInitStruct.PLL2.PLLM = 3;
  RCC_OscInitStruct.PLL2.PLLN = 66;
  RCC_OscInitStruct.PLL2.PLLP = 2;
  RCC_OscInitStruct.PLL2.PLLQ = 1;
  RCC_OscInitStruct.PLL2.PLLR = 1;
  RCC_OscInitStruct.PLL2.PLLFRACV = 0x1400;
  RCC_OscInitStruct.PLL2.PLLMODE = RCC_PLL_FRACTIONAL;
  RCC_OscInitStruct.PLL2.RPDFN_DIS = RCC_RPDFN_DIS_DISABLED;
  RCC_OscInitStruct.PLL2.TPDFN_DIS = RCC_TPDFN_DIS_DISABLED;

    /**PLL3 Config
    */
  RCC_OscInitStruct.PLL3.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL3.PLLSource = RCC_PLL3SOURCE_HSE;
  RCC_OscInitStruct.PLL3.PLLM = 2;
  RCC_OscInitStruct.PLL3.PLLN = 34;
  RCC_OscInitStruct.PLL3.PLLP = 2;
  RCC_OscInitStruct.PLL3.PLLQ = 17;
  RCC_OscInitStruct.PLL3.PLLR = 37;
  RCC_OscInitStruct.PLL3.PLLRGE = RCC_PLL3IFRANGE_1;
  RCC_OscInitStruct.PLL3.PLLFRACV = 0x1A04;
  RCC_OscInitStruct.PLL3.PLLMODE = RCC_PLL_FRACTIONAL;
  RCC_OscInitStruct.PLL3.RPDFN_DIS = RCC_RPDFN_DIS_DISABLED;
  RCC_OscInitStruct.PLL3.TPDFN_DIS = RCC_TPDFN_DIS_DISABLED;

    /**PLL4 Config
    */
  RCC_OscInitStruct.PLL4.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL4.PLLSource = RCC_PLL4SOURCE_HSE;
  RCC_OscInitStruct.PLL4.PLLM = 4;
  RCC_OscInitStruct.PLL4.PLLN = 99;
  RCC_OscInitStruct.PLL4.PLLP = 6;
  RCC_OscInitStruct.PLL4.PLLQ = 8;
  RCC_OscInitStruct.PLL4.PLLR = 8;
  RCC_OscInitStruct.PLL4.PLLRGE = RCC_PLL4IFRANGE_0;
  RCC_OscInitStruct.PLL4.PLLFRACV = 0;
  RCC_OscInitStruct.PLL4.PLLMODE = RCC_PLL_INTEGER;
  RCC_OscInitStruct.PLL4.RPDFN_DIS = RCC_RPDFN_DIS_DISABLED;
  RCC_OscInitStruct.PLL4.TPDFN_DIS = RCC_TPDFN_DIS_DISABLED;

  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
	Error_Handler();
  }
    /**RCC Clock Config
    */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_ACLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_PCLK3|RCC_CLOCKTYPE_PCLK4
                              |RCC_CLOCKTYPE_PCLK5|RCC_CLOCKTYPE_MPU;
  RCC_ClkInitStruct.MPUInit.MPU_Clock = RCC_MPUSOURCE_PLL1;
  RCC_ClkInitStruct.MPUInit.MPU_Div = RCC_MPU_DIV2;
  RCC_ClkInitStruct.AXISSInit.AXI_Clock = RCC_AXISSOURCE_PLL2;
  RCC_ClkInitStruct.AXISSInit.AXI_Div = RCC_AXI_DIV1;
  RCC_ClkInitStruct.MCUInit.MCU_Clock = RCC_MCUSSOURCE_PLL3;
  RCC_ClkInitStruct.MCUInit.MCU_Div = RCC_MCU_DIV1;
  RCC_ClkInitStruct.APB4_Div = RCC_APB4_DIV2;
  RCC_ClkInitStruct.APB5_Div = RCC_APB5_DIV4;
  RCC_ClkInitStruct.APB1_Div = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2_Div = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB3_Div = RCC_APB3_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct) != HAL_OK)
  {
	Error_Handler();
  }

    /**Set the HSE division factor for RTC clock
    */
  __HAL_RCC_RTC_HSEDIV(24);
}


/* DAC1 init function */
static void MX_DAC1_Init(void)
{

  DAC_ChannelConfTypeDef sConfig;

    /**DAC Initialization 
    */
  hdac1.Instance = DAC1;
  if (HAL_DAC_Init(&hdac1) != HAL_OK)
  {
    Error_Handler();
  }

    /**DAC channel OUT1 config 
    */
  sConfig.DAC_HighFrequency = DAC_HIGH_FREQUENCY_INTERFACE_MODE_DISABLE;
  sConfig.DAC_SampleAndHold = DAC_SAMPLEANDHOLD_DISABLE;
  sConfig.DAC_Trigger = DAC_TRIGGER_NONE;
  sConfig.DAC_OutputBuffer = DAC_OUTPUTBUFFER_DISABLE;
  sConfig.DAC_ConnectOnChipPeripheral = DAC_CHIPCONNECT_ENABLE; /* ENABLE/DISABLE connection to on-chip peripherals*/
  sConfig.DAC_UserTrimming = DAC_TRIMMING_FACTORY;

  /* The DMA is not configured for the DAC in this case */

  if (HAL_DAC_ConfigChannel(&hdac1, &sConfig, DAC_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }

}

/* TIM2 init function */
static void MX_TIM2_Init(void)
{

  TIM_ClockConfigTypeDef sClockSourceConfig;
  TIM_MasterConfigTypeDef sMasterConfig;

  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 1;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = 97999;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }

  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }

  sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }

}


/**
  * @brief IPPC Initialization Function
  * @param None
  * @retval None
  */
static void MX_IPCC_Init(void)
{

  hipcc.Instance = IPCC;
  if (HAL_IPCC_Init(&hipcc) != HAL_OK)
  {
     Error_Handler();
  }
}

/* USER CODE BEGIN 4 */
Msg_t ParseMsg(uint8_t *msg){
	Msg_t ret;
	if(!strncmp(trProc_ack,(char*)msg,strlen(trProc_ack))){ // A7 transmission processed ack
		ret = DATA_ACK;
		log_dbg("Ack received\n");
	} else if(!strncmp(thrWait_msg,(char*)msg,strlen(thrWait_msg))){ // Wait for new thresholds
		ret = WAIT_THR;
		log_dbg("Waiting for threshold\n");
	} else if(!strncmp(waitSusp_msg,(char*)msg,strlen(waitSusp_msg))){ // Wait for A7 suspension
		ret = WAIT_SUSP;
		log_dbg("Waiting for A7 suspension\n");
	} else { // Thresholds
		log_dbg("Old ADC threshold values: [High] %u | [Low] %u\n", (unsigned int) AnalogWDGConfig.HighThreshold, (unsigned int) AnalogWDGConfig.LowThreshold );
		lowThr = __ADC_CALC_VOLTAGE_DATA(VDDA_APPLI, atoi(strtok((char*)msg, &delimThr)));
		highThr = __ADC_CALC_VOLTAGE_DATA(VDDA_APPLI, atoi(strtok(NULL, &delimThr)));
		ret = (!lowThr && !highThr)? ERR:THR;
		/* atoi() returns 0 in case of error so the string 0;0 cannot be used as a valid input string */
	}
	return ret;
}

/* PVD configuration */
void ConfigPVD(void){
	PWR_PVDTypeDef sConfigPVD = {0};

	sConfigPVD.Mode = PWR_PVD_MODE_NORMAL;
	sConfigPVD.PVDLevel = PWR_PVDLEVEL_6;		// Threshold set to 2.85V

	HAL_PWR_ConfigPVD(&sConfigPVD);
}

/* PVD callback */
void HAL_PWR_PVDCallback(void){
	if(LL_PWR_IsActiveFlag_PVDO())
		log_info("VDD below 2.85V\n");
}

void VIRT_UART0_RxCpltCallback(VIRT_UART_HandleTypeDef *huart)
{

	log_dbg("Msg received on VIRTUAL UART0 channel:  %s \n\r", (char *) huart->pRxBuffPtr);

    /* copy received msg in a variable */
    VirtUart0ChannelRxSize = huart->RxXferSize < MAX_BUFFER_SIZE? huart->RxXferSize : MAX_BUFFER_SIZE-1;

    //log_dbg("Msg size: %d\n",(int)VirtUart0ChannelRxSize);
    // The messages sent with "echo" on the Linux side are always interpreted as strings
    memcpy(VirtUart0ChannelBuffRx, huart->pRxBuffPtr, VirtUart0ChannelRxSize);
    VirtUart0RxMsg = SET;
}

void Check_Delay(uint8_t *BuffRx, uint16_t BuffSize)
{
  uint8_t delay = 0;

  if (!strncmp((char *)BuffRx, MSG_DELAY, strlen(MSG_DELAY)))
  {
    if (BuffSize > strlen(MSG_DELAY))
      delay = atoi((char *)BuffRx + strlen(MSG_DELAY));

    if (delay == 0)
      delay = 20;

    log_info("Waiting %d secs before sending the answer message\r\n", delay);
    HAL_Delay(delay * 1000);
  }
}

void Check_Sleep(uint8_t *BuffRx)
{
  FlagStatus Stop_Flag = RESET;

  if (!strncmp((char *)BuffRx, MSG_STOP, strlen(MSG_STOP)))
  {
    HAL_Delay(500); /* wait for ack message to be received */

    log_info("Going into CStop mode\r\n");

    /* CRITICAL SECTION STARTS HERE!
     * IRQs will be masked (Only RCC IRQ allowed).
     * Eg. SysTick IRQ won't be able to increment uwTick HAL variable, use a
     * polling method if delays or timeouts are required.
     */

    /* (C)STOP protection mechanism
     * Only the IT with the highest priority (0 value) can interrupt.
     * RCC_WAKEUP_IRQn IT is intended to have the highest priority and to be the
     * only one IT having this value
     * RCC_WAKEUP_IRQn is generated only when RCC is completely resumed from
     * CSTOP */
    __set_BASEPRI((RCC_WAKEUP_IRQ_PRIO + 1) << (8 - __NVIC_PRIO_BITS));

    /* Note: log_info must not be used on critical section as it uses
     * HAL_GetTick() (IRQ based) */

    /* Back up clock context */
    RCC_backupClocks();

    /* Clear the Low Power MCU flags before going into CSTOP */
    LL_PWR_ClearFlag_MCU();

    HAL_PWR_EnterSTOPMode(PWR_MAINREGULATOR_ON, PWR_STOPENTRY_WFI);

    /* Leaving CStop mode */

    /* Test if system was on STOP mode */
    if(LL_PWR_MCU_IsActiveFlag_STOP() == 1U)
    {
      /* System was on STOP mode */
      Stop_Flag = SET;

      /* Clear the Low Power MCU flags */
      LL_PWR_ClearFlag_MCU();

      /* Restore clocks */
      if (RCC_restoreClocks() != HAL_OK)
      {
        Error_Handler();
      }
    }

    /* All level of ITs can interrupt */
    __set_BASEPRI(0U);

    /* CRITICAL SECTION ENDS HERE */

    log_info("CStop mode left\r\n");

    if (Stop_Flag == SET)
    {
      log_info("System was on STOP mode\r\n");
    }

  }

  if (!strncmp((char *)BuffRx, MSG_STANDBY, strlen(MSG_STANDBY)))
  {
    HAL_Delay(500); /* wait for ack message to be received */

    log_info("Going to Standby mode\r\n");
    /* MCU CSTOP allowing system Standby mode */
    HAL_PWR_EnterSTANDBYMode();
    log_info("Leaving Standby mode\r\n");
  }
}

/**
  * @brief  Configures EXTI line 14 (connected to PA.14 pin) in interrupt mode
  * @param  None
  * @retval None
  */
static void EXTI14_IRQHandler_Config(void)
{
  GPIO_InitTypeDef   GPIO_InitStruct;
  EXTI_ConfigTypeDef EXTI_ConfigStructure;

  /* Enable GPIOA clock */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  /* Configure PA.14 pin as input floating */
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;

  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Pin = USER_BUTTON_PIN;
  PERIPH_LOCK(GPIOA);
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
  PERIPH_UNLOCK(GPIOA);

  /* Set configuration except Interrupt and Event mask of Exti line 14*/
  EXTI_ConfigStructure.Line = EXTI_LINE_14;
  EXTI_ConfigStructure.Trigger = EXTI_TRIGGER_FALLING;
  EXTI_ConfigStructure.GPIOSel = EXTI_GPIOA;
  EXTI_ConfigStructure.Mode = EXTI_MODE_C2_INTERRUPT;
  PERIPH_LOCK(EXTI);
  HAL_EXTI_SetConfigLine(&hexti14, &EXTI_ConfigStructure);
  PERIPH_UNLOCK(EXTI);

  /* Register callback to treat Exti interrupts in user Exti14FallingCb function */
  HAL_EXTI_RegisterCallback(&hexti14, HAL_EXTI_FALLING_CB_ID, Exti14FallingCb);

  /* Enable and set line 14 Interrupt (UserButton) */
  /* Higher priority than ADC interrupts */
  HAL_NVIC_SetPriority(EXTI14_IRQn, DEFAULT_IRQ_PRIO, 0);
  HAL_NVIC_EnableIRQ(EXTI14_IRQn);
}

/**
  * @brief  Configure ADC (ADC instance: ADCx) and GPIO used by ADC channels.
  *         Configuration of GPIO:
  *           - Pin:                    PA.04 (on this STM32 device, ADC2 channel 16 is mapped on this GPIO)
  *           - Mode:                   analog
  *         Configuration of ADC:
  *         - Common to several ADC:
  *           - Conversion clock:       Synchronous from PCLK
  *           - Internal path:          None                         (default configuration from reset state)
  *         - Multimode
  *           Feature not used: all parameters let to default configuration from reset state
  *           - Mode                    Independent                  (default configuration from reset state)
  *           - DMA transfer:           Disabled                     (default configuration from reset state)
  *           - Delay sampling phases   1 ADC clock cycle            (default configuration from reset state)
  *         - ADC instance
  *           - Resolution:             12 bits                      (default configuration from reset state)
  *           - Data alignment:         right aligned                (default configuration from reset state)
  *           - Low power mode:         disabled                     (default configuration from reset state)
  *           - Offset:                 none                         (default configuration from reset state)
  *         - Group regular
  *           - Trigger source:         SW start
  *           - Trigger edge:           not applicable with SW start
  *           - Continuous mode:        single conversion            (default configuration from reset state)
  *           - DMA transfer:           enabled, unlimited requests
  *           - Overrun:                data overwritten
  *           - Sequencer length:       disabled: 1 rank             (default configuration from reset state)
  *           - Sequencer discont:      disabled: sequence done in 1 scan (default configuration from reset state)
  *           - Sequencer rank 1:       ADCx ADCx_CHANNELa
  *         - Group injected
  *           Feature not used: all parameters let to default configuration from reset state
  *           - Trigger source:         SW start                     (default configuration from reset state)
  *           - Trigger edge:           not applicable with SW start
  *           - Auto injection:         disabled                     (default configuration from reset state)
  *           - Contexts queue:         disabled                     (default configuration from reset state)
  *           - Sequencer length:       disabled: 1 rank             (default configuration from reset state)
  *           - Sequencer discont:      disabled: sequence done in 1 scan (default configuration from reset state)
  *           - Sequencer rank 1:       first channel available      (default configuration from reset state)
  *         - Channel
  *           - Sampling time:          ADCx ADCx_CHANNELa set to sampling time 160.5 ADC clock cycles (on this STM32 serie, sampling time is channel wise)
  *           - Differential mode:      single ended                 (default configuration from reset state)
  *         - Analog watchdog
  *           Feature not used: all parameters let to default configuration from reset state
  *           - AWD number:             1
  *           - Monitored channels:     none                         (default configuration from reset state)
  *           - Threshold high:         0x000                        (default configuration from reset state)
  *           - Threshold low:          0xFFF                        (default configuration from reset state)
  *         - Oversampling
  *           Feature not used: all parameters let to default configuration from reset state
  *           - Scope:                  none                         (default configuration from reset state)
  *           - Discontinuous mode:     disabled                     (default configuration from reset state)
  *           - Ratio:                  2                            (default configuration from reset state)
  *           - Shift:                  none                         (default configuration from reset state)
  *         - Interruptions
  *           None: with HAL driver, ADC interruptions are set using
  *           function "HAL_ADC_start_xxx()".
  * @note   Using HAL driver, configuration of GPIO used by ADC channels,
  *         NVIC and clock source at top level (RCC)
  *         are not implemented into this function,
  *         must be implemented into function "HAL_ADC_MspInit()".
  * @param  None
  * @retval None
  */
__STATIC_INLINE void Configure_ADC(void)
{
  ADC_ChannelConfTypeDef sConfig = {0};

  /*## Configuration of ADC ##################################################*/
  
  /*## Configuration of ADC hierarchical scope: ##############################*/
  /*## common to several ADC, ADC instance, ADC group regular  ###############*/
  
  /* Set ADC instance of HAL ADC handle hadc2 */
  hadc2.Instance = ADCx;
  
  /* Configuration of HAL ADC handle init structure:                          */
  /* parameters of scope ADC instance and ADC group regular.                  */
  /* Note: On this STM32 serie, ADC group regular sequencer is                */
  /*       fully configurable: sequencer length and each rank                 */
  /*       affectation to a channel are configurable.                         */
  hadc2.Init.ClockPrescaler        	= ADC_CLOCK_SYNC_PCLK_DIV2;
  hadc2.Init.Resolution            	= ADC_RESOLUTION_12B;
  hadc2.Init.ScanConvMode          	= ADC_SCAN_DISABLE;             /* Sequencer disabled (ADC conversion on only 1 channel: channel set on rank 1) */
  hadc2.Init.EOCSelection          	= ADC_EOC_SINGLE_CONV;
  hadc2.Init.LowPowerAutoWait      	= DISABLE;
  hadc2.Init.ContinuousConvMode    	= ENABLE;                      	/* Continuous mode should be disabled to have only 1 conversion at each conversion trig */
  hadc2.Init.NbrOfConversion       	= 1;                            /* Parameter discarded because sequencer is disabled */
  hadc2.Init.DiscontinuousConvMode 	= DISABLE;                      /* Parameter discarded because sequencer is disabled */
  hadc2.Init.NbrOfDiscConversion   	= 1;                            /* Parameter discarded because sequencer is disabled */
  hadc2.Init.ExternalTrigConv		= ADC_SOFTWARE_START;     		/* Trig of conversion start done by software */
  hadc2.Init.ExternalTrigConvEdge  	= ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc2.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DR;
  hadc2.Init.Overrun               	= ADC_OVR_DATA_OVERWRITTEN;
  hadc2.Init.OversamplingMode      	= DISABLE;

  HAL_ADC_DeInit(&hadc2);
  if (HAL_ADC_Init(&hadc2) != HAL_OK)
  {
    /* ADC initialization error */
    Error_Handler();
  }
  
  
  /*## Configuration of ADC hierarchical scope: ##############################*/
  /*## ADC group injected and channels mapped on group injected ##############*/
  
  /* Note: ADC group injected not used and not configured in this example.    */
  /*       Refer to other ADC examples using this feature.                    */
  /* Note: Call of the functions below are commented because they are         */
  /*       useless in this example:                                           */
  /*       setting corresponding to default configuration from reset state.   */
  
  
  /*## Configuration of ADC hierarchical scope: ##############################*/
  /*## channels mapped on group regular         ##############################*/
  
  /* Configuration of channel on ADCx regular group on sequencer rank 1 */
  /* Note: On this STM32 serie, ADC group regular sequencer is                */
  /*       fully configurable: sequencer length and each rank                 */
  /*       affectation to a channel are configurable.                         */
  /* Note: Considering IT occurring after each ADC conversion                 */
  /*       (IT by ADC group regular end of unitary conversion),               */
  /*       select sampling time and ADC clock with sufficient                 */
  /*       duration to not create an overhead situation in IRQHandler.        */
  sConfig.Channel      = ADCx_CHANNELa;               /* ADC channel selection */
  sConfig.Rank         = ADC_REGULAR_RANK_1;          /* ADC group regular rank in which is mapped the selected ADC channel */
  sConfig.SamplingTime = ADC_SAMPLETIME_810CYCLES_5;  /* ADC channel sampling time */
  sConfig.SingleDiff   = ADC_SINGLE_ENDED;            /* ADC channel differential mode */
  sConfig.OffsetNumber = ADC_OFFSET_NONE;             /* ADC channel affected to offset number */
  sConfig.Offset       = 0;                           /* Parameter discarded because offset correction is disabled */
  
  if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
  {
    /* Channel Configuration Error */
    Error_Handler();
  }
  
  
  /*## Configuration of ADC hierarchical scope: multimode ####################*/
  /* Note: ADC multimode not used and not configured in this example.         */
  /*       Refer to other ADC examples using this feature.                    */
  
  
  /*## Configuration of ADC transversal scope: analog watchdog ###############*/
  /* Configure Analog WatchDog 1*/
  /* NOTE: Use ADC_ANALOGWATCHDOG_2 or ADC_ANALOGWATCHDOG_3 if you need to monitor multiple
   * channels at the same time (WatchdogMode = ADC_ANALOGWATCHDOG_ALL_xxx) with a limited
   * resolution (8 bits) */

  AnalogWDGConfig.WatchdogNumber = ADC_ANALOGWATCHDOG_1;
  AnalogWDGConfig.WatchdogMode = ADC_ANALOGWATCHDOG_SINGLE_REG;
  AnalogWDGConfig.Channel = ADCx_CHANNELa;
  AnalogWDGConfig.ITMode = ENABLE;
  AnalogWDGConfig.HighThreshold = highThr;
  AnalogWDGConfig.LowThreshold = lowThr;
  if (HAL_ADC_AnalogWDGConfig(&hadc2, &AnalogWDGConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /*## Configuration of ADC transversal scope: oversampling ##################*/
  
  /* Note: ADC oversampling not used and not configured in this example.      */
  /*       Refer to other ADC examples using this feature.                    */
  
}

/**
  * @brief  For this example, generate a waveform voltage on a spare DAC
  *         channel, so user has just to connect a wire between DAC channel 
  *         (pin PA4) and ADC channel (pin PA4) to run this example.
  *         (this prevents the user from resorting to an external signal
  *         generator).
  *         This function configures the DAC and generates a constant voltage of Vdda/2.
  * @note   Voltage level can be modifying afterwards using function
  *         "Generate_waveform_SW_update()".
  * @param  None
  * @retval None
  */
static void Generate_waveform_SW_update_Config(void)
{
  /* Set DAC Channel data register: channel corresponding to ADC channel ADC2_CHANNEL_16 */
	/* Set DAC output to 1/2 of full range (4095 <=> Vdda=2.9V): 2048 <=> 1.45V */
  if (HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, DIGITAL_SCALE_12BITS/2) != HAL_OK)
  {
    /* Setting value Error */
    Error_Handler();
  }
  
  /* Enable DAC Channel: channel corresponding to ADC channel ADC2_CHANNEL_16 */
  if (HAL_DAC_Start(&hdac1, DAC_CHANNEL_1) != HAL_OK)
  {
    /* Start Error */
    Error_Handler();
  }

}

/**
  * @brief  For this example, generate a waveform voltage on a spare DAC
  *         channel, so user has just to connect a wire between DAC channel 
  *         (pin PA4) and ADC channel (pin PA4) to run this example.
  *         (this prevents the user from resorting to an external signal
  *         generator).
  *         This function modifies the voltage level, to generate a
  *         waveform circular, shape of ramp: Voltage is increasing at each 
  *         press on push button, from 0 to maximum range (Vdda) in 4 steps,
  *         then starting back from 0V.
  *         Voltage is updated incrementally at each call of this function.
  * @note   Preliminarily, DAC must be configured once using
  *         function "Generate_waveform_SW_update_Config()".
  * @param  None
  * @retval None
  */
static void Generate_waveform_SW_update(void)
{
  static uint8_t ub_dac_steps_count = 0;      /* Count number of clicks: Incremented after User Button interrupt */
  
  /* Set DAC voltage on channel corresponding to ADC2_CHANNEL_16              */
  /* in function of user button clicks count.                                   */
  /* Set DAC output on 5 voltage levels, successively to:                       */
  /*  - minimum of full range (0 <=> ground 0V)                                 */
  /*  - 1/4 of full range (4095 <=> Vdda=2.9V): 1023 <=> 0.725V                 */
  /*  - 1/2 of full range (4095 <=> Vdda=2.9V): 2048 <=> 1.45V                  */
  /*  - 3/4 of full range (4095 <=> Vdda=2.9V): 3071 <=> 2.175V                 */
  /*  - maximum of full range (4095 <=> Vdda=2.9V)                              */
  if (HAL_DAC_SetValue(&hdac1,
                       DAC_CHANNEL_1,
                       DAC_ALIGN_12B_R,
                       ((DIGITAL_SCALE_12BITS * ub_dac_steps_count) / 4)
                      ) != HAL_OK)
  {
    /* Start Error */
    Error_Handler();
  }
  
  /* Wait for voltage settling time */
  HAL_Delay(1);
  
  /* Manage ub_dac_steps_count to increment it in 4 steps and circularly.   */
  if (ub_dac_steps_count < 4)
  {
    ub_dac_steps_count++;
  }
  else
  {
    ub_dac_steps_count = 0;
  }

}

/**
  * @brief  Restore CM4 clock tree
  *         After a STOP platform mode re-enable PLL3 and PLL4 if used as
  *         CM4/peripheral (allocated by CM4) clock source and restore the CM4
  *         clock source muxer and the CM4 prescaler.
  *         Use polling mode on for timeout generation as code is used
  *         on critical section.
  * @param  None
  * @retval HAL_StatusTypeDef value
  */
static HAL_StatusTypeDef RCC_restoreClocks(void)
{
  bool pll3_enable = false;
  bool pll4_enable = false;
  HAL_StatusTypeDef status = HAL_OK;

  /* Update SystemCoreClock variable */
  SystemCoreClockUpdate();

  /* Reconfigure Systick */
  status = HAL_InitTick(uwTickPrio);
  if (status != HAL_OK)
  {
    return status;
  }

  /* Check out if it is needed to enable PLL3 and PLL4 */
  if (RCC_MCUInit.MCU_Clock == LL_RCC_MCUSS_CLKSOURCE_PLL3)
  {
      pll3_enable = true;
  }

  switch(PeriphClk.AdcClockSelection)
  {
    case  RCC_ADCCLKSOURCE_PLL4:
      pll4_enable = true;
      break;

    case  RCC_ADCCLKSOURCE_PLL3:
      pll3_enable = true;
      break;
  }

  /* Enable PLL3 if needed */
  if (pll3_enable)
  {
    /* Enable PLL3 */
    LL_RCC_PLL3_Enable();

    /* Wait till PLL3 is ready */
    __WAIT_EVENT_TIMEOUT(LL_RCC_PLL3_IsReady(), CLOCKSWITCH_TIMEOUT_VALUE);

    /* Enable PLL3 outputs */
    LL_RCC_PLL3P_Enable();
    LL_RCC_PLL3Q_Enable();
    LL_RCC_PLL3R_Enable();
  }

  /* Enable PLL4 if needed */
  if (pll4_enable)
  {
    /* Enable PLL4 */
    LL_RCC_PLL4_Enable();

    /* Wait till PLL4 is ready */
    __WAIT_EVENT_TIMEOUT(LL_RCC_PLL4_IsReady(), CLOCKSWITCH_TIMEOUT_VALUE);

    /* Enable PLL4 outputs */
    LL_RCC_PLL4P_Enable();
    LL_RCC_PLL4Q_Enable();
    LL_RCC_PLL4R_Enable();
  }

  /* Configure MCU clock only */
  LL_RCC_SetMCUSSClkSource(RCC_MCUInit.MCU_Clock);

  /* Wait till MCU is ready */
  __WAIT_EVENT_TIMEOUT(__HAL_RCC_GET_FLAG(RCC_FLAG_MCUSSRCRDY),
                       CLOCKSWITCH_TIMEOUT_VALUE);

  /* Update SystemCoreClock variable */
  SystemCoreClockUpdate();

  /* Reconfigure Systick */
  status = HAL_InitTick(uwTickPrio);
  if (status != HAL_OK)
  {
    return status;
  }

  /* Set MCU division factor */
  LL_RCC_SetMLHCLKPrescaler(RCC_MCUInit.MCU_Div);

  /* Wait till MCUDIV is ready */
  __WAIT_EVENT_TIMEOUT(__HAL_RCC_GET_FLAG(RCC_FLAG_MCUDIVRDY),
                       CLOCKSWITCH_TIMEOUT_VALUE);

  /* Update SystemCoreClock variable */
  SystemCoreClockUpdate();

  /* Reconfigure Systick */
  status = HAL_InitTick(uwTickPrio);
  if (status != HAL_OK)
  {
    return status;
  }

  return status;
}

/**
  * @brief  Back up clock tree
  * @param  None
  * @retval None
  */
static void RCC_backupClocks(void)
{
  /* Back up MCU clock configuration */
  RCC_MCUInit.MCU_Clock = LL_RCC_GetMCUSSClkSource();
  RCC_MCUInit.MCU_Div = LL_RCC_GetMLHCLKPrescaler();

  /* Back up peripheral clock configuration */
  HAL_RCCEx_GetPeriphCLKConfig(&PeriphClk);
}

/******************************************************************************/
/*   USER IRQ HANDLER TREATMENT                                               */
/******************************************************************************/

/**
  * @brief EXTI line detection callbacks
  * @param None:
  * @retval None
  */
static void Exti14FallingCb(void)
{
    /* Set variable to report push button event to main program */
    ubUserButtonClickEvent = SET;
}

/* HAL_ADC_ConvCpltCallback() and HAL_ADC_ConvHalfCpltCallback() are used both in
 * DMA and non-DMA transfer mode (in this case the conversion has to be started using
 * HAL_ADC_Start_IT() for the interrupt to be generated) and are used to signal respectively
 * the conversion completion and half of the conversion. */

/**
  * @brief  Conversion complete callback in non blocking mode 
  * @param  hadc: ADC handle
  * @note   This example shows a simple way to report end of conversion
  *         and get conversion result. You can add your own implementation.
  * @retval None
  */
/*void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
}*/

/**
  * @brief  Conversion DMA half-transfer callback in non-blocking mode.
  * @param hadc ADC handle
  * @retval None
  */
/*void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
}*/


/**
  * @brief  Analog watchdog 1 callback in non-blocking mode.
  * @param hadc ADC handle
  * @retval None
  */
void HAL_ADC_LevelOutOfWindowCallback(ADC_HandleTypeDef *hadc)
{
	/* Retrieve converted ADC value */
	/* Check for FULL buffer to avoid overwriting existing data (data have not been transmitted yet)
	* Some out of window data can be lost if the buffer is not emptied */
	if(OutOfWindowData != MAX_ADC_BUFFER_SIZE){
	  ADCxData = HAL_ADC_GetValue(&hadc2);
	  // The values are converted in mV before being recorded
	  ADCxDataBuffer[OutOfWindowData] = __ADC_CALC_DATA_VOLTAGE(VDDA_APPLI, ADCxData);
	  //log_dbg("ADC conversion result: %d\n", (int) ADCxData);
	  OutOfWindowData++;
	  //BSP_LED_On(LED7);
	}
	else{
	  /* Stop the ADC to avoid flooding the program with AWD interrupts in case the buffer limit
	   * is reached */
	  HAL_ADC_Stop(&hadc2);
	}
	/* The above operations need to be done in the ISR.
	 * The value conversion could be done before transferring the data but it is a simple computation */
}

void CoproSync_ShutdownCb(IPCC_HandleTypeDef * hipcc, uint32_t ChannelIndex, IPCC_CHANNELDirTypeDef ChannelDir)
{
  Shutdown_Req = 1;
}

/**
  * @brief  ADC error callback in non blocking mode
  *        (ADC conversion with interruption or transfer by DMA)
  * @param  hadc: ADC handle
  * @retval None
  */
void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *hadc)
{
  /* In case of ADC error, call main error handler */
  Error_Handler();
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @param  file: The file name as string.
  * @param  line: The line in file as a number.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  log_err("FATAL ERROR\r\n");
  BSP_LED_On(LED7);
  while(1);
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t* file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  log_err("OOOps...\r\n");
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */

