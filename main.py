import RPi.GPIO as GPIO
import LCD as LCD
from CIMIS import cimis_get
from CIMIS import irrigation_data
import Freenove_DHT as DHT

from datetime import datetime, timedelta
import threading
from time import sleep
import time

#define the pins
dht_pin = 11     #GPIO 17
pir_pin = 16      #GPIO 23

up_btn_pin = 22     #GPIO 25
down_btn_pin = 12      #GPIO 18 
door_btn_pin = 13     #GPIO 27

green_led_pin = 32     #GPIO12
red_led_pin = 36    #GPIO 16
blue_led_pin = 38      #GPIO 20

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)       

#Setup DHT , create DHT class
dht = DHT.DHT(dht_pin)  

GPIO.setup(red_led_pin, GPIO.OUT, initial = GPIO.LOW) 
GPIO.setup(blue_led_pin, GPIO.OUT, initial = GPIO.LOW) 
GPIO.setup(green_led_pin, GPIO.OUT, initial = GPIO.LOW) 

#Setup LCD Display
LCD.lcd_setup()
#Setup PIR sensor 
GPIO.setup(pir_pin, GPIO.IN)

# hvac global variabless
retrieved_data = None
humidity = None
temperature = None
terminated = False
door_state = False
hvac_temp = (65+95)/2
weather_index = None
bill_cost = None
energy_used = None
foutput = "log.txt"

# hvac energy bill
heat_state = False
ac_state =  False
start_time = None
end_time = None

# pir global
motion_detected = False
no_motion_counter = 0

# fire alarm global
fire_state = False
blink_period = 1.0  # Initial blink period set to 1 (in seconds)
blink_state = False  # Flag to indicate if blink mode is active
blinking_thread = None

# security global
door_state = "Closed"
security_on = True
door_state_change = False

#**************************************** PIR ***************************************************
def pir_thread():
    global motion_detected
    global no_motion_counter

    while (not terminated):
        if (GPIO.input(pir_pin) == GPIO.HIGH):
            if not motion_detected:
                motion_detected = True
                GPIO.output(green_led_pin, GPIO.HIGH) #turn on green led
                no_motion_counter = 0
        else:
            if motion_detected:
                no_motion_counter += 1
                if no_motion_counter >= 10:  # If no motion for 10 seconds
                    motion_detected = False
                    GPIO.output(green_led_pin, GPIO.LOW) #turn off green led
            else:
                no_motion_counter = 0
        sleep(1) # Wait for 1 second before checking again

#**************************************** HVAC ***************************************************

def dht11_thread():
    global dht
    global temperature
    recorded_temp = [0,0,0]
    i = 0

    # retrieve ambient temperature from the DHT-11 sensor once every 1
    # second and average the last three measurements to eliminate possible mistakes in measurements.
    while(not terminated):
        while i < 3:
            result = dht.readDHT11()
            recorded_temp[i] = result
            i+=1
            sleep(1)
        temperature = sum(recorded_temp)/len(recorded_temp)
        i = 0
    print('[Main] DHT Thread terminated')

def cimis_thread():
    global humidity
    global terminated

    start_time = time.time()
    initial_state = True

    while(not terminated):
        if initial_state or (time.time() - start_time >= 3600):
            initial_state = False

            # update start_time to current time
            start_time = time.time()

            curr = datetime.now()
            hr = curr.hour
            irr_data = cimis_get(hr)
            humidity = irr_data.get_humidity()
        sleep(5)
    print('[Main] CIMIS Thread terminated')

def hvac_thread():
    global hvac_temp
    global temperature
    global weather_index
    global start_time
    global end_time
    global heat_state
    global ac_state
    global bill_cost
    global energy_used
    
    while(not terminated):
        get_weather_index() # update weather index
        temp_diff = hvac_temp - weather_index
        GPIO.output(red_led_pin, GPIO.LOW)
        GPIO.output(blue_led_pin, GPIO.LOW)

        if (temp_diff > 3):
            if (not heat_state):
                # turn on heater if desired temp is higher than room temp
                GPIO.output(red_led_pin, GPIO.HIGH)
                LCD.display_message("Heat is on")
                start_time = datetime.now()
                heat_state = True
        elif (temp_diff < 3):
            if (not ac_state):
                # turn on AC if desired temp is lower than room temp
                GPIO.output(blue_led_pin, GPIO.HIGH)
                LCD.display_message("AC is on")
                start_time = datetime.now()
                ac_state = True
        else:
            # if heat or ac was already on
            if heat_state:
                end_time = datetime.now()
                time_difference = end_time - start_time
                difference_in_seconds = time_difference.total_seconds()
                energy_used = 3.6 * (difference_in_seconds/3600) # convert seconds to hours
                bill_cost = 0.5 * energy_used # 50 cents per kWh
                LCD.display_data(f'Energy:{energy_used}\n cost: {bill_cost}')

            elif ac_state:
                end_time = datetime.now()
                time_difference = end_time - start_time
                difference_in_seconds = time_difference.total_seconds()
                energy_used = 1.8 * (difference_in_seconds/3600) # convert seconds to hours
                bill_cost = 0.5 * energy_used # 50 cents per kWh
                LCD.display_data(f'Energy:{energy_used}\n cost: {bill_cost}')

            heat_state = False
            ac_state = False

        #check for button inputs every 3 seconds
        time.sleep(3)
    print('[Main] HVAC Thread terminated')

def handle_hvac(pin):
    global havac_temp

    if (pin == up_btn_pin):
        hvac_temp += 1
    elif (pin == down_btn_pin):
        havac_temp -= 1

def get_weather_index():
    global temperature
    global humidity
    global weather_index

    weather_index = temperature + 0.05 * humidity

# Turn off all LEDs
def turn_off_leds():
    GPIO.output(green_led_pin, GPIO.LOW)  
    GPIO.output(blue_led_pin, GPIO.LOW)
    GPIO.output(red_led_pin, GPIO.LOW)

#**************************************** Fire Detection ***************************************************

def fire_thread():
    global terminated
    global weather_index
    global blinking_thread
    global blink_state

    while (not terminated or fire_state):
        get_weather_index() # get latest weather index

        if weather_index > 95:
            # fire detected!
            # turn off HVAC
            terminated = True
            fire_state = True
            LCD.display_data("FIRE DETECTED!")
            if not blink_state:
                # Start blink mode by setting blink state to true
                blink_state = True
                blinking_thread = threading.Thread(target=blink_thread)
                blinking_thread.daemon = True
                blinking_thread.start()

                sleep(3600) #sleep an hour before detecting for fire again
        else:
            # Stop blink mode by setting blink state to False
            blink_state = False
            blinking_thread.join()  # Wait for the blink thread to finish
            turn_off_leds()

            # fire should be gone
            fire_state = False
            terminated = False
        sleep(1)

def blink_thread():
    global blink_state, blink_period
    # Assuming that all leds are turned off initially
    led_state = GPIO.HIGH
    while blink_state:
        if (led_state == GPIO.LOW):
            led_state = GPIO.HIGH 
        else:
            led_state = GPIO.LOW
            
        # Set the LED state for all LEDs    
        GPIO.output(red_led_pin, led_state)
        GPIO.output(blue_led_pin, led_state)
        GPIO.output(green_led_pin, led_state)
        # Pause for half the blink period
        time.sleep(blink_period / 2.0)

#**************************************** security system ***************************************************
def security_thread():
    global door_state

    while (not terminated or security_on):
        if (door_state_change):
            LCD.display_message("door/window" + door_state)

def handle_door(pin):
    global door_state
    global door_state_change
    # if door is initially closed, open it
    # else close it
    if (pin == door_btn_pin):
        if (door_state == "Closed"):
            door_state = "Opened"
            door_state_change = True
        else:
            door_state = "Closed"
            door_state_change = True


# if __name__ == '__main__':

