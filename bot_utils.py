from datetime import datetime
import re


def format_date(text):
    # Define the possible date formats
    date_formats = ["%m/%d/%y", "%m/%d/%Y", "%d/%m/%y", "%d/%m/%Y", "%m-%d-%Y", "%m-%d-%y"]

    # Extract all possible date strings from the input text
    date_strings = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)

    # Replace each date string with its formatted version
    for date_string in date_strings:
        for date_format in date_formats:
            try:
                dt = datetime.strptime(date_string, date_format)
                # If the year is less than 100, assume it refers to a year in the future
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 2000)
                # If the date is successfully parsed, reformat it and replace the original date string in the output
                text = text.replace(date_string, dt.strftime("%Y-%m-%d"))
                break
            except ValueError as e:
                pass

    return text


def replace_text(input_str):
    # Use regular expression to replace 'provider id' with 'doctor'
    input_str = re.sub(r'provider id \d+', 'doctor', input_str)

    # Create a list of texts to be replaced with 'doctor'
    replace_list = ['attending_provider_id',
                    'attending provider id',
                    'provider_id',
                    'provider id',
                    'provider',
                    'attending provider'
                    ]

    # Iterate through the list and replace each text with 'doctor' in the input string
    for text in replace_list:
        input_str = input_str.replace(text, 'doctor')

    # Return the modified input string
    return input_str


