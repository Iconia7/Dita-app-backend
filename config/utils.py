import re
from datetime import datetime
from decimal import Decimal

import openpyxl
from django.utils import timezone


def parse_date_string(date_str):
    if not date_str:
        return None
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", str(date_str))
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            return None
    return None


def parse_time_range(time_str):
    """Returns (start_time_obj, end_time_obj, duration_decimal)"""
    if not time_str:
        return None, None, 0
    s = str(time_str).upper().replace(".", ":").replace(" ", "")
    try:
        parts = s.split("-")
        if len(parts) != 2:
            return None, None, 0

        def parse_t(t):
            for fmt in ("%I:%M%p", "%H:%M"):
                try:
                    return datetime.strptime(t, fmt)
                except ValueError:
                    continue
            return None

        start_dt = parse_t(parts[0])
        end_dt = parse_t(parts[1])

        if not start_dt or not end_dt:
            return None, None, 0

        diff = (end_dt - start_dt).total_seconds()
        if diff < 0:
            diff += 86400
        duration = Decimal(diff) / Decimal(3600)

        return start_dt.time(), end_dt.time(), duration
    except Exception as e:
        print(f"Error parsing time range: {e}")
        return None, None, 0


def expand_course_codes(val):
    """
    Expands shorthand course codes like BIL112X/Y into ['BIL112X', 'BIL112Y']
    and LLD345/407 into ['LLD345', 'LLD407'].
    """
    if not val:
        return []

    # Split by common separators including newlines, slashes, ampersands, commas, semicolons
    import re
    parts = re.split(r"[/&\n,;]", str(val))
    expanded = []
    last_full_code = ""

    for p in parts:
        p = p.strip()
        if not p or p.upper() in ["CHAPEL", "BREAK", "NONE"]:
            continue

        # Handle suffix expansion: e.g. BIL112X/Y -> BIL112Y
        if len(p) <= 2 and last_full_code and len(last_full_code) > len(p):
            prefix = last_full_code[: -len(p)]
            full_code = prefix + p
            expanded.append(full_code)
        # Handle numeric expansion: e.g. LLD345/407 -> LLD407
        elif p.isdigit() and len(p) == 3 and last_full_code:
            match = re.match(r"^([A-Z]+)", last_full_code.upper())
            if match:
                letters = match.group(1)
                full_code = letters + p
                expanded.append(full_code)
            else:
                expanded.append(p)
        else:
            expanded.append(p)
            last_full_code = p

    return expanded


def process_exam_excel(file_path):
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    all_exams = []
    DAYS_SET = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"}

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        # Normalize sheet name for venue prefix (clean up extra spaces)
        display_sheet_name = sheet_name.replace(" ", "").upper()

        rows = list(sheet.iter_rows(values_only=True))
        i = 0
        col_map = {}

        while i < len(rows):
            row = rows[i]
            if not row:
                i += 1
                continue

            row_text = " ".join([str(x).upper() for x in row if x])

            # 1. HEADER ROW DETECTION
            # Check if any cell in the row contains a day from our set
            is_header = any(day in row_text for day in DAYS_SET)

            if is_header:
                col_map = {}
                active_date = None
                for idx, cell in enumerate(row):
                    if not cell:
                        # Propagate active date across merged cells
                        if active_date:
                            col_map[idx] = {"date": active_date}
                        continue

                    new_date = parse_date_string(cell)
                    if new_date:
                        active_date = new_date
                        col_map[idx] = {"date": active_date}
                    elif active_date:
                        col_map[idx] = {"date": active_date}

                # 2. TIME ROW (Expected immediately below header)
                if i + 1 < len(rows):
                    i += 1  # Move to the time row
                    time_row = rows[i]
                    final_map = {}
                    for idx, meta in col_map.items():
                        if idx < len(time_row) and time_row[idx]:
                            s_time, e_time, dur = parse_time_range(time_row[idx])
                            if dur > 0:
                                meta["start"] = s_time
                                meta["end"] = e_time
                                meta["duration"] = dur
                                final_map[idx] = meta
                    col_map = final_map

            # 3. DATA ROW
            elif col_map and row[0]:
                venue_label = str(row[0]).strip()
                if venue_label.upper() not in ["ROOM", "NOTE:", "LUNCH", "BREAK", "CHAPEL"]:
                    # Prepend sheet name for unique campus venues
                    full_venue = f"{display_sheet_name} - {venue_label}"

                    for col_idx, meta in col_map.items():
                        if col_idx < len(row) and row[col_idx]:
                            val = str(row[col_idx]).strip()

                            # Use the new robust expansion logic
                            codes = expand_course_codes(val)

                            for code in codes:
                                if len(code) >= 3:
                                    naive_dt = datetime.combine(meta["date"], meta["start"])
                                    # Make the datetime aware of Africa/Nairobi offset
                                    full_datetime = timezone.make_aware(naive_dt)
                                    all_exams.append(
                                        {
                                            "course_code": code,
                                            "title": code,
                                            "date": full_datetime,
                                            "end_time": meta["end"],
                                            "venue": full_venue,
                                            "duration_hours": meta["duration"],
                                        }
                                    )
            i += 1
    return all_exams

