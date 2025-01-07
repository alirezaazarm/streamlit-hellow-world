import pandas as pd
import torch
import pickle
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from glob import glob
import os
import sys

class CLIPInference:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        self.model.eval()
        
        self.metadata_df = None
        self.img_base_dir = None
        self.image_index = None
        self.image_features = None
        self.image_paths = None

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

def load_inference():
    with open('drive/inference.pkl', 'rb') as f:
        
        pickle_data = f.read()
    
    old_modules = {}
    for mod_name in list(sys.modules.keys()):
        if mod_name not in sys.builtin_module_names:
            old_modules[mod_name] = sys.modules[mod_name]
            del sys.modules[mod_name]
    
    try:
        sys.modules['__main__'] = sys.modules[__name__]
        inference = pickle.loads(pickle_data)
        return inference
    finally:
        sys.modules.clear()
        sys.modules.update(old_modules)

def process_image(image_path, top_k=5):
    try:
        inference = load_inference()
        
        data = pd.read_csv('drive/translated_data.csv', encoding='utf-8', engine='python')
        
        results = inference.search_by_image(image_path, top_k=5)
        
        output_logs = []
        for i, result in enumerate(results, 1):
            similarity = f"\n{i}. Similarity: {result['similarity']:.3f}"
            image_path = f"   Image: {result['path']}"
            pid = f"   pID: {result['metadata']['pID']}"
            eng_text = f"   English Text: {result['metadata']['text']}"
            try:
                persian_title = f"   Persian Title: {data.loc[data['pID'] == int(result['metadata']['pID']), 'title'].values[0]}"
            except:
                persian_title = "   Persian Title: Not found"
            
            output_logs.extend([similarity, image_path, pid, eng_text, persian_title])
        
        return "\n".join(output_logs)
    except Exception as e:
        raise Exception(f"Error in processing: {str(e)}")
