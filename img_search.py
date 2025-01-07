import pandas as pd
import torch
import pickle
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch.nn.functional as F
from glob import glob
import os

class CLIPInference:
    def __init__(self, model_path, metadata, img_base_dir):

        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        checkpoint = torch.load(model_path, map_location='cpu')
        self.model.load_state_dict(checkpoint['model_state_dict'])

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        self.model.eval()

        self.metadata_df = metadata
        self.img_base_dir = img_base_dir
        self.image_index = self._create_image_index()

        self.image_features = None
        self.image_paths = None
        self._create_feature_bank()

    def _create_image_index(self):
        image_index = []
        for _, row in self.metadata_df.iterrows():
            pID = str(row['pID'])
            img_dir = os.path.join(self.img_base_dir, pID)
            images = glob(os.path.join(img_dir, '*.[jJ][pP][gG]')) + \
                    glob(os.path.join(img_dir, '*.[pP][nN][gG]'))
            for img_path in images:
                image_index.append({
                    'path': img_path,
                    'pID': pID,
                    'text': row['translated_title']
                })
        return image_index

    @torch.no_grad()
    def _create_feature_bank(self):
        print("Creating feature bank...")
        features = []
        paths = []

        for item in self.image_index:
            try:
                image = Image.open(item['path']).convert('RGB')
                inputs = self.processor(images=image, return_tensors="pt")
                image_features = self.model.get_image_features(inputs['pixel_values'].to(self.device))
                features.append(F.normalize(image_features.cpu(), dim=-1))
                paths.append(item['path'])
            except Exception as e:
                print(f"Error processing {item['path']}: {e}")
                continue

        self.image_features = torch.cat(features)
        self.image_paths = paths
        print("Feature bank created!")

    @torch.no_grad()
    def search_by_text(self, text, top_k=5):
        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        text_features = self.model.get_text_features(inputs['input_ids'].to(self.device))
        text_features = F.normalize(text_features.cpu(), dim=-1)

        similarities = torch.matmul(text_features, self.image_features.t())[0]
        top_indices = torch.topk(similarities, min(top_k, len(self.image_paths))).indices

        results = []
        for idx in top_indices:
            img_path = self.image_paths[idx]
            for item in self.image_index:
                if item['path'] == img_path:
                    results.append({
                        'path': img_path,
                        'similarity': similarities[idx].item(),
                        'metadata': item
                    })
                    break

        return results

    @torch.no_grad()
    def search_by_image(self, image_path, top_k=5):
        image = Image.open(image_path).convert('RGB')
        inputs = self.processor(images=image, return_tensors="pt")
        image_features = self.model.get_image_features(inputs['pixel_values'].to(self.device))
        image_features = F.normalize(image_features.cpu(), dim=-1)

        similarities = torch.matmul(image_features, self.image_features.t())[0]
        top_indices = torch.topk(similarities, min(top_k, len(self.image_paths))).indices

        results = []
        for idx in top_indices:
            img_path = self.image_paths[idx]
            for item in self.image_index:
                if item['path'] == img_path:
                    results.append({
                        'path': img_path,
                        'similarity': similarities[idx].item(),
                        'metadata': item
                    })
                    break

        return results


data = pd.read_csv('/workspaces/streamlit-hellow-world/drive/translated_data.csv', encoding='utf-8', engine='python')

with open('/workspaces/streamlit-hellow-world/drive/inference.pkl', 'rb') as f:
    inference = pickle.load(f)

image_query = "/workspaces/streamlit-hellow-world/buffer/image.jpg"
results = inference.search_by_image(image_query, top_k=5)

print(f"\nResults for image query: '{image_query}'")
for i, result in enumerate(results, 1):
        print(f"\n{i}. Similarity: {result['similarity']:.3f}")
        print(f"   Image: {result['path']}")
        print(f"   pID: {result['metadata']['pID']}")
        print(f"   English Text: {result['metadata']['text']}")
        print(f"   Persian Text: {data.loc[data['pID'] == int(result['metadata']['pID']), 'title'].values[0]}")