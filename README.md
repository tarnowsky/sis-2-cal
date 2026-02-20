# SIS Schedule to iCalendar Converter

An ETL pipeline for extracting academic schedule data from the Gdansk University of Technology (Politechnika Gdanska) Student Information System (SIS) and converting it to iCalendar (.ics) format.

---

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.15+-43B02A?style=flat&logo=selenium&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-4.12+-orange?style=flat)
![iCalendar](https://img.shields.io/badge/iCalendar-RFC%205545-blue?style=flat)

---

## Overview

This tool automates the extraction of class schedules from the SIS portal and generates standard iCalendar files compatible with Google Calendar, Apple Calendar, Microsoft Outlook, and other calendar applications.

### Features

- Web scraping with Selenium WebDriver for JavaScript-rendered content
- HTML parsing with BeautifulSoup4
- Automatic detection of multi-hour class blocks
- Support for biweekly and custom repeat intervals
- Academic hour conversion (45-minute periods starting 15 minutes past the hour)
- Extensible transformer architecture for additional output formats

---

## Requirements

- Python 3.13 or higher
- Google Chrome browser
- ChromeDriver (automatically managed by Selenium)

### Dependencies

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
icalendar>=5.0.0
selenium>=4.15.0
```

---

## Installation

```bash
git clone <repository-url>
cd pg-schedule-to-ical
pip install -r requirements.txt
```

---

## Usage

### Basic Usage

```bash
python3 sis2iCal.py --url <SCHEDULE_URL> --start-date <YYYY-MM-DD>
```

### Full Options

```bash
python3 sis2iCal.py \
    --url https://sis.eti.pg.edu.pl/Planner/ScheduleForGroup/<GROUP_ID>/<SEMESTER> \
    --start-date 2026-02-23 \
    --end-date 2026-06-30 \
    -o my_schedule \
    -a
```

### Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--url` | | Yes | URL of the SIS schedule page |
| `--start-date` | | Yes | Semester start date (YYYY-MM-DD) |
| `--end-date` | | No | Semester end date (default: Jun 30 or Jan 31) |
| `--output` | `-o` | No | Output filename (default: schedule.ics) |
| `--apply-academic-hours` | `-a` | No | Convert to academic hours (45 min blocks) |

### Academic Hours Mode

When `-a` is specified, the tool converts schedule times to actual academic hours:

| Schedule Time | Academic Time | Duration |
|---------------|---------------|----------|
| 08:00-09:00 | 08:15-09:00 | 45 min |
| 08:00-10:00 | 08:15-09:45 | 90 min |
| 08:00-11:00 | 08:15-10:30 | 135 min |

---

## Project Structure

```
pg-schedule-to-ical/
├── sis2iCal.py              # Main entry point
├── requirements.txt         # Python dependencies
├── scraper/
│   ├── __init__.py
│   ├── models.py            # ScheduleEvent dataclass
│   └── scraper.py           # ScheduleScraper class (Selenium + BS4)
└── transformer/
    ├── __init__.py
    ├── base.py              # BaseTransformer abstract class
    └── ical_transformer.py  # ICalTransformer implementation
```

---

## Output Format

The generated .ics file contains:

- **SUMMARY**: `[TYPE] Course Name` (e.g., `[W] Machine Learning`)
- **LOCATION**: Room identifier (e.g., `NE 234`, `EA AUD.1`)
- **DESCRIPTION**: Instructor name and title
- **RRULE**: Weekly recurrence with interval support

### Event Type Codes

| Code | Type |
|------|------|
| W | Wyklad (Lecture) |
| L | Laboratorium (Laboratory) |
| C | Cwiczenia (Exercises) |
| P | Projekt (Project) |
| S | Seminarium (Seminar) |

---

## Disclaimer

**FOR ACADEMIC USE ONLY**

This tool is intended exclusively for personal academic schedule management by students of Gdansk University of Technology. Users are responsible for:

- Complying with the university's terms of service
- Using valid personal credentials only
- Not distributing or sharing extracted schedule data
- Verifying schedule accuracy with official university sources

The authors assume no responsibility for any misuse of this tool or inaccuracies in the generated calendar data. Always refer to the official SIS portal for authoritative schedule information.

---

## License

This project is provided for educational purposes. Use at your own discretion.

---

## Technical Notes

- The scraper uses Selenium WebDriver in headless mode for authentication
- Cookie consent is handled automatically
- Session management supports the university's SSO flow
- HTML parsing targets the specific table structure of the SIS portal
- The transformer architecture allows extension to other calendar formats (Google Calendar API, JSON, etc.)
