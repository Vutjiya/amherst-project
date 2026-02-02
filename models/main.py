from skimage.util import img_as_float
from sklearn.svm import LinearSVC
from sklearn.model_selection import KFold
from sklearn.cluster import KMeans
import numpy as np


    

def kNN_model():
    kmeans = KNeighborsClassifier()

    images = np.array(process_images())

    kmeans.fit(images)
    print(kmeans.cluster_centers_)


def main():
    kNN_model()

if __name__ == '__main__':
    main()

    

