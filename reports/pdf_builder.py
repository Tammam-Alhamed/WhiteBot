"""PDF builder utility for generating sales reports."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from datetime import datetime


# Try to use Arabic font if available, otherwise fallback to default
def setup_fonts():
    """Setup fonts for Arabic text support."""
    try:
        # Try common Arabic fonts
        arabic_fonts = [
            "Arial Unicode MS",
            "Tahoma",
            "DejaVu Sans"
        ]
        # For now, use default fonts
        # In production, you might want to embed an Arabic font file
        pass
    except:
        pass


def format_price(price):
    """Format price for display."""
    return f"{float(price):.2f}"


def build_sales_report_pdf(file_path, report_data):
    """
    Build a PDF sales report.
    
    Args:
        file_path: Path where PDF will be saved
        report_data: Dict with keys:
            - title: Report title
            - date_range: Date range string
            - total_orders: Total completed orders count
            - total_sales_usd: Total sales in USD
            - total_sales_syp: Total sales in SYP
            - category_breakdown: Optional dict {category: count}
            - payment_method_breakdown: Optional dict {method: count}
    """
    setup_fonts()
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Section header style
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    # Normal text style
    normal_style = styles['Normal']
    
    # Title
    title = Paragraph(report_data['title'], title_style)
    story.append(title)
    story.append(Spacer(1, 0.5*cm))
    
    # Date range
    date_range = Paragraph(f"<b>Date Range:</b> {report_data['date_range']}", subtitle_style)
    story.append(date_range)
    story.append(Spacer(1, 0.5*cm))
    
    # Summary section
    summary_data = [
        ['Metric', 'Value'],
        ['Total Completed Orders', str(report_data['total_orders'])],
        ['Total Sales (USD)', f"${format_price(report_data['total_sales_usd'])}"],
        ['Total Sales (SYP)', f"{report_data['total_sales_syp']:,} ل.س"]
    ]
    
    summary_table = Table(summary_data, colWidths=[8*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    story.append(Paragraph("<b>Summary</b>", section_style))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Category breakdown (if available)
    if report_data.get('category_breakdown'):
        cat_data = [['Category', 'Orders Count']]
        for cat, count in sorted(report_data['category_breakdown'].items()):
            cat_data.append([cat, str(count)])
        
        cat_table = Table(cat_data, colWidths=[8*cm, 6*cm])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ebf5fb')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#aed6f1'))
        ]))
        
        story.append(Paragraph("<b>Category Breakdown</b>", section_style))
        story.append(cat_table)
        story.append(Spacer(1, 0.5*cm))
    
    # Payment method breakdown (if available)
    if report_data.get('payment_method_breakdown'):
        pm_data = [['Payment Method', 'Orders Count']]
        for method, count in sorted(report_data['payment_method_breakdown'].items()):
            pm_data.append([method, str(count)])
        
        pm_table = Table(pm_data, colWidths=[8*cm, 6*cm])
        pm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#d5f4e6')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#82e0aa'))
        ]))
        
        story.append(Paragraph("<b>Payment Method Breakdown</b>", section_style))
        story.append(pm_table)
    
    # Footer
    story.append(Spacer(1, 1*cm))
    footer = Paragraph(
        f"<i>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#7f8c8d'))
    )
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    return file_path
