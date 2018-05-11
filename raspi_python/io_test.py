import time
import pigpio

piio = pigpio.pi()

print("Wait 60 and then pump")
time.sleep(60)
print("Pump!")
piio.write(13,1)
time.sleep(10)
piio.write(13,0)
print("--Done")