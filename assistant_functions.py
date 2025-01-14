import pandas as pd
from datetime import datetime

def format_datetime(iso_datetime):
    """Convert ISO datetime string to a formatted string."""
    dt = datetime.fromisoformat(iso_datetime)
    return dt.strftime("%Y-%m-%d %H:%M")

def add_order_row(file_path, first_name, last_name, address, phone, product, price, how_many):
    try:
        df = pd.read_json(file_path, dtype={
            'first_name': str,
            'last_name': str,
            'address': str,
            'phone': str,  # Ensure phone is read as string
            'product': str,
            'price': str,
            'date': str,
            'how_many': int
        })
    except FileNotFoundError:
        df = pd.DataFrame(columns=['first_name', 'last_name', 'address', 'phone', 'product', 'price', 'date', 'how_many'])

    now = datetime.now()
    date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    new_row = {
        'first_name': str(first_name),
        'last_name': str(last_name),
        'address': str(address),
        'phone': str(phone),
        'product': str(product),
        'price': str(price),
        'date': date_time_str,
        'how_many': int(how_many)
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_json(file_path, orient='records', force_ascii=False, date_format='iso')
    print(f"Order added to {file_path}")
    return df
