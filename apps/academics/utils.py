import requests
from bs4 import BeautifulSoup
import re

def scrape_portal(admission_number, password):
    """
    Scrapes the Daystar Student Portal to find the student's current unit codes.
    Returns a list of unique course codes (e.g., ['ACS401', 'BIL112']).
    """
    LOGIN_URL = "https://student.daystar.ac.ke/"
    # The screenshot shows capitalization: StudentTimeTable
    TIMETABLE_URL = "https://student.daystar.ac.ke/Course/StudentTimeTable"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": "https://student.daystar.ac.ke",
        "Referer": "https://student.daystar.ac.ke/",
    })

    try:
        # 1. Start Session
        # Hit the root to get initial load-balancer/session cookies
        session.get("https://student.daystar.ac.ke/", timeout=15)
        
        # 2. AJAX Login (Mirroring portal's jQuery AJAX exactly)
        LOGIN_API_URL = "https://student.daystar.ac.ke/Login/LoginUser"
        
        login_payload = {
            "userlogin": {
                "Username": admission_number,
                "Password": password
            }
        }
        
        # Exact headers and spacing from the portal's script
        headers = {
            "Content-Type": "application/json; charset = utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://student.daystar.ac.ke/",
            "Origin": "https://student.daystar.ac.ke"
        }

        login_response = session.post(
            LOGIN_API_URL, 
            json=login_payload, 
            headers=headers,
            timeout=15, 
        )
        
        # 3. Check for Login Success
        try:
            res_json = login_response.json()
            if not res_json.get("success"):
                portal_msg = res_json.get("message") or "Invalid credentials"
                return {"error": f"Portal Sync failed: {portal_msg}. Please check your credentials."}
        except Exception as e:
            # SAVE FOR DEBUGGING
            with open("failed_login_portal.html", "w", encoding="utf-8") as f:
                f.write(login_response.text)
            
            return {"error": f"Portal authentication failed (Non-JSON response). check failed_login_portal.html"}

        # 4. Navigate to Timetable
        # Try primary URL case
        timetable_response = session.get(TIMETABLE_URL, timeout=15)
        
        # Verify we didn't get kicked back to login
        if "Account/Login" in timetable_response.url or "Login/Index" in timetable_response.url:
             # Fallback: try the other capitalization
             alt_url = "https://student.daystar.ac.ke/Course/StudentTimetable"
             timetable_response = session.get(alt_url, timeout=15)
             
             if "Account/Login" in timetable_response.url or "Login/Index" in timetable_response.url:
                 # SAVE FAILED HTML FOR DEBUGGING
                 with open("failed_sync_portal.html", "w", encoding="utf-8") as f:
                     f.write(timetable_response.text)
                 return {"error": "Portal authentication failed (AJAX response ok but session not established). check failed_sync_portal.html"}

        # 5. Parse Timetable
        soup = BeautifulSoup(timetable_response.text, "html.parser")
        
        # Broad Search for any table containing "Unit" and "Period" or "Day"
        table = None
        all_tables = soup.find_all("table")
        for t in all_tables:
            text = t.get_text().upper()
            if "UNIT" in text and ("DAY" in text or "PERIOD" in text or "LECTURE ROOM" in text):
                table = t
                break
        
        if not table:
            # SAVE FOR DEBUGGING
            with open("failed_table_portal.html", "w", encoding="utf-8") as f:
                f.write(timetable_response.text)
            return {"error": f"Timetable table not found on the portal page (Found {len(all_tables)} tables). Check failed_table_portal.html"}
        
        if not table:
            return {"error": "Timetable table not found on the portal page."}

        course_codes = set()
        rows = table.find_all("tr")
        
        collecting = False
        for row in rows:
            row_text = row.get_text(separator=" ", strip=True).upper()
            
            # 1. Start collecting after the "My Timetable" header row
            if "MY TIMETABLE" in row_text:
                collecting = True
                continue
            
            # 2. Stop collecting when we hit the "Courses in Timetable" section
            if "COURSES IN TIMETABLE" in row_text:
                break
            
            if not collecting:
                continue

            cells = row.find_all("td")
            if len(cells) >= 2:
                # 1. Extract base code (e.g., ACS-413 -> ACS413)
                unit_text = cells[0].get_text(strip=True).upper()
                clean_unit = re.sub(r'[^A-Z0-9]', '', unit_text)
                
                # 2. Extract section identifier (e.g., A-ATH -> A)
                section_text = cells[1].get_text(strip=True).upper()
                # Take the part before the hyphen
                section_part = section_text.split('-')[0].strip()
                
                # 3. Combine for precise matching (e.g., ACS413A)
                if len(clean_unit) >= 3:
                    full_code = f"{clean_unit}{section_part}"
                    course_codes.add(full_code)

        return list(course_codes)

    except requests.exceptions.RequestException as e:
        return {"error": f"Portal connection failed: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred during sync: {str(e)}"}
