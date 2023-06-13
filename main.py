import RPi.GPIO as GPIO
import LCD as LCD
from CIMIS import cimis_get
from CIMIS import irrigation_data
import Freenove_DHT as DHT

from datetime import datetime, timedelta
import threading
from time import sleep
import time
import sys
import select

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
LCD.LCD_setup()
#Setup PIR sensor 
GPIO.setup(pir_pin, GPIO.IN)
GPIO.setup(up_btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(down_btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(door_btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
def pir_thread(lock):
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
    print('[Main] Pir Thread terminated')

#**************************************** HVAC ***************************************************

def dht11_thread(lock):
    global dht
    global temperature
    recorded_temp = [0,0,0]
    i = 0

    # retrieve ambient temperature from the DHT-11 sensor once every 1
    # second and average the last three measurements to eliminate possible mistakes in measurements.
    while(not terminated):
        chk = dht.readDHT11()
        while chk is not dht.DHTLIB_OK:
            chk = dht.readDHT11()
            time.sleep(0.1)
        
        while i < 3:
            recorded_temp[i] = dht.temperature
            i+=1
            sleep(1)
        temperature = sum(recorded_temp)/len(recorded_temp)
        i = 0
    print('[Main] DHT Thread terminated')

def cimis_thread(lock):
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

def hvac_thread(lock):
    global hvac_temp
    global temperature
    global weather_index
    global start_time
    global end_time
    global heat_state
    global ac_state
    global bill_cost
    global energy_used
    global terminated
    global door_state
    global motion_detected
    
    while(not terminated):
        get_weather_index() # update weather index
        temp_diff = hvac_temp - weather_index
        # GPIO.output(red_led_pin, GPIO.LOW)
        # GPIO.output(blue_led_pin, GPIO.LOW)
        # LCD.display_message("Hi FROM HVAC")
        # sleep(3)
        # print(temp_diff)
        if motion_detected:
            light_msg = "ON"
        else:
            light_msg = "OFF"

        if ac_state or heat_state:
            hvac_msg = "ON"
        else:
            hvac_msg = "OFF"

        LCD.display_data(irrigation_data(temperature=weather_index, humidity=humidity), door_state, hvac_msg, light_msg)
        # print(hvac_temp)
        # print (temp_diff)
        if door_state != "Opened":
            if (temp_diff < -3):
                if (not heat_state):
                    # turn on heater if desired temp is higher than room temp
                    GPIO.output(red_led_pin, GPIO.HIGH)
                    GPIO.output(blue_led_pin, GPIO.LOW)
                    LCD.display_message("Heat is on")
                    sleep(3)
                    start_time = datetime.now()
                    heat_state = True
                    ac_state = False
                else:
                    GPIO.output(red_led_pin, GPIO.HIGH)
                    GPIO.output(blue_led_pin, GPIO.LOW)
            elif (temp_diff > 3):
                if (not ac_state):
                    # turn on AC if desired temp is lower than room temp
                    GPIO.output(red_led_pin, GPIO.LOW)
                    GPIO.output(blue_led_pin, GPIO.HIGH)
                    LCD.display_message("AC is on")
                    sleep(3)
                    start_time = datetime.now()
                    heat_state = False
                    ac_state = True
                else:
                    GPIO.output(red_led_pin, GPIO.LOW)
                    GPIO.output(blue_led_pin, GPIO.HIGH)
            else:
                # if heat or ac was already on
                if heat_state:
                    GPIO.output(red_led_pin, GPIO.LOW)
                    end_time = datetime.now()
                    time_difference = end_time - start_time
                    difference_in_seconds = time_difference.total_seconds()
                    energy_used = 3.6 * (difference_in_seconds/3600) # convert seconds to hours
                    bill_cost = 0.5 * energy_used # 50 cents per kWh
                    LCD.display_message(f'Energy: {energy_used}\nCost: ${bill_cost}')
                    sleep(4)

                elif ac_state:
                    GPIO.output(blue_led_pin, GPIO.LOW)
                    end_time = datetime.now()
                    time_difference = end_time - start_time
                    difference_in_seconds = time_difference.total_seconds()
                    energy_used = 1.8 * (difference_in_seconds/3600) # convert seconds to hours
                    bill_cost = 0.5 * energy_used # 50 cents per kWh
                    LCD.display_message(f'Energy: {round(energy_used, 4)}\nCost: ${round(bill_cost, 4)}')
                    sleep(4)

                heat_state = False
                ac_state = False
        else:
            GPIO.output(red_led_pin, GPIO.LOW)
            GPIO.output(blue_led_pin, GPIO.LOW)
        #check for button inputs every 3 seconds
        time.sleep(3)

    print('[Main] HVAC Thread terminated')

def handle_hvac(pin):
    global hvac_temp

    if (pin == up_btn_pin):
        hvac_temp += 1
    elif (pin == down_btn_pin):
        hvac_temp -= 1
    # print(hvac_temp)

def get_weather_index():
    global temperature
    global humidity
    global weather_index

    weather_index = ((float(temperature) * 9/5) + 32) + 0.05 * float(humidity)
    # print(weather_index)

# Turn off all LEDs
def turn_off_leds():
    GPIO.output(green_led_pin, GPIO.LOW)  
    GPIO.output(blue_led_pin, GPIO.LOW)
    GPIO.output(red_led_pin, GPIO.LOW)

#**************************************** Fire Detection ***************************************************

def fire_thread(lock):
    global terminated
    global weather_index
    global blinking_thread
    global blink_state
    global fire_state
    global door_state
    global door_state_change

    while (not terminated or fire_state):
        get_weather_index() # get latest weather index
        # detect_fire() #test fire detection

        if weather_index > 95:
            # fire detected!
            # tff HVAC
            terminated = True
            fire_state = True
            print("fire!")
            LCD.display_message("FIRE DETECTED!")
            if not blink_state:
                # Start blink mode by setting blink state to true
                blink_state = True
                blinking_thread = threading.Thread(target=blink_thread)
                blinking_thread.daemon = True
                blinking_thread.start()
            terminated = True
            fire_state = True
            door_state = "Opened"
            door_state_change = True
            LCD.display_message("DOOR/WINDOW OPEN\n HVAC HALTED")

            sleep(3600) #sleep an hour before detecting for fire again

        elif blink_state:
            # Stop blink mode by setting blink state to False
            blink_state = False
            blinking_thread.join()  # Wait for the blink thread to finish
            turn_off_leds()

            # fire should be gone
            fire_state = False
            terminated = False
        sleep(1)
    print('[Main] Fire Thread terminated')


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
    print('[Main] Blink Thread terminated')

#**************************************** security system ***************************************************
def security_thread(lock):
    global door_state
    global door_state_change
    global terminated
    global security_on
    global ac_state
    global heat_state

    # might need to add security_on later on
    while (not terminated):
        if (door_state_change):
            if (door_state == "Opened"):
                ac_state = False
                heat_state = False

            LCD.display_message("Door/Window\n" + door_state)
            door_state_change = False
            sleep(3)
    print('[Main] Security Thread terminated')

def handle_door(pin):
    global door_state
    global door_state_change
    # if door is initially closed, open it
    # else close it
    if (pin == door_btn_pin):
        # print("door change")
        if (door_state == "Closed"):
            door_state = "Opened"
            door_state_change = True
        else:
            door_state = "Closed"
            door_state_change = True

def input_available():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def detect_fire():
    global weather_index
    weather_index = 100

# Button events detection
GPIO.add_event_detect(up_btn_pin, GPIO.FALLING, callback=handle_hvac, bouncetime=300)
GPIO.add_event_detect(down_btn_pin, GPIO.FALLING, callback=handle_hvac, bouncetime=300)
GPIO.add_event_detect(door_btn_pin, GPIO.FALLING, callback=handle_door, bouncetime=300)

if __name__ == '__main__':
    try:
        print('[Main] BMS System Starting')
        lock = threading.Lock()
        curr = datetime.now()
        hr = curr.hour

        # print('[Main] LCD is ready')
        # t = threading.Thread(target=LCD.lcd_thread)
        # # t3.daemon = True
        # t.start()

        print('[Main] CIMIS Thread Starting')
        t0 = threading.Thread(target=cimis_thread, args=(lock,))
        # t0.daemon = True
        t0.start()
        while(humidity is None):
            time.sleep(1)

        print('[Main] Initializing DHT11 sensor...')
        t1 = threading.Thread(target=dht11_thread, args=(lock,))
        # t1.daemon = True
        t1.start()
        print('[Main] Waiting for initial temperature being calculated...')
        while(temperature is None):
            time.sleep(1)
        print('[Main] Current temperature is ready')
        
        t2 = threading.Thread(target=hvac_thread, args=(lock,))
        # t2.daemon = True
        t2.start()
        time.sleep(3)

        print('[Main] Initializing PIR sensor...')
        t3 = threading.Thread(target=pir_thread, args=(lock,))
        # t3.daemon = True
        t3.start()
        print('[Main] PIR is ready')

        t4 = threading.Thread(target=fire_thread, args=(lock,))
        # t3.daemon = True
        t4.start()
        print('[Main] Fire Thread is ready')

        t5 = threading.Thread(target=security_thread, args=(lock,))
        # t3.daemon = True
        t5.start()
        print('[Main] Secuirty Thread Thread is ready')

        while True:
            if input_available():
                terminated = True
                security_on = False
                break
            # msg = input('[Main] Press <Enter> key to exit the program: \n')
            time.sleep(1)

        # msg = input('[Main] Press <Enter> key to exit the program: \n')
        # terminated = True
        t0.join()
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        # t.join()
        LCD.lcd_terminate()
        GPIO.cleanup()
        print('BMS ended')
    except KeyboardInterrupt:
        terminated = True
        t0.join()
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        # t.join()
        LCD.lcd_terminate()
        GPIO.cleanup()
        print('BMS ended')
    except:
        terminated = True
        t0.join()
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        # t.join()
        LCD.lcd_terminate()
        GPIO.cleanup()
        print('BMS ended')


