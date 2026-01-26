"""Report generation service."""
import os
from datetime import datetime, timedelta
import logging
import services.database as database
import services.settings as settings
from .pdf_builder import build_sales_report_pdf

logger = logging.getLogger(__name__)

# Report directories
REPORTS_BASE_DIR = "reports"
DAILY_DIR = os.path.join(REPORTS_BASE_DIR, "daily")
WEEKLY_DIR = os.path.join(REPORTS_BASE_DIR, "weekly")
MONTHLY_DIR = os.path.join(REPORTS_BASE_DIR, "monthly")


def ensure_directories():
    """Ensure report directories exist."""
    for directory in [DAILY_DIR, WEEKLY_DIR, MONTHLY_DIR]:
        os.makedirs(directory, exist_ok=True)


def calculate_order_totals(orders):
    """Calculate total sales from orders."""
    total_usd = 0.0
    category_breakdown = {}
    
    for order in orders:
        price = float(order.get('product', {}).get('price', 0))
        qty = int(order.get('qty', 1))
        total_usd += price * qty
        
        # Category breakdown
        category = order.get('product', {}).get('category_name', 'Unknown')
        category_breakdown[category] = category_breakdown.get(category, 0) + 1
    
    rate = settings.get_setting("exchange_rate")
    total_syp = int(total_usd * rate)
    
    return total_usd, total_syp, category_breakdown


def generate_daily_report(target_date=None):
    """
    Generate daily report for a specific date.
    If target_date is None, uses yesterday.
    """
    ensure_directories()
    
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    
    # Set time to start of day
    start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Check if report already exists
    date_str = start_date.strftime("%Y_%m_%d")
    last_report = database.get_last_report_date("daily")
    if last_report == date_str:
        logger.info(f"Daily report for {date_str} already generated, skipping.")
        return None
    
    # Get orders for the day
    orders = database.get_orders_by_date_range(start_date, end_date)
    
    if not orders:
        logger.info(f"No completed orders found for {date_str}, skipping report generation.")
        return None
    
    # Calculate totals
    total_usd, total_syp, category_breakdown = calculate_order_totals(orders)
    
    # Prepare report data
    report_data = {
        'title': 'Daily Sales Report',
        'date_range': start_date.strftime("%Y-%m-%d"),
        'total_orders': len(orders),
        'total_sales_usd': total_usd,
        'total_sales_syp': total_syp,
        'category_breakdown': category_breakdown if category_breakdown else None
    }
    
    # Generate PDF
    filename = f"daily_sales_{date_str}.pdf"
    file_path = os.path.join(DAILY_DIR, filename)
    
    try:
        build_sales_report_pdf(file_path, report_data)
        database.update_last_report_date("daily", date_str)
        logger.info(f"Daily report generated: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return None


def generate_weekly_report(target_week_start=None):
    """
    Generate weekly report for a specific week.
    If target_week_start is None, uses last week (Monday to Sunday).
    """
    ensure_directories()
    
    if target_week_start is None:
        # Get last Monday
        today = datetime.now()
        days_since_monday = (today.weekday() + 1) % 7
        if days_since_monday == 0:
            days_since_monday = 7
        last_monday = today - timedelta(days=days_since_monday + 7)
        target_week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Week ends on Sunday
    week_end = target_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Check if report already exists
    year = target_week_start.year
    week_num = target_week_start.isocalendar()[1]
    date_str = f"{year}_{week_num:02d}"
    last_report = database.get_last_report_date("weekly")
    if last_report == date_str:
        logger.info(f"Weekly report for {date_str} already generated, skipping.")
        return None
    
    # Get orders for the week
    orders = database.get_orders_by_date_range(target_week_start, week_end)
    
    if not orders:
        logger.info(f"No completed orders found for week {date_str}, skipping report generation.")
        return None
    
    # Calculate totals
    total_usd, total_syp, category_breakdown = calculate_order_totals(orders)
    
    # Prepare report data
    date_range_str = f"{target_week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
    report_data = {
        'title': 'Weekly Sales Report',
        'date_range': date_range_str,
        'total_orders': len(orders),
        'total_sales_usd': total_usd,
        'total_sales_syp': total_syp,
        'category_breakdown': category_breakdown if category_breakdown else None
    }
    
    # Generate PDF
    filename = f"weekly_sales_{date_str}.pdf"
    file_path = os.path.join(WEEKLY_DIR, filename)
    
    try:
        build_sales_report_pdf(file_path, report_data)
        database.update_last_report_date("weekly", date_str)
        logger.info(f"Weekly report generated: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        return None


def generate_monthly_report(target_month=None):
    """
    Generate monthly report for a specific month.
    If target_month is None, uses last month.
    """
    ensure_directories()
    
    if target_month is None:
        # Get first day of last month
        today = datetime.now()
        if today.month == 1:
            last_month = today.replace(year=today.year - 1, month=12, day=1)
        else:
            last_month = today.replace(month=today.month - 1, day=1)
        target_month = last_month
    
    # Set to first day of month
    month_start = target_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get last day of month
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
    month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Check if report already exists
    date_str = month_start.strftime("%Y_%m")
    last_report = database.get_last_report_date("monthly")
    if last_report == date_str:
        logger.info(f"Monthly report for {date_str} already generated, skipping.")
        return None
    
    # Get orders for the month
    orders = database.get_orders_by_date_range(month_start, month_end)
    
    if not orders:
        logger.info(f"No completed orders found for month {date_str}, skipping report generation.")
        return None
    
    # Calculate totals
    total_usd, total_syp, category_breakdown = calculate_order_totals(orders)
    
    # Prepare report data
    date_range_str = f"{month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}"
    report_data = {
        'title': 'Monthly Sales Report',
        'date_range': date_range_str,
        'total_orders': len(orders),
        'total_sales_usd': total_usd,
        'total_sales_syp': total_syp,
        'category_breakdown': category_breakdown if category_breakdown else None
    }
    
    # Generate PDF
    filename = f"monthly_sales_{date_str}.pdf"
    file_path = os.path.join(MONTHLY_DIR, filename)
    
    try:
        build_sales_report_pdf(file_path, report_data)
        database.update_last_report_date("monthly", date_str)
        logger.info(f"Monthly report generated: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        return None
