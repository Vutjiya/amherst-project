from skimage.util import img_as_float
from sklearn.svm import LinearSVC
from sklearn.model_selection import KFold
from sklearn.cluster import KMeans
import numpy as np
from pathlib import Path
from PIL import Image

#TODO: preprocess images so all of them are square

# Processes images in positive and negative set, returning a tuple of ndarrays
def process_images():
    # process all 7000 cutouts, convert to matrices, then store them in an array
    image_matrices_positive = []
    image_matrices_negative = []

    p_pos = Path.cwd().parent.parent.joinpath('dataset_tool/cutouts/amherst')
    p_neg = Path.cwd().parent.parent.joinpath('cutouts/negative')
    

    for image in p_pos.iterdir():
        img = Image.open(image)
        matrix = np.array(img)
        image_matrices_positive.append(matrix)
    
    for image in p_neg.iterdir():
        img = Image.open(image)
        matrix = np.array(img)
        image_matrices_negative.append(matrix)
    
    return image_matrices_positive, image_matrices_negative
    

def kNN_model():
    kmeans = KNeighborsClassifier()

    images = np.array(process_images())

    kmeans.fit(images)
    print(kmeans.cluster_centers_)


def main():
    k_means_model()

if __name__ == '__main__':
    main()

    

