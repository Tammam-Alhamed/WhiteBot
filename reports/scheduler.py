"""Scheduler for automated report generation."""
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
import config
from .service import generate_daily_report, generate_weekly_report, generate_monthly_report

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_report_to_admins(bot: Bot, file_path: str, report_type: str, date_range: str, total_usd: float, total_syp: int):
    """Send generated report to all admins."""
    try:
        from aiogram.types import FSInputFile
        
        caption = (
            f"📊 <b>{report_type} Report</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📅 Date Range: {date_range}\n"
            f"💰 Total Sales:\n"
            f"🇺🇸 {total_usd:.2f} $\n"
            f"🇸🇾 {total_syp:,} ل.س"
        )
        
        document = FSInputFile(file_path)
        
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=document,
                    caption=caption,
                    parse_mode="HTML"
                )
                logger.info(f"Report sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send report to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending report to admins: {e}")


async def daily_report_job(bot: Bot):
    """Job to generate and send daily report."""
    logger.info("Starting daily report generation...")
    try:
        file_path = generate_daily_report()
        if file_path:
            # Extract date from filename
            filename = file_path.split(os.sep)[-1]
            date_str = filename.replace("daily_sales_", "").replace(".pdf", "")
            
            # Get report totals for caption
            from reports.service import calculate_order_totals
            from services.database import get_orders_by_date_range
            
            target_date = datetime.strptime(date_str, "%Y_%m_%d")
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            orders = get_orders_by_date_range(start_date, end_date)
            total_usd, total_syp, _ = calculate_order_totals(orders)
            
            await send_report_to_admins(
                bot, file_path, "Daily", date_str.replace("_", "-"),
                total_usd, total_syp
            )
        else:
            logger.info("No daily report generated (no orders or already exists)")
    except Exception as e:
        logger.error(f"Error in daily report job: {e}")


async def weekly_report_job(bot: Bot):
    """Job to generate and send weekly report."""
    logger.info("Starting weekly report generation...")
    try:
        file_path = generate_weekly_report()
        if file_path:
            # Extract week info from filename
            filename = file_path.split(os.sep)[-1]
            week_str = filename.replace("weekly_sales_", "").replace(".pdf", "")
            
            # Get report totals for caption
            from reports.service import calculate_order_totals
            from services.database import get_orders_by_date_range
            
            year, week = week_str.split("_")
            # Calculate week start (Monday of that week)
            # ISO week: week 1 is the first week with a Thursday
            year_int = int(year)
            week_int = int(week)
            # Get January 4th of the year (always in week 1)
            jan4 = datetime(year_int, 1, 4)
            # Get the Monday of that week
            monday_of_week1 = jan4 - timedelta(days=jan4.weekday())
            # Calculate target Monday
            target_date = monday_of_week1 + timedelta(weeks=week_int - 1)
            week_end = target_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
            orders = get_orders_by_date_range(target_date, week_end)
            total_usd, total_syp, _ = calculate_order_totals(orders)
            
            date_range = f"{target_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
            await send_report_to_admins(
                bot, file_path, "Weekly", date_range,
                total_usd, total_syp
            )
        else:
            logger.info("No weekly report generated (no orders or already exists)")
    except Exception as e:
        logger.error(f"Error in weekly report job: {e}")


async def monthly_report_job(bot: Bot):
    """Job to generate and send monthly report."""
    logger.info("Starting monthly report generation...")
    try:
        file_path = generate_monthly_report()
        if file_path:
            # Extract month info from filename
            filename = file_path.split(os.sep)[-1]
            month_str = filename.replace("monthly_sales_", "").replace(".pdf", "")
            
            # Get report totals for caption
            from reports.service import calculate_order_totals
            from services.database import get_orders_by_date_range
            
            year, month = month_str.split("_")
            month_start = datetime(int(year), int(month), 1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            orders = get_orders_by_date_range(month_start, month_end)
            total_usd, total_syp, _ = calculate_order_totals(orders)
            
            date_range = f"{month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}"
            await send_report_to_admins(
                bot, file_path, "Monthly", date_range,
                total_usd, total_syp
            )
        else:
            logger.info("No monthly report generated (no orders or already exists)")
    except Exception as e:
        logger.error(f"Error in monthly report job: {e}")


def setup_scheduler(bot: Bot):
    """Setup and start the scheduler."""
    # Daily report at 00:00
    scheduler.add_job(
        daily_report_job,
        trigger=CronTrigger(hour=0, minute=0),
        args=[bot],
        id='daily_report',
        replace_existing=True
    )
    
    # Weekly report every Monday at 00:00
    scheduler.add_job(
        weekly_report_job,
        trigger=CronTrigger(day_of_week='mon', hour=0, minute=0),
        args=[bot],
        id='weekly_report',
        replace_existing=True
    )
    
    # Monthly report on 1st of each month at 00:00
    scheduler.add_job(
        monthly_report_job,
        trigger=CronTrigger(day=1, hour=0, minute=0),
        args=[bot],
        id='monthly_report',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Report scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()
    logger.info("Report scheduler stopped")
