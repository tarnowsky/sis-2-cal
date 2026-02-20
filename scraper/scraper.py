"""Schedule scraper for SIS portal."""

import re
from datetime import time
from typing import Optional

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions

from .models import ScheduleEvent


class ScheduleScraper:
    """Scraper for extracting schedule data from SIS portal.
    
    Handles authentication and HTML parsing to extract class schedule
    information from the university's Student Information System.
    Uses Selenium for JavaScript-based authentication.
    """
    
    WAIT_TIMEOUT = 15
    
    def __init__(self, username: str, password: str, headless: bool = True) -> None:
        """Initialize scraper with authentication credentials.
        
        Args:
            username: Portal login username.
            password: Portal login password.
            headless: Run browser in headless mode (default: True).
        """
        self._username = username
        self._password = password
        self._headless = headless
        self._driver: Optional[webdriver.Chrome] = None
        self._soup: Optional[BeautifulSoup] = None
    
    def _init_driver(self) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with appropriate options."""
        options = ChromeOptions()
        if self._headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=pl-PL")
        
        return webdriver.Chrome(options=options)
    
    def _accept_cookies(self) -> None:
        """Accept cookies consent dialog if present."""
        if not self._driver:
            return
        
        try:
            cookie_btn = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cky-btn-accept"))
            )
            cookie_btn.click()
        except TimeoutException:
            pass
    
    def _login(self) -> None:
        """Authenticate with the portal using Selenium."""
        if not self._driver:
            return
        
        try:
            username_field = WebDriverWait(self._driver, self.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.clear()
            username_field.send_keys(self._username)
            
            password_field = self._driver.find_element(By.ID, "password")
            password_field.clear()
            # Use JavaScript to set password value directly (handles special characters better)
            # Also dispatch input event to trigger form validation
            self._driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, password_field, self._password)
            
            submit_btn = self._driver.find_element(By.ID, "submit_button")
            submit_btn.click()
            
            # Click additional submit button after login if present
            try:
                additional_submit = WebDriverWait(self._driver, self.WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input.btn-submit"))
                )
                additional_submit.click()
            except TimeoutException:
                pass
            
            WebDriverWait(self._driver, self.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-bordered"))
            )
            
        except TimeoutException:
            pass
        except NoSuchElementException:
            pass
    
    def fetch_schedule(self, url: str) -> BeautifulSoup:
        """Fetch and parse the schedule page.
        
        Args:
            url: Full URL to the schedule page.
            
        Returns:
            Parsed HTML as BeautifulSoup object.
        """
        self._driver = self._init_driver()
        
        try:
            self._driver.get(url)
            
            self._accept_cookies()
            
            self._login()
            
            self._soup = BeautifulSoup(self._driver.page_source, "lxml")
            return self._soup
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
    
    def _parse_hour(self, hour_str: str) -> time:
        """Parse hour string into time object.
        
        Args:
            hour_str: Hour string like "07:00" or "8:00".
            
        Returns:
            Time object for the hour.
        """
        hour_str = hour_str.strip()
        match = re.search(r"(\d{1,2}):(\d{2})", hour_str)
        
        if match:
            hour, minute = map(int, match.groups())
            return time(hour, minute)
        
        raise ValueError(f"Cannot parse hour: {hour_str}")
    
    def _parse_cell_content(self, cell: Tag) -> list[dict[str, str]]:
        """Parse content of a schedule cell to extract event details.
        
        Args:
            cell: BeautifulSoup Tag representing a table cell.
            
        Returns:
            List of dictionaries with event details (can have multiple events per cell).
        """
        text = cell.get_text(separator=" ", strip=True)
        if not text or text.isspace():
            return []
        
        events: list[dict[str, str]] = []
        
        # Event type mapping (code -> full name)
        event_type_map = {
            "W": "Wykład",
            "L": "Laboratorium",
            "P": "Projekt",
            "S": "Seminarium",
            "C": "Ćwiczenia",
        }
        
        # Reverse mapping for getting codes
        event_code_map = {v: k for k, v in event_type_map.items()}
        
        # Find all subject links - each represents an event
        subject_links = cell.find_all("a", class_="subject_name")
        
        if not subject_links:
            return []
        
        # Get all text content split by <br> for analysis
        html_content = str(cell)
        
        for subject_link in subject_links:
            result: dict[str, str] = {
                "course_name": "",
                "event_type": "Zajęcia",
                "event_type_code": "",
                "instructor": "",
                "room": "",
                "repeat_interval": "1",
                "date_constraint": ""
            }
            
            # Get course name from subject link
            result["course_name"] = subject_link.get_text(strip=True)
            
            # Find the context around this subject link
            # Look for preceding siblings for room and event type
            prev_elements = []
            for sibling in subject_link.previous_siblings:
                if hasattr(sibling, 'get_text'):
                    prev_elements.append(sibling)
                elif isinstance(sibling, str) and sibling.strip():
                    prev_elements.append(sibling)
                if len(prev_elements) > 5:
                    break
            
            # Find room - look for room_name class in previous elements (or inside <b> tags)
            room_found = False
            for elem in prev_elements:
                # Check if element itself is a room_name anchor
                if hasattr(elem, 'get') and elem.get('class') and 'room_name' in elem.get('class', []):
                    result["room"] = elem.get_text(strip=True)
                    room_found = True
                    break
                # Check if element is a <b> containing a room_name anchor
                if hasattr(elem, 'name') and elem.name == 'b':
                    room_anchor = elem.find("a", class_="room_name")
                    if room_anchor:
                        result["room"] = room_anchor.get_text(strip=True)
                        room_found = True
                        break
            
            if not room_found:
                # Fallback: Look for room pattern in bold text before subject
                # Patterns like: "NE 234", "EA 630", "NE AUD1L", "EA AUD.1", "SPNJO Ia"
                for elem in prev_elements:
                    if hasattr(elem, 'name') and elem.name == 'b':
                        room_text = elem.get_text(strip=True)
                        # Match room-like patterns: 1-4 uppercase letters + optional space + alphanumeric
                        if re.match(r'^[A-Z]{1,5}\s*[A-Z0-9][\w\.]*$', room_text, re.IGNORECASE):
                            result["room"] = room_text
                            break
            
            # Find event type [W], [L], [P], [S], [C]
            for elem in prev_elements:
                elem_text = elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem)
                type_match = re.search(r'\[([WLPSC])\]', elem_text)
                if type_match:
                    code = type_match.group(1)
                    result["event_type_code"] = code
                    result["event_type"] = event_type_map.get(code, "Zajęcia")
                    break
            
            # Find instructor - text after subject link
            next_elements = []
            for sibling in subject_link.next_siblings:
                if isinstance(sibling, str) and sibling.strip():
                    next_elements.append(sibling.strip())
                elif hasattr(sibling, 'name'):
                    if sibling.name == 'br':
                        continue
                    elif sibling.name == 'b':
                        # This could be date constraint or next event's room
                        bold_text = sibling.get_text(strip=True)
                        if re.search(r'(do|od)\s+\d{2}\.\d{2}\.\d{4}', bold_text):
                            result["date_constraint"] = bold_text
                        elif 'co 2 tygodn' in bold_text.lower():
                            result["repeat_interval"] = "2"
                        elif re.search(r'co\s+(\d+)\s+tygodn', bold_text.lower()):
                            interval_match = re.search(r'co\s+(\d+)\s+tygodn', bold_text.lower())
                            if interval_match:
                                result["repeat_interval"] = interval_match.group(1)
                        break
                    elif sibling.name == 'a':
                        # Next subject link - stop here
                        break
                    else:
                        next_elements.append(sibling.get_text(strip=True))
            
            # Extract instructor from next elements
            for elem_text in next_elements:
                instructor_match = re.search(
                    r'((?:dr hab\.|dr inż\.|dr|prof\.|mgr inż\.|mgr)\.?\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż-]+)*)',
                    elem_text
                )
                if instructor_match:
                    result["instructor"] = instructor_match.group(1).strip()
                    break
            
            # Check for repeat interval in the remaining text
            full_text = cell.get_text(separator=" ", strip=True).lower()
            if 'co 2 tygodn' in full_text and result["repeat_interval"] == "1":
                # Only if this event has the interval (check context)
                pos = html_content.find(str(subject_link))
                if pos != -1:
                    context = html_content[pos:pos+500].lower()
                    if 'co 2 tygodn' in context:
                        result["repeat_interval"] = "2"
            
            events.append(result)
        
        return events
    
    def parse_events(self) -> list[ScheduleEvent]:
        """Parse schedule table and extract all events.
        
        Returns:
            List of ScheduleEvent objects.
        """
        if not self._soup:
            raise RuntimeError("No schedule data loaded. Call fetch_schedule() first.")
        
        table = self._soup.find("table", class_=re.compile(r"table.*table-bordered.*table-striped"))
        if not table or not isinstance(table, Tag):
            table = self._soup.find("table", class_="table")
        
        if not table or not isinstance(table, Tag):
            raise ValueError("Schedule table not found in the page")
        
        events: list[ScheduleEvent] = []
        hours: list[time] = []
        
        rows = table.find_all("tr")
        
        # Cell grid stores list of events per cell (multiple events possible)
        cell_grid: list[list[list[dict[str, str]]]] = []
        
        for row_idx, row in enumerate(rows):
            if not isinstance(row, Tag):
                continue
            
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            
            first_cell = cells[0]
            first_text = first_cell.get_text(strip=True) if isinstance(first_cell, Tag) else ""
            
            # Check if this row has an hour in first column
            if re.search(r"^\d{1,2}:\d{2}$", first_text):
                try:
                    hour = self._parse_hour(first_text)
                    hours.append(hour)
                except ValueError:
                    continue
                
                row_data: list[list[dict[str, str]]] = []
                for col_idx, cell in enumerate(cells[1:6]):  # Columns 1-5 = Mon-Fri
                    if not isinstance(cell, Tag):
                        row_data.append([])
                        continue
                    
                    cell_events = self._parse_cell_content(cell)
                    row_data.append(cell_events)
                
                cell_grid.append(row_data)
        
        if not hours:
            raise ValueError("No time slots found in schedule table")
        
        # Process cell grid to create events with proper duration
        processed: set[tuple[int, int, str]] = set()  # (row, col, course_name)
        
        for col in range(min(5, len(cell_grid[0]) if cell_grid else 0)):
            row = 0
            while row < len(cell_grid):
                if col >= len(cell_grid[row]):
                    row += 1
                    continue
                
                cell_events = cell_grid[row][col]
                if not cell_events:
                    row += 1
                    continue
                
                for event_data in cell_events:
                    course_key = (row, col, event_data.get("course_name", ""))
                    if course_key in processed:
                        continue
                    
                    # Count how many consecutive rows have the same event
                    span_count = 1
                    next_row = row + 1
                    while next_row < len(cell_grid) and col < len(cell_grid[next_row]):
                        next_cell_events = cell_grid[next_row][col]
                        found_match = False
                        for next_event in next_cell_events:
                            if (next_event.get("course_name") == event_data.get("course_name") and
                                next_event.get("event_type") == event_data.get("event_type") and
                                next_event.get("room") == event_data.get("room")):
                                span_count += 1
                                processed.add((next_row, col, next_event.get("course_name", "")))
                                found_match = True
                                break
                        if not found_match:
                            break
                        next_row += 1
                    
                    processed.add(course_key)
                    
                    start_time = hours[row]
                    # End time is start of next hour slot after span
                    end_row_idx = min(row + span_count, len(hours) - 1)
                    if row + span_count < len(hours):
                        end_time = hours[row + span_count]
                    else:
                        # Last slot - add 1 hour to start
                        end_hour = (hours[end_row_idx].hour + 1) % 24
                        end_time = time(end_hour, hours[end_row_idx].minute)
                    
                    try:
                        event = ScheduleEvent(
                            course_name=event_data.get("course_name", "Unknown"),
                            event_type=event_data.get("event_type", "Zajęcia"),
                            instructor=event_data.get("instructor", ""),
                            room=event_data.get("room", ""),
                            weekday=col,
                            start_time=start_time,
                            end_time=end_time,
                            repeat_interval=int(event_data.get("repeat_interval", "1")),
                            event_type_code=event_data.get("event_type_code", "")
                        )
                        events.append(event)
                    except ValueError as e:
                        print(f"Warning: Skipping invalid event: {e}")
                
                row += 1
        
        return events
