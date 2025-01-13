import pandas as pd
from datetime import datetime

def add_order_row(file_path, first_name, last_name, address, phone, product, price, how_many):
  try:
    df = pd.read_json(file_path)
  except FileNotFoundError:
    df = pd.DataFrame(columns=[ 'first_name', 'last_name', 'address', 'phone', 'product', 'price', 'date', 'how_many'])

  now = datetime.now()
  date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

  new_row = {'first_name':first_name, 'last_name':last_name,'address': address,
             'phone':phone, 'product': product, 'price': price, 'date':date_time_str, 'how_many':how_many}

  df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

  df.to_json(file_path, orient='records', force_ascii=False)
  print(f"Order added to {file_path}")
  return df
  
