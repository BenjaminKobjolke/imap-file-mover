"""
HTML converter with redirect handling - supports PDF and Markdown output.
"""
import re
import os
import tempfile
import requests
import pdfkit
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from typing import Optional, Tuple
from pathlib import Path
from src.utils.logger import Logger


class HtmlConverter:
    """
    Handles downloading HTML content and converting it to PDF or Markdown.
    """
    
    def __init__(self, logger: Optional[Logger] = None, wkhtmltopdf_path: Optional[str] = None):
        """
        Initialize the converter.
        
        Args:
            logger: Optional logger instance
            wkhtmltopdf_path: Optional path to wkhtmltopdf executable
        """
        self.logger = logger or Logger()
        self.wkhtmltopdf_path = wkhtmltopdf_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_meta_refresh_url(self, html_content: str) -> Optional[str]:
        """
        Extract URL from meta refresh tag.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            Optional[str]: The redirect URL if found, None otherwise
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for meta refresh tag
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if meta_refresh:
            content = meta_refresh.get('content', '')
            # Extract URL from content like "0;url='https://...'"
            match = re.search(r"url=['\"]?([^'\"]+)['\"]?", content, re.IGNORECASE)
            if match:
                url = match.group(1)
                self.logger.info(f"Found meta refresh redirect to: {url}")
                return url
        
        return None
    
    def download_html_with_redirects(self, url: str, max_redirects: int = 5) -> Tuple[str, str]:
        """
        Download HTML content, following meta refresh redirects.
        
        Args:
            url: URL to download
            max_redirects: Maximum number of redirects to follow
            
        Returns:
            Tuple[str, str]: (final_url, html_content)
            
        Raises:
            Exception: If download fails or too many redirects
        """
        current_url = url
        redirect_count = 0
        
        while redirect_count < max_redirects:
            try:
                self.logger.debug(f"Downloading HTML from: {current_url}")
                response = self.session.get(current_url, timeout=30)
                response.raise_for_status()
                
                html_content = response.text
                
                # Check for meta refresh redirect
                redirect_url = self.extract_meta_refresh_url(html_content)
                
                if redirect_url:
                    # Handle relative URLs
                    if not redirect_url.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        redirect_url = urljoin(current_url, redirect_url)
                    
                    self.logger.info(f"Following meta refresh redirect to: {redirect_url}")
                    current_url = redirect_url
                    redirect_count += 1
                else:
                    # No more redirects, return the content
                    self.logger.info(f"Downloaded HTML from final URL: {current_url}")
                    return current_url, html_content
                    
            except requests.RequestException as e:
                self.logger.error(f"Failed to download HTML from {current_url}: {e}")
                raise
        
        raise Exception(f"Too many redirects (>{max_redirects}) when downloading {url}")
    
    def html_to_pdf(self, html_content: str, output_path: str, url: str = None) -> bool:
        """
        Convert HTML content to PDF.
        
        Args:
            html_content: HTML content to convert
            output_path: Path where PDF should be saved
            url: Optional URL for base path resolution
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Configure pdfkit options
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            
            # If we have a URL, add base tag to HTML for proper resource resolution
            if url:
                soup = BeautifulSoup(html_content, 'html.parser')
                if not soup.find('base'):
                    base_tag = soup.new_tag('base', href=url)
                    if soup.head:
                        soup.head.insert(0, base_tag)
                    else:
                        head = soup.new_tag('head')
                        head.append(base_tag)
                        if soup.html:
                            soup.html.insert(0, head)
                        else:
                            soup.insert(0, head)
                    html_content = str(soup)
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(html_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Convert to PDF using pdfkit
                # Note: pdfkit requires wkhtmltopdf to be installed
                config = None
                
                # First, check if a path was provided in configuration
                if self.wkhtmltopdf_path and os.path.exists(self.wkhtmltopdf_path):
                    config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
                    self.logger.info(f"Using configured wkhtmltopdf path: {self.wkhtmltopdf_path}")
                else:
                    # Try to find wkhtmltopdf in common locations if not in PATH
                    import platform
                    if platform.system() == 'Windows':
                        # Common Windows installation paths
                        possible_paths = [
                            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
                            r'C:\wkhtmltopdf\bin\wkhtmltopdf.exe'
                        ]
                        for path in possible_paths:
                            if os.path.exists(path):
                                config = pdfkit.configuration(wkhtmltopdf=path)
                                self.logger.info(f"Found wkhtmltopdf at: {path}")
                                break
                
                if config:
                    pdfkit.from_file(tmp_file_path, output_path, options=options, configuration=config)
                else:
                    pdfkit.from_file(tmp_file_path, output_path, options=options)
                self.logger.important(f"Successfully converted HTML to PDF: {output_path}")
                return True
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to convert HTML to PDF: {e}")
            self.logger.error("Note: wkhtmltopdf must be installed and in PATH for PDF conversion")
            return False
    
    def html_to_markdown(self, html_content: str, output_path: str) -> bool:
        """
        Convert HTML content to Markdown.
        
        Args:
            html_content: HTML content to convert
            output_path: Path where Markdown should be saved
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Clean HTML before conversion
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'meta', 'link', 'head']):
                element.decompose()
            
            # Remove inline style attributes from all elements
            for element in soup.find_all(attrs={'style': True}):
                del element['style']
            
            # Remove class attributes (often contain CSS class names)
            for element in soup.find_all(attrs={'class': True}):
                del element['class']
            
            # Remove other common HTML attributes that don't translate well to markdown
            unwanted_attrs = ['id', 'data-.*', 'aria-.*', 'role', 'tabindex', 'dir', 'lang']
            for attr_pattern in unwanted_attrs:
                for element in soup.find_all():
                    attrs_to_remove = []
                    for attr in element.attrs:
                        if re.match(attr_pattern, attr, re.IGNORECASE):
                            attrs_to_remove.append(attr)
                    for attr in attrs_to_remove:
                        del element[attr]
            
            # Get cleaned HTML
            cleaned_html = str(soup)
            
            # Convert HTML to Markdown with better options
            markdown_content = md(
                cleaned_html,
                heading_style="ATX",  # Use # for headings instead of underlines
                bullets="-"  # Use - for bullet points
            )
            
            # Trim excessive whitespace from the converted markdown
            markdown_content = markdown_content.strip()
            
            # Remove excessive empty lines (more than 2 consecutive newlines)
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            # Remove any remaining CSS-like content that might have leaked through
            markdown_content = re.sub(r'{[^}]*}', '', markdown_content)  # Remove CSS rules
            markdown_content = re.sub(r'@media[^{]*{[^}]*}', '', markdown_content)  # Remove media queries
            markdown_content = re.sub(r'#[a-zA-Z_][a-zA-Z0-9_-]*\s*{[^}]*}', '', markdown_content)  # Remove ID selectors
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.important(f"Successfully converted HTML to Markdown: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to convert HTML to Markdown: {e}")
            return False
    
    def convert_content(self, content: str, output_path: str, target_format: str = "pdf", url: str = None) -> bool:
        """
        Convert content to the specified format.
        
        Args:
            content: Content to convert (HTML for URL/body, raw text for body)
            output_path: Path where output should be saved
            target_format: Target format ("pdf" or "md")
            url: Optional URL for base path resolution (for PDF)
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        if target_format.lower() == "md":
            return self.html_to_markdown(content, output_path)
        elif target_format.lower() == "pdf":
            return self.html_to_pdf(content, output_path, url)
        else:
            self.logger.error(f"Unsupported target format: {target_format}")
            return False
    
    def download_and_convert(self, url: str, output_path: str, target_format: str = "pdf") -> bool:
        """
        Download HTML from URL (following redirects) and convert to specified format.
        
        Args:
            url: URL to download
            output_path: Path where output should be saved
            target_format: Target format ("pdf" or "md")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Download HTML with redirect handling
            final_url, html_content = self.download_html_with_redirects(url)
            
            # Convert to target format
            return self.convert_content(html_content, output_path, target_format, final_url)
            
        except Exception as e:
            self.logger.error(f"Failed to download and convert {url}: {e}")
            return False