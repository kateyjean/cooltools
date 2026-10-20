from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.edge.options import Options
import sys
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event

##webdriver options & setup
def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")
    driver = webdriver.Edge(options=options)
    return driver

def __main__():
    driver = create_driver()
    driver.get("https://www.visitspacecoast.com/events/")
    wait = WebDriverWait(driver, 10)
    wait.until(lambda d: d.find_element(By.CLASS_NAME, "paging"))

    #find no. of pages we'll need to click thru:
   
    pages = driver.find_elements(By.CLASS_NAME, "js-pagination-link")
    last_page = pages[-1].text

    #grab events from all pages
    #first page:
    event_parents = driver.find_elements(By.CLASS_NAME, "cards")
    titles = driver.find_elements(By.CLASS_NAME, "card-title")
    titlenames = [title.text for title in titles]
    dates = driver.find_elements(By.CLASS_NAME, "card-date")
    date = [date.text for date in dates]
    descriptions = driver.find_elements(By.CLASS_NAME, "card-description")
    description = [description.text for description in descriptions]

    linklist = []
    
    for element in event_parents:
        links = element.find_elements(By.XPATH, ".//a")
        linklist.append(links[1].get_attribute("href"))

    calevents = [list(group) for group in zip(titlenames, date, description, linklist)]

    #go through the rest of the pages and grab events the same way
    for page in range(2, int(last_page) + 1):
        driver.execute_script(f"window.location.href = 'https://www.visitspacecoast.com/events/?app_page={page}/';")
        wait.until(lambda d: d.find_element(By.CLASS_NAME, "paging"))
        event_parents = driver.find_elements(By.CLASS_NAME, "cards")
        titles = driver.find_elements(By.CLASS_NAME, "card-title")
        titlenames = [title.text for title in titles]
        dates = driver.find_elements(By.CLASS_NAME, "card-date")
        date = [date.text for date in dates]
        descriptions = driver.find_elements(By.CLASS_NAME, "card-description")
        description = [description.text for description in descriptions]

        linklist = []
        
        for element in event_parents:
            links = element.find_elements(By.XPATH, ".//a")
            linklist.append(links[1].get_attribute("href"))

        page_events = [list(group) for group in zip(titlenames, date, description, linklist)]
        calevents.extend(page_events)

    # Perform login if necessary
    # add events to calendar if they do not already exist

    # Create a new event
    event_title = "Test Event"
    event_start_time = "2024-06-01T10:00:00"
    event_end_time = "2024-06-01T11:00:00"
    
    calendar = GoogleCalendar()
    event = Event(event_title, start=event_start_time, end=event_end_time)
    calendar.add_event(event)

    print(f"Event '{event_title}' created from {event_start_time} to {event_end_time}.")
    
    driver.quit()