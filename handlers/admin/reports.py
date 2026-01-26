"""Admin report download handlers."""
import os
from aiogram import Router, types, F
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
import data.keyboards as kb
from bot.utils.helpers import smart_edit

router = Router()

REPORTS_BASE_DIR = "reports"
DAILY_DIR = os.path.join(REPORTS_BASE_DIR, "daily")
WEEKLY_DIR = os.path.join(REPORTS_BASE_DIR, "weekly")
MONTHLY_DIR = os.path.join(REPORTS_BASE_DIR, "monthly")


def get_report_files(directory):
    """Get list of report files in a directory, sorted by name (newest first)."""
    if not os.path.exists(directory):
        return []
    files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    files.sort(reverse=True)  # Newest first
    return files


@router.callback_query(F.data == "admin_reports")
async def show_reports_menu(call: types.CallbackQuery):
    """Show reports menu."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📅 التقارير اليومية", callback_data="admin_reports_daily")
    keyboard.button(text="📆 التقارير الأسبوعية", callback_data="admin_reports_weekly")
    keyboard.button(text="📊 التقارير الشهرية", callback_data="admin_reports_monthly")
    keyboard.button(text="🔙 رجوع", callback_data="admin_home")
    keyboard.adjust(1)
    
    await smart_edit(
        call,
        "📊 <b>قائمة التقارير:</b>\n"
        "اختر نوع التقرير لعرض القائمة والتحميل.",
        keyboard.as_markup()
    )


@router.callback_query(F.data == "admin_reports_daily")
async def show_daily_reports(call: types.CallbackQuery):
    """Show list of daily reports."""
    files = get_report_files(DAILY_DIR)
    
    if not files:
        return await smart_edit(
            call,
            "❌ <b>لا توجد تقارير يومية متاحة حالياً.</b>",
            kb.back_btn("admin_reports")
        )
    
    keyboard = InlineKeyboardBuilder()
    for filename in files[:20]:  # Limit to 20 most recent
        # Extract date from filename: daily_sales_YYYY_MM_DD.pdf
        date_str = filename.replace("daily_sales_", "").replace(".pdf", "").replace("_", "-")
        keyboard.button(text=f"📅 {date_str}", callback_data=f"download_daily:{filename}")
    
    keyboard.button(text="🔙 رجوع", callback_data="admin_reports")
    keyboard.adjust(1)
    
    await smart_edit(
        call,
        f"📅 <b>التقارير اليومية ({len(files)}):</b>\n"
        "اختر تقرير للتحميل.",
        keyboard.as_markup()
    )


@router.callback_query(F.data == "admin_reports_weekly")
async def show_weekly_reports(call: types.CallbackQuery):
    """Show list of weekly reports."""
    files = get_report_files(WEEKLY_DIR)
    
    if not files:
        return await smart_edit(
            call,
            "❌ <b>لا توجد تقارير أسبوعية متاحة حالياً.</b>",
            kb.back_btn("admin_reports")
        )
    
    keyboard = InlineKeyboardBuilder()
    for filename in files[:20]:  # Limit to 20 most recent
        # Extract week from filename: weekly_sales_YYYY_WW.pdf
        week_str = filename.replace("weekly_sales_", "").replace(".pdf", "")
        keyboard.button(text=f"📆 Week {week_str}", callback_data=f"download_weekly:{filename}")
    
    keyboard.button(text="🔙 رجوع", callback_data="admin_reports")
    keyboard.adjust(1)
    
    await smart_edit(
        call,
        f"📆 <b>التقارير الأسبوعية ({len(files)}):</b>\n"
        "اختر تقرير للتحميل.",
        keyboard.as_markup()
    )


@router.callback_query(F.data == "admin_reports_monthly")
async def show_monthly_reports(call: types.CallbackQuery):
    """Show list of monthly reports."""
    files = get_report_files(MONTHLY_DIR)
    
    if not files:
        return await smart_edit(
            call,
            "❌ <b>لا توجد تقارير شهرية متاحة حالياً.</b>",
            kb.back_btn("admin_reports")
        )
    
    keyboard = InlineKeyboardBuilder()
    for filename in files[:20]:  # Limit to 20 most recent
        # Extract month from filename: monthly_sales_YYYY_MM.pdf
        month_str = filename.replace("monthly_sales_", "").replace(".pdf", "").replace("_", "-")
        keyboard.button(text=f"📊 {month_str}", callback_data=f"download_monthly:{filename}")
    
    keyboard.button(text="🔙 رجوع", callback_data="admin_reports")
    keyboard.adjust(1)
    
    await smart_edit(
        call,
        f"📊 <b>التقارير الشهرية ({len(files)}):</b>\n"
        "اختر تقرير للتحميل.",
        keyboard.as_markup()
    )


@router.callback_query(F.data.startswith("download_daily:"))
async def download_daily_report(call: types.CallbackQuery):
    """Download a daily report."""
    filename = call.data.split(":", 1)[1]
    file_path = os.path.join(DAILY_DIR, filename)
    
    if not os.path.exists(file_path):
        return await call.answer("❌ الملف غير موجود", show_alert=True)
    
    try:
        document = FSInputFile(file_path)
        await call.message.answer_document(document, caption=f"📅 {filename}")
        await call.answer("✅ تم الإرسال")
    except Exception as e:
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("download_weekly:"))
async def download_weekly_report(call: types.CallbackQuery):
    """Download a weekly report."""
    filename = call.data.split(":", 1)[1]
    file_path = os.path.join(WEEKLY_DIR, filename)
    
    if not os.path.exists(file_path):
        return await call.answer("❌ الملف غير موجود", show_alert=True)
    
    try:
        document = FSInputFile(file_path)
        await call.message.answer_document(document, caption=f"📆 {filename}")
        await call.answer("✅ تم الإرسال")
    except Exception as e:
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("download_monthly:"))
async def download_monthly_report(call: types.CallbackQuery):
    """Download a monthly report."""
    filename = call.data.split(":", 1)[1]
    file_path = os.path.join(MONTHLY_DIR, filename)
    
    if not os.path.exists(file_path):
        return await call.answer("❌ الملف غير موجود", show_alert=True)
    
    try:
        document = FSInputFile(file_path)
        await call.message.answer_document(document, caption=f"📊 {filename}")
        await call.answer("✅ تم الإرسال")
    except Exception as e:
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)
