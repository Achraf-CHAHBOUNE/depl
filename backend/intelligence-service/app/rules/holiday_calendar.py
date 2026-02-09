from datetime import date, timedelta
from typing import Set


class MoroccanHolidayCalendar:
    """
    Moroccan legal holidays and business day calculations.
    
    Fixed holidays are defined. Islamic holidays vary by lunar calendar
    and should be updated annually by configuration.
    """
    
    # Fixed Moroccan holidays (Gregorian calendar)
    FIXED_HOLIDAYS = {
        (1, 1): "Nouvel An",
        (1, 11): "Manifeste de l'indépendance",
        (5, 1): "Fête du Travail",
        (7, 30): "Fête du Trône",
        (8, 14): "Journée de l'oued Ed-Dahab",
        (8, 20): "Révolution du Roi et du Peuple",
        (8, 21): "Fête de la Jeunesse",
        (11, 6): "Marche Verte",
        (11, 18): "Fête de l'Indépendance",
    }
    
    def __init__(self, islamic_holidays: Set[date] = None):
        """
        Args:
            islamic_holidays: Set of Islamic holiday dates for current year(s)
                             Should include: Aid Al-Fitr, Aid Al-Adha, 
                             Nouvel An Hégirien, Aid Al-Mawlid
        """
        self.islamic_holidays = islamic_holidays or set()
    
    def is_weekend(self, d: date) -> bool:
        """Check if date is Saturday or Sunday"""
        return d.weekday() in (5, 6)
    
    def is_fixed_holiday(self, d: date) -> bool:
        """Check if date is a fixed Moroccan holiday"""
        return (d.month, d.day) in self.FIXED_HOLIDAYS
    
    def is_islamic_holiday(self, d: date) -> bool:
        """Check if date is an Islamic holiday"""
        return d in self.islamic_holidays
    
    def is_business_day(self, d: date) -> bool:
        """
        Check if date is a business day.
        Returns False for weekends and holidays.
        """
        return not (
            self.is_weekend(d) or 
            self.is_fixed_holiday(d) or 
            self.is_islamic_holiday(d)
        )
    
    def next_business_day(self, d: date) -> date:
        """
        Get the next business day after given date.
        If date is already a business day, return it.
        """
        current = d
        
        # Safety limit to prevent infinite loops
        max_iterations = 30
        iterations = 0
        
        while not self.is_business_day(current) and iterations < max_iterations:
            current += timedelta(days=1)
            iterations += 1
        
        if iterations >= max_iterations:
            # Fallback: just skip weekends
            while current.weekday() in (5, 6):
                current += timedelta(days=1)
        
        return current
    
    def add_business_days(self, start_date: date, days: int) -> date:
        """
        Add business days to a date, skipping weekends and holidays.
        
        Args:
            start_date: Starting date
            days: Number of business days to add
        
        Returns:
            Resulting date
        """
        current = start_date
        days_added = 0
        
        while days_added < days:
            current += timedelta(days=1)
            if self.is_business_day(current):
                days_added += 1
        
        return current
    
    @classmethod
    def create_for_year(cls, year: int, islamic_holidays: Set[date] = None):
        """
        Factory method to create calendar for a specific year.
        
        Args:
            year: Year to create calendar for
            islamic_holidays: Islamic holidays for that year
        """
        return cls(islamic_holidays=islamic_holidays or set())