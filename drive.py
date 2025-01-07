import os
import gdown

def main():
    file_ides = {
        'translated_data.csv': '1Y1DW_sY2mnK8Ty080fRtLQ4shMKHOZCG',
        'inference.pkl' : '1-1ikhnjrS3ZdDfroa9sDTq4P5mELa0KL',
        'products.csv' : '1cZm-MVPCVcvkY0FJ9iZpDjSe9JiPIzm7'
    }
    
    os.makedirs('./drive', exist_ok=True)
    
    for file in file_ides.keys():
        url = f"https://drive.google.com/uc?id={file_ides[file]}"
        output = f"./drive/{file}"
    
        if not os.path.exists(output):
            print(f"Downloading {file} from Google Drive...")
            gdown.download(url, output, quiet=False)
        else:
            print(f"{file} already exists locally.")

if __name__ == "__main__":
    main()
