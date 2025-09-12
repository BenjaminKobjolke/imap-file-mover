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
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
import mimetypes
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
    
    def download_image(self, image_url: str, output_dir: str, base_filename: str) -> Optional[str]:
        """
        Download an image from URL and save it to the _resources subdirectory.
        
        Args:
            image_url: URL of the image to download
            output_dir: Base directory (images will be saved in _resources subfolder)
            base_filename: Base filename (without extension) for the markdown file
            
        Returns:
            Optional[str]: Local filename if successful, None if failed
        """
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Create _resources subfolder
            resources_dir = os.path.join(output_dir, "_resources")
            os.makedirs(resources_dir, exist_ok=True)
            
            # Get file extension from content type or URL
            content_type = response.headers.get('content-type', '')
            if 'image/' in content_type:
                ext = mimetypes.guess_extension(content_type)
                if not ext:
                    ext = '.png'  # Default fallback
            else:
                # Try to get extension from URL
                parsed_url = urlparse(image_url)
                path = parsed_url.path
                ext = os.path.splitext(path)[1] if os.path.splitext(path)[1] else '.png'
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            image_filename = f"Pasted image {timestamp}{ext}"
            image_path = os.path.join(resources_dir, image_filename)
            
            # Save the image
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.debug(f"Downloaded image to _resources: {image_filename}")
            return image_filename  # Return just the filename, Obsidian will find it
            
        except Exception as e:
            self.logger.debug(f"Failed to download image {image_url}: {e}")
            return None
    
    def process_embedded_images(self, soup: BeautifulSoup, output_dir: str, base_filename: str, base_url: str = None) -> Dict[str, str]:
        """
        Download embedded images and return a mapping of original URLs to local filenames.
        
        Args:
            soup: BeautifulSoup object containing the HTML
            output_dir: Directory to save images
            base_filename: Base filename for the markdown file
            base_url: Base URL for resolving relative image URLs
            
        Returns:
            Dict[str, str]: Mapping of original image URLs to local filenames
        """
        image_mapping = {}
        
        # Find all img tags
        for img_tag in soup.find_all('img'):
            img_src = img_tag.get('src')
            if not img_src:
                continue
            
            # Convert relative URLs to absolute
            if base_url and not img_src.startswith(('http://', 'https://')):
                img_src = urljoin(base_url, img_src)
            
            # Skip data URLs (base64 encoded images)
            if img_src.startswith('data:'):
                continue
            
            # Download the image
            local_filename = self.download_image(img_src, output_dir, base_filename)
            if local_filename:
                image_mapping[img_src] = local_filename
                
        return image_mapping
    
    def update_markdown_image_links(self, markdown_content: str, image_mapping: Dict[str, str]) -> str:
        """
        Update markdown image links to use Obsidian-style local references.
        
        Args:
            markdown_content: Original markdown content
            image_mapping: Mapping of original URLs to local filenames
            
        Returns:
            str: Updated markdown content
        """
        for original_url, local_filename in image_mapping.items():
            # Replace markdown image syntax with Obsidian-style
            # ![alt text](url) -> ![[filename]]
            markdown_content = re.sub(
                r'!\[([^\]]*)\]\(' + re.escape(original_url) + r'\)',
                f'![[{local_filename}]]',
                markdown_content
            )
            
            # Also handle HTML img tags that might have survived
            markdown_content = re.sub(
                r'<img[^>]*src=["\']' + re.escape(original_url) + r'["\'][^>]*>',
                f'![[{local_filename}]]',
                markdown_content
            )
        
        return markdown_content
    
    def html_to_markdown(self, html_content: str, output_path: str, base_url: str = None) -> bool:
        """
        Convert HTML content to Markdown.
        
        Args:
            html_content: HTML content to convert
            output_path: Path where Markdown should be saved
            base_url: Base URL for resolving relative image URLs
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean HTML before conversion
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Convert only 3+ consecutive <br> tags to reduce excessive spacing
            # Keep single and double <br> tags as they represent intentional line breaks
            html_str = str(soup)
            # Replace 3+ consecutive <br> tags with double <br> to reduce spacing
            html_str = re.sub(r'(<br\s*/?>[\s\n]*){3,}', '<br/><br/>', html_str)
            # Remove empty paragraphs if any
            html_str = re.sub(r'<p>\s*</p>', '', html_str)
            
            # Re-parse the cleaned HTML
            soup = BeautifulSoup(html_str, 'html.parser')
            
            # Process embedded images first (before cleaning)
            base_filename = os.path.splitext(os.path.basename(output_path))[0]
            image_mapping = self.process_embedded_images(soup, output_dir, base_filename, base_url)
            
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
            
            # Update image links to Obsidian-style
            if image_mapping:
                markdown_content = self.update_markdown_image_links(markdown_content, image_mapping)
                self.logger.info(f"Downloaded and linked {len(image_mapping)} images")
            
            # Trim excessive whitespace from the converted markdown
            markdown_content = markdown_content.strip()
            
            # Very aggressive newline cleanup
            # First, normalize line endings
            markdown_content = markdown_content.replace('\r\n', '\n')
            markdown_content = markdown_content.replace('\r', '\n')
            
            # Replace 3+ newlines with exactly 2 (preserve paragraph breaks)
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            # Clean up spaces followed by newlines
            markdown_content = re.sub(r' +\n', '\n', markdown_content)
            
            # Clean up newlines followed by spaces
            markdown_content = re.sub(r'\n +', '\n', markdown_content)
            
            # Remove multiple spaces within lines
            markdown_content = re.sub(r'[ \t]+', ' ', markdown_content)
            
            # Remove empty lines that only contain spaces
            markdown_content = re.sub(r'\n[ \t]+\n', '\n\n', markdown_content)
            
            # Final cleanup: no more than 2 consecutive newlines
            markdown_content = re.sub(r'\n{2,}', '\n\n', markdown_content)
            
            # Remove leading/trailing newlines
            markdown_content = markdown_content.strip()
            
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
    
    def convert_content_with_cid(self, content: str, output_path: str, target_format: str = "pdf", url: str = None, cid_mapping: Dict[str, str] = None) -> bool:
        """
        Convert content to the specified format with CID image mapping support.
        
        Args:
            content: Content to convert (HTML for URL/body, raw text for body)
            output_path: Path where output should be saved
            target_format: Target format ("pdf" or "md")
            url: Optional URL for base path resolution
            cid_mapping: Optional mapping of CID references to local filenames
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        if target_format.lower() == "md":
            # Convert to markdown first
            result = self.html_to_markdown(content, output_path, url)
            
            # If we have CID mappings, update the markdown file to use Obsidian-style links
            if result and cid_mapping:
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                    
                    # Replace any remaining CID references or local filename references
                    for cid_ref, local_filename in cid_mapping.items():
                        # Replace markdown image syntax
                        markdown_content = re.sub(
                            r'!\[([^\]]*)\]\(' + re.escape(local_filename) + r'\)',
                            f'![[{local_filename}]]',
                            markdown_content
                        )
                        # Also handle any remaining CID references
                        markdown_content = re.sub(
                            r'!\[([^\]]*)\]\(' + re.escape(cid_ref) + r'\)',
                            f'![[{local_filename}]]',
                            markdown_content
                        )
                        # Handle plain CID references that might remain
                        markdown_content = markdown_content.replace(cid_ref, local_filename)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                        
                except Exception as e:
                    self.logger.error(f"Failed to update CID references in markdown: {e}")
            
            return result
        elif target_format.lower() == "pdf":
            return self.html_to_pdf(content, output_path, url)
        else:
            self.logger.error(f"Unsupported target format: {target_format}")
            return False
    
    def convert_content(self, content: str, output_path: str, target_format: str = "pdf", url: str = None) -> bool:
        """
        Convert content to the specified format.
        
        Args:
            content: Content to convert (HTML for URL/body, raw text for body)
            output_path: Path where output should be saved
            target_format: Target format ("pdf" or "md")
            url: Optional URL for base path resolution
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        if target_format.lower() == "md":
            return self.html_to_markdown(content, output_path, url)
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