import schedule
import time
from get_generation_info import InfoGetter
import os

def job():
    info_getter = InfoGetter()
    path = 'output.csv'
    info_getter.get_generation_info(path)
    info_getter.upload(path)
    os.remove(path)

schedule.every().day.at("23:30").do(job)
schedule.every().day.at("08:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)