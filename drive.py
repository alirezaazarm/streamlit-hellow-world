import os
import gdown

def main():
    file_ides = {
        'translated_data.csv': '1Y1DW_sY2mnK8Ty080fRtLQ4shMKHOZCG',
        'inference.pkl' : '1JJx2ZIgClo3ksigYxuW6MxLtc1t52Gg4',
        'products.csv' : '1cZm-MVPCVcvkY0FJ9iZpDjSe9JiPIzm7'
    }
    
    os.makedirs('/workspaces/streamlit-hellow-world/drive', exist_ok=True)
    
    for file in file_ides.keys():
        url = f"https://drive.google.com/uc?id={file_ides[file]}"
        output = f"/workspaces/streamlit-hellow-world/drive/{file}"
    
        if not os.path.exists(output):
            print(f"Downloading {file} from Google Drive...")
            gdown.download(url, output, quiet=False)
        else:
            print(f"{file} already exists locally.")

if __name__ == "__main__":
    main()
