import openpyxl
import re
from datetime import datetime, timedelta
from decimal import Decimal

def parse_date_string(date_str):
    if not date_str: return None
    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', str(date_str))
    if match:
        day, month, year = match.groups()
        if len(year) == 2: year = '20' + year
        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            return None
    return None

def parse_time_range(time_str):
    """Returns (start_time_obj, end_time_obj, duration_decimal)"""
    if not time_str: return None, None, 0
    s = str(time_str).upper().replace('.', ':').replace(' ', '')
    try:
        parts = s.split('-')
        if len(parts) != 2: return None, None, 0
        
        def parse_t(t):
            for fmt in ('%I:%M%p', '%H:%M'):
                try:
                    return datetime.strptime(t, fmt)
                except ValueError: continue
            return None

        start_dt = parse_t(parts[0])
        end_dt = parse_t(parts[1])
        
        if not start_dt or not end_dt: return None, None, 0
        
        diff = (end_dt - start_dt).total_seconds()
        if diff < 0: diff += 86400
        duration = Decimal(diff) / Decimal(3600)
        
        return start_dt.time(), end_dt.time(), duration
    except:
        return None, None, 0

def process_exam_excel(file_path):
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    all_exams = []

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        rows = list(sheet.iter_rows(values_only=True))
        i = 0
        col_map = {} 

        while i < len(rows):
            row = rows[i]
            row_str = " ".join([str(x).upper() for x in row if x])

            # 1. HEADER ROW
            if "MONDAY" in row_str or "TUESDAY" in row_str or "WEDNESDAY" in row_str:
                col_map = {}
                active_date = None
                for idx, cell in enumerate(row):
                    new_date = parse_date_string(cell)
                    if new_date: active_date = new_date
                    if active_date: col_map[idx] = {'date': active_date}

                # 2. TIME ROW
                if i + 1 < len(rows):
                    time_row = rows[i+1]
                    final_map = {}
                    for idx, meta in col_map.items():
                        if idx < len(time_row):
                            s_time, e_time, dur = parse_time_range(time_row[idx])
                            if dur > 0:
                                meta['start'] = s_time
                                meta['end'] = e_time
                                meta['duration'] = dur
                                final_map[idx] = meta
                    col_map = final_map
                    i += 1 

            # 3. DATA ROW
            elif col_map and row[0]:
                venue = str(row[0]).strip()
                if venue.upper() not in ['ROOM', 'NOTE:', 'LUNCH', 'BREAK']:
                    for col_idx, meta in col_map.items():
                        if col_idx < len(row) and row[col_idx]:
                            val = str(row[col_idx]).strip()
                            if val.upper() in ['CHAPEL', 'BREAK', '', 'NONE']: continue
                            
                            for code in val.replace('&', '/').split('/'):
                                code = code.strip()
                                if len(code) > 2:
                                    # CRITICAL: Combine Date + Time here
                                    # We combine the date from header with start_time
                                    full_datetime = datetime.combine(meta['date'], meta['start'])

                                    all_exams.append({
                                        'course_code': code,
                                        'title': code,
                                        'date': full_datetime, # Now it's a DateTime object!
                                        'end_time': meta['end'],
                                        'venue': venue,
                                        'duration_hours': meta['duration']
                                    })
            i += 1
    return all_exams