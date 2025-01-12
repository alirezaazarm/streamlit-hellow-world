import pandas as pd

params = {
            "first_name": { "type": "string", "description":"نام سفارش دهنده" } ,
            "last_name" : { "type": "string", "description":"نام خانوادگی سفارش دهنده" } ,
            "address" : { "type": "string", "description":"آدرس (نشانی) سفارش دهنده" } ,
            "phone": { "type": "string", "description":"شماره تلفن سفارش دهنده" } ,
            "product" : { "type": "string", "description":"عنوان محصول خریداری شده" } ,
            "price" : { "type": "string", "description":"قیمت محصول خریداری شده" } ,
            "date" : { "type": "string", "description":"تاریخ و ساعت ثبت سفارش" }
          }

tools_list = [ {"type": "file_search"},
 {"type": "function",
 "function": {      "name": "add_order_row",
                    "description": "ثبت سفارش جدید در جدول سفارشات",
                    "parameters": {  "type": "object", "properties": params,
                    "required":[ 'first_name', 'last_name', 'address', 'phone'] }
  }}         ]

def add_order_row(file_path, first_name, last_name, address, phone, product, price):
  try:
    df = pd.read_json(file_path)
  except FileNotFoundError:
    df = pd.DataFrame(columns=[ 'first_name', 'last_name', 'address', 'phone', 'product', 'price', 'date'])

  now = datetime.now()
  date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

  new_row = {'first_name':first_name, 'last_name':last_name,'address': address,
             'phone':phone, 'product': product, 'price': price, 'date':date_time_str}

  df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

  df.to_json(file_path, orient='records', force_ascii=False)
  print(f"Order added to {file_path}")
  return df
  
