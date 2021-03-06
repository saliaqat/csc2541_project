from sklearn import metrics
import numpy as np
import pandas as pd
import matplotlib as MPL

MPL.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
import pylab as plt
import sys, os, csv
from mpl_toolkits.axes_grid1 import make_axes_locatable
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from Models.model import Model
from Models.clustermodel import ClusterModel
import gensim
from gensim import corpora
from gensim.models.coherencemodel import CoherenceModel
import pickle
import seaborn as sns
from data_manipulator import *
from sklearn.cluster import KMeans
from sklearn.metrics.cluster import homogeneity_score
from sklearn.metrics.pairwise import euclidean_distances
import warnings

warnings.filterwarnings("ignore")
en_stop = set(nltk.corpus.stopwords.words('english'))
from sklearn.cluster import SpectralClustering
from sklearn.metrics import davies_bouldin_score
from sklearn.cluster import Birch


class Birch_(ClusterModel):
    def __init__(self, num_clusters, feature_names, train_x, train_y, rep):
        ClusterModel.__init__(self, train_x, train_y, feature_names, rep)
        self.birch_model = Birch(n_clusters=num_clusters).fit(train_x)
        self.birch_model.predict(train_x)
        self.labels = self.birch_model.labels_
        print(self.labels)
        self.num_clusters = num_clusters
