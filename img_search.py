# img_search.py
import pandas as pd
import torch
import pickle
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os

def load_precomputed_data():
    """Load the precomputed features and metadata"""
    with open('drive/inference.pkl', 'rb') as f:
        data_dict = pickle.load(f)
    return data_dict['image_features'], data_dict['image_paths'], data_dict['image_index']

def initialize_model():
    """Initialize CLIP model and processor"""
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    return model, processor, device

def search_by_image(image_path, model, processor, device, image_features, image_paths, image_index, top_k=5):
    """Search for similar images using CLIP"""
    with torch.no_grad():
        image = Image.open(image_path).convert('RGB')
        inputs = processor(images=image, return_tensors="pt")
        image_features_query = model.get_image_features(inputs['pixel_values'].to(device))
        image_features_query = F.normalize(image_features_query.cpu(), dim=-1)

        similarities = torch.matmul(image_features_query, image_features.t())[0]
        top_indices = torch.topk(similarities, min(top_k, len(image_paths))).indices

        results = []
        for idx in top_indices:
            img_path = image_paths[idx]
            for item in image_index:
                if item['path'] == img_path:
                    results.append({
                        'path': img_path,
                        'similarity': similarities[idx].item(),
                        'metadata': item
                    })
                    break
        return results

def process_image(image_path, top_k=5):
    try:
        # Load precomputed data
        image_features, image_paths, image_index = load_precomputed_data()
        
        # Initialize model
        model, processor, device = initialize_model()
        
        # Load metadata
        data = pd.read_csv('drive/translated_data.csv', encoding='utf-8', engine='python')
        
        # Search for similar images
        results = search_by_image(
            image_path, 
            model, 
            processor, 
            device, 
            image_features, 
            image_paths, 
            image_index, 
            top_k
        )
        
        # Format results
        output_logs = []
        for i, result in enumerate(results, 1):
            similarity = f"\n{i}. Similarity: {result['similarity']:.3f}"
            image_path = f"   Image: {result['path']}"
            pid = f"   pID: {result['metadata']['pID']}"
            eng_text = f"   English Text: {result['metadata']['text']}"
            try:
                persian_title = f"   Persian Title: {data.loc[data['product_id'] == int(result['metadata']['pID']), 'title'].values[0]}"
            except:
                persian_title = "   Persian Title: Not found"
            
            output_logs.extend([similarity, pid, eng_text, persian_title])
        
        return "\n".join(output_logs)
    except Exception as e:
        raise Exception(f"Detailed error: {str(e)}")
