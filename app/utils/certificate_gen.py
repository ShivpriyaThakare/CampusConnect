import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_certificate_pdf(student_name, event_title, club_name, event_date_str, certificate_uid):
    """
    Generates a high-quality PDF Certificate of Participation using ReportLab.
    Returns a BytesIO buffer containing the PDF binary data.
    """
    buffer = io.BytesIO()
    
    # Page dimensions (Landscape Letter)
    page_width, page_height = landscape(letter)
    
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    
    # --- Background & Outer Border ---
    c.setFillColor(colors.HexColor('#F8FAFC'))
    c.rect(0, 0, page_width, page_height, fill=True, stroke=False)
    
    # Primary Outer Border (Deep Indigo)
    c.setStrokeColor(colors.HexColor('#4F46E5'))
    c.setLineWidth(4)
    c.rect(20, 20, page_width - 40, page_height - 40)
    
    # Inner Accent Border (Gold/Amber)
    c.setStrokeColor(colors.HexColor('#D97706'))
    c.setLineWidth(1.5)
    c.rect(28, 28, page_width - 56, page_height - 56)
    
    # Corner Ornaments
    corner_size = 15
    for x, y in [(35, 35), (page_width - 35, 35), (35, page_height - 35), (page_width - 35, page_height - 35)]:
        c.setFillColor(colors.HexColor('#4F46E5'))
        c.circle(x, y, 4, fill=True, stroke=False)

    # --- Header Banner ---
    c.setFillColor(colors.HexColor('#4F46E5'))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2.0, page_height - 75, "CAMPUS CONNECT • OFFICIAL CERTIFICATE")
    
    # Gold decorative divider line
    c.setStrokeColor(colors.HexColor('#F59E0B'))
    c.setLineWidth(2)
    c.line(page_width / 2.0 - 150, page_height - 85, page_width / 2.0 + 150, page_height - 85)
    
    # Certificate Title
    c.setFillColor(colors.HexColor('#1E293B'))
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(page_width / 2.0, page_height - 140, "CERTIFICATE OF PARTICIPATION")
    
    c.setFillColor(colors.HexColor('#64748B'))
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2.0, page_height - 170, "This certificate is proudly presented to")
    
    # --- Recipient Name ---
    c.setFillColor(colors.HexColor('#0F172A'))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2.0, page_height - 225, student_name.upper())
    
    # Underline for recipient name
    name_width = c.stringWidth(student_name.upper(), "Helvetica-Bold", 28)
    c.setStrokeColor(colors.HexColor('#6366F1'))
    c.setLineWidth(1.5)
    c.line((page_width - name_width) / 2.0 - 10, page_height - 235, (page_width + name_width) / 2.0 + 10, page_height - 235)
    
    # --- Event & Achievement Details ---
    c.setFillColor(colors.HexColor('#334155'))
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_width / 2.0, page_height - 280, f"for successfully attending and participating in the event")
    
    c.setFillColor(colors.HexColor('#4338CA'))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(page_width / 2.0, page_height - 315, f'"{event_title}"')
    
    c.setFillColor(colors.HexColor('#475569'))
    c.setFont("Helvetica", 13)
    c.drawCentredString(page_width / 2.0, page_height - 345, f"Organized by {club_name} on {event_date_str}")
    
    # --- Seal & Signature Lines ---
    y_sig = 110
    
    # Left Signature: Club Coordinator
    c.setStrokeColor(colors.HexColor('#94A3B8'))
    c.setLineWidth(1)
    c.line(100, y_sig + 30, 260, y_sig + 30)
    c.setFillColor(colors.HexColor('#334155'))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(180, y_sig + 15, "Club Coordinator")
    c.setFont("Helvetica", 9)
    c.drawCentredString(180, y_sig, club_name)
    
    # Center Seal Emblem
    c.setFillColor(colors.HexColor('#EEF2FF'))
    c.setStrokeColor(colors.HexColor('#4F46E5'))
    c.setLineWidth(2)
    c.circle(page_width / 2.0, y_sig + 25, 30, fill=True, stroke=True)
    c.setFillColor(colors.HexColor('#4338CA'))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(page_width / 2.0, y_sig + 28, "VERIFIED")
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_width / 2.0, y_sig + 16, "CAMPUS")
    
    # Right Signature: Campus Administrator
    c.setStrokeColor(colors.HexColor('#94A3B8'))
    c.setLineWidth(1)
    c.line(page_width - 260, y_sig + 30, page_width - 100, y_sig + 30)
    c.setFillColor(colors.HexColor('#334155'))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(page_width - 180, y_sig + 15, "Campus Administrator")
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width - 180, y_sig, "CampusConnect Portal")
    
    # --- Footer Verification UID ---
    c.setFillColor(colors.HexColor('#94A3B8'))
    c.setFont("Courier", 9)
    c.drawCentredString(page_width / 2.0, 45, f"Certificate Verification ID: {certificate_uid}")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer
