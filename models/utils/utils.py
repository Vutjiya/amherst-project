from pathlib import Path
from PIL import Image
import numpy as np
from sklearn.model_selection import train_test_split

#TODO: preprocess images so all of them are square

# Processes images in positive and negative set, returning a tuple of ndarrays
# def process_images():
#     # process all 7000 cutouts, convert to matrices, then store them in an array
#     image_matrices_positive = []
#     image_matrices_negative = []

#     p_pos = Path.cwd().parent.parent.joinpath('dataset_tool/cutouts/amherst')
#     p_neg = Path.cwd().parent.parent.joinpath('cutouts/negative')
    

#     for image in p_pos.iterdir():
#         img = Image.open(image)
#         matrix = np.array(img)
#         image_matrices_positive.append(matrix)
    
#     for image in p_neg.iterdir():
#         img = Image.open(image)
#         matrix = np.array(img)
#         image_matrices_negative.append(matrix)
    
#     return image_matrices_positive, image_matrices_negative

def process_and_split_images():
    # process all 14000 cutouts, convert to matrices, then store them in arrays
    paths = {}
    towns = ['amherst', 'annapolis', 'annarbor', 'cambridge', 'charlottesville', 'hanover', 'newhaven', 'oberlin', 'princeton']

    for town in towns:
        path = Path.cwd().parent.parent.joinpath(f'dataset_tool/cutouts/{town}')
        paths[town] = path

    # Create discovery sets D1, D2
    discovery_set = []
    for image in paths['amherst'].iterdir():
        img = Image.open(image)
        matrix = np.array(img)
        discovery_set.append(matrix)
    
    discovery_set1, discovery_set2 = train_test_split(discovery_set, test_size=0.5, random_state=67)

    # Create natural world sets W1, W2
    natural_world_set = []
    for image in paths.values().iterdir():
        img = Image.open(image)
        matrix = np.array(img)
        natural_world_set.append(matrix)
    
    natural_world_set1, natural_world_set2 = train_test_split(natural_world_set, test_size=0.5, random_state=42)
    
    return [discovery_set1, discovery_set2], [natural_world_set1, natural_world_set2]

