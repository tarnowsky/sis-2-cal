#!/usr/bin/env python3
"""SIS Schedule to iCalendar converter.

ETL pipeline that scrapes academic schedule data from SIS portal
and generates an iCalendar (.ics) file.
"""

import argparse
import getpass
import sys
from datetime import date, datetime

from scraper import ScheduleScraper
from transformer import ICalTransformer


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
        )


def get_default_end_date() -> date:
    """Calculate default end date based on current month.
    
    Returns June 30 if current month is January-June,
    January 31 of next year if current month is July-December.
    """
    today = date.today()
    
    if today.month < 7:
        return date(today.year, 6, 30)
    else:
        return date(today.year + 1, 1, 31)


def get_credentials() -> tuple[str, str]:
    """Prompt user for login credentials.
    
    Returns:
        Tuple of (username, password).
    """
    print("SIS Portal Authentication")
    print("-" * 30)
    
    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    return username, password


def main() -> None:
    """Main entry point for the ETL pipeline."""
    parser = argparse.ArgumentParser(
        description="Convert SIS schedule to iCalendar format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sis2iCal.py --url https://sis.eti.pg.edu.pl/Planner/ScheduleForGroup/M2501IM-0/1 --start-date 2026-02-23
  python3 sis2iCal.py --url <URL> --start-date 2026-02-23 --end-date 2026-06-30 --output my_schedule.ics
        """
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="URL of the schedule page to scrape"
    )
    
    parser.add_argument(
        "--start-date",
        type=parse_date,
        required=True,
        help="Start date of the semester (format: YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=None,
        help="End date of the semester (format: YYYY-MM-DD). "
             "Default: June 30 (spring semester) or January 31 (fall semester)"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="schedule.ics",
        help="Output file path (default: schedule.ics)"
    )
    
    parser.add_argument(
        "-a", "--apply-academic-hours",
        action="store_true",
        help="Apply academic hour logic: 45 min per hour, starts 15 min after full hour"
    )
    
    args = parser.parse_args()
    
    # Ensure output file has .ics extension
    output_path = args.output
    if not output_path.lower().endswith(".ics"):
        output_path = f"{output_path}.ics"
    
    end_date = args.end_date if args.end_date else get_default_end_date()
    
    if args.start_date >= end_date:
        print("Error: Start date must be before end date.", file=sys.stderr)
        sys.exit(1)
    
    username, password = get_credentials()
    
    print(f"\nFetching schedule from: {args.url}")
    
    try:
        scraper = ScheduleScraper(username, password)
        scraper.fetch_schedule(args.url)
        events = scraper.parse_events()
        
        print(f"Found {len(events)} schedule events.")
        
        if not events:
            print("Warning: No events found. The output file will be empty.")
        
        transformer = ICalTransformer(apply_academic_hours=args.apply_academic_hours)
        transformer.transform(events, args.start_date, end_date)
        transformer.save(output_path)
        
        print(f"Schedule saved to: {output_path}")
        print(f"Period: {args.start_date} to {end_date}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
