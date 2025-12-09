"""
PDF generation service for creating PDFs from text content.
Uses ReportLab to generate professional-looking PDFs.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
import io
import logging
import re

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Service for generating PDF documents."""

    def __init__(self):
        """Initialize PDF generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor='#1e40af',
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor='#64748b',
            spaceAfter=20,
            alignment=TA_CENTER
        ))

        # Chat message user style
        self.styles.add(ParagraphStyle(
            name='ChatUser',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor='#1e40af',
            fontName='Helvetica-Bold',
            spaceAfter=6,
            leftIndent=20
        ))

        # Chat message bot style
        self.styles.add(ParagraphStyle(
            name='ChatBot',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor='#059669',
            fontName='Helvetica-Bold',
            spaceAfter=6,
            leftIndent=20
        ))

        # Chat content style
        self.styles.add(ParagraphStyle(
            name='ChatContent',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=16,
            leftIndent=40,
            rightIndent=20
        ))

        # Markdown heading styles
        self.styles.add(ParagraphStyle(
            name='MarkdownH1',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor='#1e40af',
            spaceAfter=12,
            spaceBefore=12
        ))

        self.styles.add(ParagraphStyle(
            name='MarkdownH2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor='#374151',
            spaceAfter=10,
            spaceBefore=10
        ))

        self.styles.add(ParagraphStyle(
            name='MarkdownH3',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor='#4b5563',
            spaceAfter=8,
            spaceBefore=8
        ))

        # Code block style
        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=self.styles['Code'],
            fontSize=9,
            fontName='Courier',
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            spaceBefore=12,
            backColor='#f3f4f6'
        ))

    def generate_from_prompt(self, prompt: str, response: str, source_documents: list = None) -> bytes:
        """
        Generate PDF from a prompt and response.

        Args:
            prompt: User's prompt/question
            response: AI's response (supports markdown formatting)
            source_documents: Optional list of source document filenames to include at the end

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build content
        story = []

        # Title
        title = Paragraph("CaseBase AI Report", self.styles['CustomTitle'])
        story.append(title)

        # Date
        date_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        date_para = Paragraph(date_text, self.styles['CustomSubtitle'])
        story.append(date_para)
        story.append(Spacer(1, 0.5 * inch))

        # Prompt section
        prompt_title = Paragraph("Question:", self.styles['Heading2'])
        story.append(prompt_title)
        story.append(Spacer(1, 0.1 * inch))

        prompt_content = Paragraph(self._escape_html(prompt), self.styles['Normal'])
        story.append(prompt_content)
        story.append(Spacer(1, 0.3 * inch))

        # Response section
        response_title = Paragraph("Answer:", self.styles['Heading2'])
        story.append(response_title)
        story.append(Spacer(1, 0.1 * inch))

        # Convert markdown response to PDF elements
        response_elements = self._markdown_to_pdf_elements(response)
        story.extend(response_elements)

        # Add source documents section if provided
        if source_documents and len(source_documents) > 0:
            story.append(Spacer(1, 0.4 * inch))

            # Add visual separator (horizontal line)
            from reportlab.platypus import HRFlowable
            story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#cbd5e1'), spaceBefore=10, spaceAfter=10))

            # Sources heading
            sources_title = Paragraph("Source Documents", self.styles['Heading2'])
            story.append(sources_title)
            story.append(Spacer(1, 0.15 * inch))

            # Description
            description = Paragraph(
                "This report was generated using information from the following source document(s):",
                self.styles['Normal']
            )
            story.append(description)
            story.append(Spacer(1, 0.15 * inch))

            # List source documents
            for doc_name in source_documents:
                bullet = f"• {doc_name}"
                doc_para = Paragraph(bullet, self.styles['Normal'])
                story.append(doc_para)
                story.append(Spacer(1, 0.05 * inch))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def generate_from_chat_history(self, messages: list, title: str = None) -> bytes:
        """
        Generate PDF from chat conversation history.

        Args:
            messages: List of chat messages with 'role' and 'content'
            title: Optional custom title for the PDF

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build content
        story = []

        # Title
        pdf_title = title or "CaseBase Conversation History"
        title_para = Paragraph(pdf_title, self.styles['CustomTitle'])
        story.append(title_para)

        # Date
        date_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        date_para = Paragraph(date_text, self.styles['CustomSubtitle'])
        story.append(date_para)
        story.append(Spacer(1, 0.5 * inch))

        # Add conversation
        for i, message in enumerate(messages):
            role = message.get('role', 'user')
            content = message.get('content', '')

            # Skip system messages
            if role == 'system':
                continue

            # Add speaker label
            if role == 'user':
                speaker = Paragraph("User:", self.styles['ChatUser'])
            else:
                speaker = Paragraph("Casey (AI Assistant):", self.styles['ChatBot'])

            story.append(speaker)

            # Add message content - check if it contains markdown
            if self._contains_markdown(content):
                # Use markdown converter for formatted content
                content_elements = self._markdown_to_pdf_elements(content)
                for elem in content_elements:
                    story.append(elem)
            else:
                # Plain text
                content_para = Paragraph(self._escape_html(content), self.styles['ChatContent'])
                story.append(content_para)

            # Add spacing between messages
            story.append(Spacer(1, 0.2 * inch))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _contains_markdown(self, text: str) -> bool:
        """
        Check if text contains markdown formatting.

        Args:
            text: Text to check

        Returns:
            bool: True if markdown formatting detected
        """
        markdown_patterns = [
            r'^#{1,3} ',  # Headers
            r'\|.*\|',     # Tables
            r'^\* ',       # Bullet lists
            r'^- ',        # Bullet lists
            r'\*\*.+\*\*', # Bold
            r'```.+```',   # Code blocks
        ]

        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True

        return False

    def _markdown_to_pdf_elements(self, markdown_text: str) -> list:
        """
        Convert markdown text to ReportLab PDF elements.

        Args:
            markdown_text: Markdown formatted text

        Returns:
            list: List of ReportLab flowables (Paragraph, Table, Spacer, etc.)
        """
        elements = []
        lines = markdown_text.split('\n')
        i = 0
        max_iterations = len(lines) * 2  # Safety limit to prevent infinite loops
        iteration_count = 0

        while i < len(lines):
            # Safety check for infinite loops
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.error(f"Infinite loop detected in markdown parsing at line {i}")
                break

            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Heading 1 (# Title)
            if line.startswith('# '):
                text = line[2:].strip()
                elements.append(Paragraph(text, self.styles['MarkdownH1']))
                i += 1

            # Heading 2 (## Subtitle)
            elif line.startswith('## '):
                text = line[3:].strip()
                elements.append(Paragraph(text, self.styles['MarkdownH2']))
                i += 1

            # Heading 3 (### Subsubtitle)
            elif line.startswith('### '):
                text = line[4:].strip()
                elements.append(Paragraph(text, self.styles['MarkdownH3']))
                i += 1

            # Table detection (markdown table with |)
            elif '|' in line:
                # Look ahead to see if this is part of a table
                is_table = False
                if i + 1 < len(lines) and '|' in lines[i + 1]:
                    is_table = True

                if is_table:
                    table_lines = []
                    while i < len(lines) and '|' in lines[i]:
                        table_lines.append(lines[i])
                        i += 1

                    # Parse markdown table
                    if len(table_lines) >= 2:
                        table_element = self._parse_markdown_table(table_lines)
                        if table_element:
                            elements.append(table_element)
                            elements.append(Spacer(1, 0.2 * inch))
                        else:
                            # Table parsing failed, treat as regular text
                            pass
                else:
                    # Single line with |, treat as regular text
                    elements.append(Paragraph(self._escape_html(line), self.styles['Normal']))
                    i += 1

            # Code block (```)
            elif line.strip().startswith('```'):
                code_lines = []
                i += 1  # Skip opening ```
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing ```

                code_text = '\n'.join(code_lines)
                elements.append(Paragraph(self._escape_html(code_text), self.styles['CodeBlock']))
                elements.append(Spacer(1, 0.1 * inch))

            # Bullet list (- item or * item)
            elif line.strip().startswith(('- ', '* ')):
                list_items = []
                while i < len(lines) and lines[i].strip().startswith(('- ', '* ')):
                    item_text = lines[i].strip()[2:]
                    list_items.append(item_text)
                    i += 1

                for item in list_items:
                    # Convert markdown formatting in bullet items
                    item = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', item)  # Bold (must be first)
                    item = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', item)  # Italic (single * not part of **)
                    bullet_text = f"• {item}"
                    elements.append(Paragraph(bullet_text, self.styles['Normal']))

                elements.append(Spacer(1, 0.1 * inch))

            # Regular paragraph
            else:
                # Collect consecutive non-empty lines as a paragraph
                para_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '```')) and '|' not in lines[i] and not lines[i].strip().startswith(('-', '*')):
                    para_lines.append(lines[i].strip())
                    i += 1

                if para_lines:
                    para_text = ' '.join(para_lines)
                    # Convert markdown bold (**text**) to HTML bold (must be first)
                    para_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', para_text)
                    # Convert markdown italic (*text*) to HTML italic (single * not part of **)
                    para_text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', para_text)
                    elements.append(Paragraph(para_text, self.styles['Normal']))
                    elements.append(Spacer(1, 0.1 * inch))
                else:
                    # If we couldn't collect any lines, skip this line to avoid infinite loop
                    i += 1

        return elements

    def _parse_markdown_table(self, table_lines: list) -> Table:
        """
        Parse markdown table into ReportLab Table.

        Args:
            table_lines: Lines containing markdown table

        Returns:
            Table: ReportLab Table object or None
        """
        try:
            # Parse table rows
            data = []
            for i, line in enumerate(table_lines):
                # Skip separator line (|---|---|)
                if i == 1 and re.match(r'^\s*\|[\s\-:|]+\|\s*$', line):
                    continue

                # Split by | and clean up
                cells = [cell.strip() for cell in line.split('|')]
                # Remove empty first/last cells (from leading/trailing |)
                cells = [cell for cell in cells if cell]

                if cells:
                    data.append(cells)

            if not data:
                return None

            # Create table
            table = Table(data)

            # Style the table
            table_style = TableStyle([
                # Header row (first row)
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

                # Grid
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ])

            table.setStyle(table_style)
            return table

        except Exception as e:
            logger.error(f"Error parsing markdown table: {str(e)}")
            return None

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters for ReportLab.

        Args:
            text: Text to escape

        Returns:
            str: Escaped text
        """
        # Replace special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('\n', '<br/>')

        return text


# Global PDF generator instance
pdf_generator = PDFGenerator()
