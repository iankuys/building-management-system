from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
from time import sleep, strftime
from datetime import datetime
import threading
from CIMIS import irrigation_data 

lcd = None
mcp = None
thread = None
lcd_state = False
new_message = None

def LCD_setup():
    global lcd
    global mcp
    global lcd_state
    global thread

    PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
    PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
    # Create PCF8574 GPIO adapter.
    try:
        mcp = PCF8574_GPIO(PCF8574_address)
    except:
        try:
            mcp = PCF8574_GPIO(PCF8574A_address)
        except:
            print ('I2C Address Error !')
            exit(1)
    
    # Create LCD, passing in MCP GPIO adapter.
    lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)
    mcp.output(3, 1) # Turns on lcd backlight
    lcd.begin(16, 2) # Set lcd mode

    lcd_state = True
    thread = threading.Thread(target=lcd_thread)
    thread.daemon = True
    thread.start()

def display_data(data: irrigation_data):
    global new_message
    message = f'{data.get_type}\nT:{str(data.get_temperature)} H:{str(data.get_humidity)}'
    # wait till previous message is displayed
    while new_message is not None:
        sleep(1)
    new_message = message

#This function facilitates what gets printed to the LCD based on the message we 
#receive from main program.  
def display_message(string) :
    global new_message 
    message = string
    # while(new_message is not None):
    #     sleep(1)
    new_message = message 

def lcd_thread():
    global new_message

    while lcd_state:
        lcd.clear()
        lcd.setCursor(0, 0)
        if new_message is None:
            lcd.message(datetime.now().strftime('Date: %m-%d-%Y') + "\n" + datetime.now().strftime('Time: %H:%M:%S'))
            sleep(1)
        else:
            lcd.message(new_message)
            new_message = None
            sleep(3)
    print('[Main] LCD Thread terminated')

def lcd_terminate():
    global thread
    global lcd_state

    lcd_state = False

    thread.join()
    mcp.output(3,0)
    lcd.clear()

    

