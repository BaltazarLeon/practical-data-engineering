import requests
import time
import os
from urllib.parse import urljoin
import json

class Inmuebles24Scraper:
    def __init__(self, cf_clearance_cookie, user_agent):
        """
        Initialize the scraper with Cloudflare clearance cookie and user agent
        
        Args:
            cf_clearance_cookie (str): The cf_clearance cookie value from Unflare
            user_agent (str): User agent string from Unflare response
        """
        self.session = requests.Session()
        self.base_url = "https://inmuebles24.com"
        
        # Set up headers with the cf_clearance cookie and user agent
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set the cf_clearance cookie
        self.session.cookies.set('cf_clearance', cf_clearance_cookie, domain='.inmuebles24.com')
    
    def get_unflare_cookie(self, unflare_url="http://localhost:5002"):
        """
        Get cf_clearance cookie from Unflare service
        
        Args:
            unflare_url (str): URL of your Unflare service
            
        Returns:
            tuple: (cf_clearance_cookie, user_agent) or (None, None) if failed
        """
        try:
            target_url = "https://www.inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-5.html"
                         
            payload = {
                "url": target_url,
                "timeout": 60000,
                }
            
            print("Getting cf_clearance cookie from Unflare...")
            response = requests.post(f"{unflare_url}/scrape", 
                                   json=payload, 
                                   )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract cf_clearance cookie
                cf_clearance = None
                for cookie in data.get('cookies', []):
                    if cookie['name'] == 'cf_clearance':
                        cf_clearance = cookie['value']
                        break
                
                user_agent = data.get('headers', {}).get('user-agent', '')
                
                if cf_clearance and user_agent:
                    print(f"Successfully got cf_clearance cookie: {cf_clearance[:20]}...")
                    return cf_clearance, user_agent
                else:
                    print("cf_clearance cookie not found in response")
                    return None, None
            else:
                print(f"Unflare request failed: {response.status_code}")
                print(response.text)
                return None, None
                
        except Exception as e:
            print(f"Error getting cookie from Unflare: {e}")
            return None, None
    
    def scrape_page(self, page_num):
        """
        Scrape a specific page
        
        Args:
            page_num (int): Page number to scrape
            
        Returns:
            str: HTML content or None if failed
        """
        url = f"https://inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-{page_num}.html"
        
        try:
            print(f"Scraping page {page_num}...")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                print(f"Successfully scraped page {page_num}")
                return response.text
            elif response.status_code == 403:
                print(f"Access denied for page {page_num} - cookie may have expired")
                return None
            else:
                print(f"Failed to scrape page {page_num}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
            return None
    
    def save_html(self, html_content, page_num, output_dir="scraped_pages"):
        """
        Save HTML content to file
        
        Args:
            html_content (str): HTML content to save
            page_num (int): Page number for filename
            output_dir (str): Directory to save files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filename = f"inmuebles24_page_{page_num}.html"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Saved page {page_num} to {filepath}")
        except Exception as e:
            print(f"Error saving page {page_num}: {e}")
    
    def scrape_pages(self, start_page=5, end_page=10, delay=2):
        """
        Scrape pages from start_page to end_page
        
        Args:
            start_page (int): Starting page number
            end_page (int): Ending page number (inclusive)
            delay (int): Delay between requests in seconds
        """
        print(f"Starting to scrape pages {start_page} to {end_page}")
        
        for page_num in range(start_page, end_page + 1):
            html_content = self.scrape_page(page_num)
            
            if html_content:
                self.save_html(html_content, page_num)
            else:
                print(f"Skipping page {page_num} due to error")
            
            # Add delay between requests to be respectful
            if page_num < end_page:
                print(f"Waiting {delay} seconds before next request...")
                time.sleep(delay)
        
        print("Scraping completed!")

def main():
    """
    Main function to run the scraper
    """
    # Option 1: Get cookie automatically from Unflare
    scraper_temp = Inmuebles24Scraper("", "")
    cf_clearance, user_agent = scraper_temp.get_unflare_cookie()
    
    if cf_clearance and user_agent:
        # Initialize scraper with the cookie
        scraper = Inmuebles24Scraper(cf_clearance, user_agent)
        
        # Scrape pages 5 to 10
        scraper.scrape_pages(start_page=5, end_page=10, delay=3)
    else:
        print("Failed to get cf_clearance cookie. Please check your Unflare service.")
        print("\nAlternatively, you can manually provide the cookie:")
        print("1. Run Unflare and get the cf_clearance cookie")
        print("2. Modify the script to use manual_run() function below")

def manual_run():
    """
    Alternative function if you want to manually provide the cookie
    Replace the values below with your actual cookie and user agent
    """
    # Replace these with actual values from Unflare
    CF_CLEARANCE_COOKIE = "your_cf_clearance_cookie_here"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    scraper = Inmuebles24Scraper(CF_CLEARANCE_COOKIE, USER_AGENT)
    scraper.scrape_pages(start_page=5, end_page=10, delay=3)

if __name__ == "__main__":
    main()
    
    # Uncomment the line below if you want to use manual cookie input
    # manual_run()