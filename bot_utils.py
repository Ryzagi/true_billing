from datetime import datetime


def format_date(text):
    # Define the possible date formats
    date_formats = ["%m/%d/%y", "%m/%d/%Y", "%d/%m/%y", "%d/%m/%Y", "%m-%d-%Y"]
    # Extract the date string from the input text
    for word in text.split():
        for date_format in date_formats:
            try:
                dt = datetime.strptime(word, date_format)
                # If the year is less than 100, assume it refers to a year in the future
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                # If the date is successfully parsed, reformat it and return the output
                return text.replace(word, dt.strftime("%Y-%m-%d"))
            except ValueError:
                pass
    # If no valid date format is found, return an error message
    return text
