"""Scraper module for extracting schedule data from SIS portal."""

from .models import ScheduleEvent
from .scraper import ScheduleScraper

__all__ = ["ScheduleEvent", "ScheduleScraper"]
