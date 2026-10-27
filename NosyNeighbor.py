from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.options import Options
import os
import re
from datetime import date,timedelta
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from google.oauth2 import service_account


##webdriver options & setup
def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")
    driver = webdriver.Firefox(options=options)
    return driver

def next_month(y, m):
    return (y + 1, 1) if (m == 12) else (y, m + 1)

def parse_range(text, year=None):
        #make sure my dates are datey enough and handle the multimonth span cases:
    MONTHS = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}
    PAT= re.compile(r'([a-z]{3})\w*\.?\s+(\d{1,2})(?:st|nd|rd|th)?'                       # "sep 8th"
    r'(?:\s*-\s*(?:([a-z]{3})\w*\.?\s+)?(\d{1,2})(?:st|nd|rd|th)?)?'      # "-31st" or "-oct 2nd"
    r'(?:\s*,?\s*(\d{4}))?', re.IGNORECASE)                                 # ", 2023"
    year = year or date.today().year
    m = PAT.search(text)
    if not m:
        raise ValueError(f"Can't parse date: {text!r}")
    sm, sd = MONTHS[m.group(1).capitalize()], int(m.group(2))
    start = date(year, sm, sd)

    if m.group(4) is None:                      # single day, no range
        return start, start

    ed = int(m.group(4))
    if m.group(3):                              # explicit end month
        return start, date(year, MONTHS[m.group(3)].capitalize(), ed)

    y, em = year, sm                            # no end month: try this month, then next
    for _ in range(2):
        try:
            end = date(y, em, ed)
            if end >= start:
                return start, end
        except ValueError:
            pass
        y, em = next_month(y, em)
    raise ValueError(f"Bad range: {text!r}")

def main():
    driver = create_driver()
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = service_account.Credentials.from_service_account_file(os.path.join(BASE, 'service_account.json'), scopes=SCOPES)
    try:
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
        datelist = [date.text for date in dates]
        descriptions = driver.find_elements(By.CLASS_NAME, "card-description")
        description = [description.text for description in descriptions]

        linklist = []
        
        for element in event_parents:
            links = element.find_elements(By.XPATH, ".//a")
            linklist.append(links[1].get_attribute("href"))

        calevents = [list(group) for group in zip(titlenames, datelist, description, linklist)]

        #go through the rest of the pages and grab events the same way
        for page in range(2, int(last_page) + 1):
            driver.execute_script(f"window.location.href = 'https://www.visitspacecoast.com/events/?app_page={page}/';")
            wait.until(lambda d: d.find_element(By.CLASS_NAME, "paging"))
            event_parents = driver.find_elements(By.CLASS_NAME, "cards")
            titles = driver.find_elements(By.CLASS_NAME, "card-title")
            titlenames = [title.text for title in titles]
            dates = driver.find_elements(By.CLASS_NAME, "card-date")
            datelist = [date.text for date in dates]
            descriptions = driver.find_elements(By.CLASS_NAME, "card-description")
            description = [description.text for description in descriptions]

            linklist = []
            
            for element in event_parents:
                links = element.find_elements(By.XPATH, ".//a")
                linklist.append(links[1].get_attribute("href"))

            page_events = [list(group) for group in zip(titlenames, datelist, description, linklist)]
            calevents.extend(page_events)
    finally: 
        driver.quit()
    # add events to calendar if they do not already exist
    CALENDAR_ID = os.environ["CALENDAR_ID"]
    BASE = os.path.dirname(os.path.abspath(__file__))
    calendar = GoogleCalendar(CALENDAR_ID, credentials=creds)
   # token_path=os.path.join(BASE, 'token.pickle'),)
    # grab list of currently existing events
    #parse dates and add events to calendar if they do not already exist
    parsed = []
    for title, datelist, description, linklist in calevents:
    # Parse the date range
        start, end = parse_range(datelist)
        parsed.append((title, start, end+timedelta(days=1), f"{description}\n\n{linklist}"))
        if not parsed:
            return
    
        earliest = min(p[1] for p in parsed)
        latest = max(p[2] for p in parsed)
        existing = {(e.summary, e.start) for e in calendar.get_events(time_min=earliest, time_max=latest)}
    
        for title, start, end, desc in parsed:
            if (title, start) in existing:
                continue
            calendar.add_event(Event(title, start=start, end=end, description=desc))
            
    

if __name__ == "__main__":
    main()