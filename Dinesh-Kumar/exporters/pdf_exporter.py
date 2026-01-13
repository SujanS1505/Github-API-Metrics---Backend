from fpdf import FPDF
import datetime

class PDFExporter:
    @staticmethod
    def export(data, output_path, owner_repo):
        """
        Export metrics to a PDF file with premium HR-ready styling.
        """
        pdf = FPDF()
        
        # Colors
        PRIMARY_COLOR = (44, 62, 80)    # Dark Slate / Navy
        ACCENT_COLOR = (52, 152, 219)   # Professional Blue
        TEXT_COLOR = (50, 50, 50)
        LIGHT_BG = (245, 247, 250)      # Very Light Gray for stripes
        WHITE = (255, 255, 255)

        # --- COVER PAGE ---
        pdf.add_page()
        
        # Background accent
        pdf.set_fill_color(*PRIMARY_COLOR)
        pdf.rect(0, 0, 210, 80, 'F')
        
        # Title
        pdf.set_y(30)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Arial", 'B', 24)
        pdf.cell(0, 15, "Repository Technical Audit", 0, 1, 'C')
    

        # Repo Info Box
        pdf.set_y(100)
        pdf.set_text_color(*TEXT_COLOR)
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Repository: {owner_repo}", 0, 1, 'C')
        
        pdf.set_font("Arial", '', 12)
        # Use simple UTC time to avoid ZoneInfo dependency issues
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        pdf.cell(0, 10, f"Generated: {timestamp}", 0, 1, 'C')   

        # Executive Summary Mockup
        pdf.set_y(150)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(20, 150, 170, 40, 'F')
        pdf.set_xy(25, 155)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Executive Summary", 0, 1)
        pdf.set_xy(25, 165)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(160, 6, "This report provides a detailed analysis of the repository's scale, technology stack, and code quality indicators. The data is aggregated from the complete file history and contents.")

        # Footer
        pdf.set_y(260)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Confidential - For Internal Review Only", 0, 0, 'C')


        # --- METRICS PAGE ---
        pdf.add_page()
        pdf.set_text_color(*TEXT_COLOR)

        def section_header(title):
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(*PRIMARY_COLOR)
            pdf.cell(0, 10, title, 0, 1, 'L')
            # Underline
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_draw_color(*ACCENT_COLOR)
            pdf.set_line_width(1)
            pdf.line(x, y, x + 190, y)
            pdf.ln(2)

        def metric_row(name, value, fill=False):
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(*TEXT_COLOR)
            if fill:
                pdf.set_fill_color(*LIGHT_BG)
                pdf.rect(pdf.get_x(), pdf.get_y(), 190, 8, 'F')
            
            pdf.cell(140, 8, name, 0, 0, 'L')
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(50, 8, str(value), 0, 1, 'R')

        # 1. SCALE
        section_header("Scale & Activity")
        total_loc = data.get('total_loc', 0)
        num_files = data.get('num_files', 0)
        avg_size = data.get('avg_file_size', 0)
        max_size = data.get('largest_file_size', 0)
        
        metric_row("Total Lines of Code (LOC)", f"{total_loc:,}", True)
        metric_row("Total Files", f"{num_files:,}", False)
        metric_row("Average File Size", f"{avg_size:.1f} bytes", True)
        metric_row("Largest File Size", f"{max_size:,} bytes", False)
        metric_row("Lines Added (Recent)", f"{data.get('LOC added', 0):,}", True)
        metric_row("Lines Deleted (Recent)", f"{data.get('LOC deleted', 0):,}", False)
        metric_row("Net Growth", f"{data.get('Net LOC growth', 0):,}", True)
        metric_row("Total Commits (Recent)", f"{data.get('num_commits', 0):,}", False)

        # 2. TECHNOLOGY STACK
        pdf.ln(5)
        section_header("Technology Stack")
        
        langs = data.get('language_percentage', {})
        # Sort by percentage
        sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)
        
        fill_row = True
        for lang, pct in sorted_langs:
            if pct < 1.0: continue # Skip minor langs
            
            metric_row(lang, f"{pct:.1f}%", fill_row)
            
            # Visual Bar
            bar_x = 10
            bar_y = pdf.get_y() - 1 # Nudge up
            bar_w = 190 * (pct / 100.0)
            
            # Draw distinct color for bar
            pdf.set_fill_color(*ACCENT_COLOR)
            pdf.rect(bar_x, bar_y, bar_w, 1, 'F')
            
            fill_row = not fill_row

        # 3. CODE QUALITY
        pdf.ln(5)
        section_header("Quality Indicators")
        
        # Format ratios
        comment_ratio = data.get('comment_to_code_ratio', 0) * 100
        test_ratio = data.get('test_to_production_ratio', 0) * 100
        dupe_ratio = data.get('duplicate_code_percentage', 0)
        
        metric_row("Comment Density", f"{comment_ratio:.1f}%", True)
        metric_row("Test-to-Code Ratio", f"{test_ratio:.1f}%", False)
        metric_row("Duplicate Code", f"{dupe_ratio:.1f}%", True)
        metric_row("Binary Files", str(data.get('binary_files_count', 0)), False)
        metric_row("Generated Files", str(data.get('generated_files_count', 0)), True)
        metric_row("Configuration Files", str(data.get('config_files_count', 0)), False)


        try:
            pdf.output(output_path)
            print(f"PDF successfully written to {output_path}")
        except Exception as e:
            print(f"Failed to write PDF: {e}")
