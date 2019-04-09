import matplotlib as MPL
MPL.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
import pylab as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from sklearn.metrics.cluster import homogeneity_score
from sklearn.metrics import pairwise_distances
from sklearn import metrics
import pandas as pd
from data_reader import DataReader
from data_manipulator import *
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
import random
import keras
import gzip
import nltk
#nltk.download('stopwords')
from keras.layers import Input,Conv2D,MaxPooling2D,UpSampling2D
from keras.models import Model
from keras.optimizers import RMSprop
from Models.lda import Lda
from Models.kmeans import Kmeans
from Models.dbscan import DBscan
from Models.birch import Birch_
from Models.hierarchical import Hierarchical
from Models.gmm import GMM
from Models.meanshift import Meanshift
from Models.spectral import Spectral
from Models.affinity import Affinity
from run_autoencoder import get_encoder

from sklearn.manifold import TSNE

import argparse

def plot_dataset_size_per_site(dataset_sizes, x_labels):
    fig = plt.figure()
    y_pos = np.arange(len(x_labels))
    plt.bar(y_pos, dataset_sizes)
    plt.xticks(y_pos, x_labels, rotation='vertical')
    plt.tight_layout()
    plt.title('Data set sizes by Site')
    plt.savefig("dataset_sizes_per_site.pdf", bbox_inches = "tight")

def plot_sil_scores_per_site(scores, x_labels):
    fig = plt.figure()
    y_pos = np.arange(len(x_labels))
    plt.bar(y_pos, scores)
    plt.xticks(y_pos, x_labels, rotation='vertical')
    plt.tight_layout()
    plt.title('Silhouette Scores for Clustering by Site')
    plt.savefig("sil_scores_per_site.pdf", bbox_inches = "tight")

def get_top_keywords(data, clusters, feature_names, n_terms):
    # group by clusters and get the mean occurence of each word
    df = pd.DataFrame(data).groupby(clusters).mean()
    
    # iterate through each cluster and get the most frequent occuring words
    for i,r in df.iterrows():
        print('Cluster {}: '.format(i) + ','.join([str(feature_names[t]) for t in np.argsort(r)[-n_terms:]]))

def plot_cluster_size_frequency(data, clusters, nc):
    x = list()
    for i in range(nc):
        count = np.count_nonzero(clusters == i)
        x.append(count)
    fig = plt.figure()
    plt.hist(x)
    plt.title('Frequency of cluster sizes')
    plt.savefig("kmeans_tfidf_cluster_size_frequency.png")

# code from: https://www.kaggle.com/jbencina/clustering-documents-with-tfidf-and-kmeans
def find_optimal_clusters(max_k, feature_names, train_x, train_y, rep):
    iters = [2] + list(range(100, max_k+1, 100))
    sse = []
    for k in iters:
        kmeans = ""
        #h = ""
        kmeans = Kmeans(k, feature_names, train_x, train_y, rep)
        #sse.append(kmeans.kmeans_model.inertia_)
        sse.append(kmeans.get_sil_score())
        print('Fit '+ str(k)  + ' clusters: ' + str(kmeans.get_sil_score()))

    f, ax = plt.subplots(1, 1)
    ax.plot(iters, sse, marker='o')
    ax.set_xlabel('Number of Cluster Centers (k)')
    ax.set_xticks(iters)
    ax.set_xticklabels(iters)
    ax.set_ylabel('SSE')
    ax.set_title('SSE by Cluster Center Plot')
    plt.savefig('vary_k.png', dpi=1000)

def main():
    # parse arguments
    parser = argparse.ArgumentParser(description='Run unsupervised methods', add_help=True)
    parser.add_argument("-m", "--model", action="store", required=True, dest="MODELS", nargs='+', choices=['all', 'kmeans', 'lda', 'dbscan', 'birch', 'hierarchical', 'gmm', 'meanshift', 'spectral', 'affinity'], help="Run model")
    parser.add_argument("-r", "--rep",   action="store", required=False, dest="REP", choices=['bow', 'tfidf', 'doc2vec', 'pca'], help="Use bag of words representation (BOW), tfidf, doc2vec representation, or PCA")
    parser.add_argument("--use-autoencoder", action="store_true", dest="USE_AUTOENCODER", help="Use autoencoders to reduce representations")
    parser.add_argument("--use-doc2vec", action="store_true", dest="USE_DOC2VEC", help="Use doc2vec representations")
    parser.add_argument("--queries", action="store", dest="queries", nargs='+', help="Return closest neighbours for query words to test search querying capabilities")
    parser.add_argument("--print-keywords", action="store_true", dest="PRINT_KEYWORDS", help="Use if you want to print keywords in each cluster")
    parser.add_argument("--find-optimal-k",  action="store_true", dest="FIND_OPTIMAL_K", help="Find optimal K")
    parser.add_argument("-s", "--sample-size", action="store", required=False, dest="SIZE", help="Use smaller set")
    parser.add_argument("-d", "--downsample-frac", action="store", required=False, default=1.0, dest="DOWNSAMPLE_FRAC", type=float, help="downsample fraction (0-1]")
    parser.add_argument("--min-cluster-size", action="store", required=False, default=5, dest="MIN_CLUSTER_SIZE", help="Filter out any ON WG IDENTIFIER classes with less than MIN_CLUSTER_SIZE")
    parser.add_argument("-n", "--num-clusters", action="store", required=False, default=1500, dest="NUM_CLUSTERS", help="Number of clusters for algorithms that require it")
    args = parser.parse_args()
    #print(args.MODELS)

    assert(not (args.DOWNSAMPLE_FRAC) or (args.DOWNSAMPLE_FRAC > 0.0 and args.DOWNSAMPLE_FRAC <= 1.0 and args.DOWNSAMPLE_FRAC))

	# get data
    data_reader = DataReader()
    df = data_reader.get_all_data()
    if args.SIZE:
        subset_df = df.sample(n=int(args.SIZE))
        train_x_raw, train_y_raw, test_x_raw, test_y_raw = get_train_test_split(subset_df)
    elif args.DOWNSAMPLE_FRAC:
        subset_df = df.sample(frac=float(args.DOWNSAMPLE_FRAC))
        train_x_raw, train_y_raw, test_x_raw, test_y_raw = get_train_test_split(subset_df)
    else:
        train_x_raw, train_y_raw, test_x_raw, test_y_raw = get_train_test_split(df)
    #train_x_raw = pd.concat([train_x_raw, test_x_raw], axis=0)
    #train_y_raw = pd.concat([train_y_raw, test_y_raw], axis=0)
    train_x_raw.drop(['RIS PROCEDURE CODE'], axis=1, inplace=True)
    test_x_raw.drop(['RIS PROCEDURE CODE'], axis=1, inplace=True)

    # identify ON WG IDENTIFIERS that occur infrequently
    #print("MIN_CLUSTER_SIZE: " + str(args.MIN_CLUSTER_SIZE))
    min_samples = args.MIN_CLUSTER_SIZE
    train_y_list = train_y_raw['ON WG IDENTIFIER'].values.tolist()
    unique_ids = list(set(train_y_list))
    small_clusters = list()
    for i in unique_ids:
        if train_y_list.count(i) < min_samples:
            small_clusters.append(i)
    train_x_raw = train_x_raw[~train_y_raw['ON WG IDENTIFIER'].isin(small_clusters)]
    train_y_raw = train_y_raw[~train_y_raw['ON WG IDENTIFIER'].isin(small_clusters)]
    #print(train_y_raw['ON WG IDENTIFIER'])
    #print(len(unique_ids))
    num_clusters = len(unique_ids) - len(small_clusters)
    #print("NUM_CLUSTERS: " + str(num_clusters))

    # append the ON WG IDENTIFIERS to the original documents
    train_y_raw = pd.concat([train_x_raw, train_y_raw], axis=1)
    test_y_raw = pd.concat([test_x_raw, test_y_raw], axis=1)

    # tokenize and subsample
    tokens_train, train_y_raw = tokenize_columns(train_x_raw, train_y_raw, regex_string=r'[a-zA-Z0-9]+', 
        save_missing_feature_as_string=False, remove_short=True, remove_num=True, remove_empty=True)
    tokens_test, test_y_raw = tokenize_columns(test_x_raw, test_y_raw, regex_string=r'[a-zA-Z0-9]+', 
        save_missing_feature_as_string=False, remove_short=True, remove_num=True, remove_empty=True)
    #print("done tokenizing columns")

    # get representation of data
    feature_names = list()
    train_x = list()
    train_y = list()
    test_x = list()
    test_y = list()
    #print(test_x_raw.shape)
    if args.REP == "bow" or args.USE_AUTOENCODER:
        train_x, train_y, feature_names = tokens_to_bagofwords(tokens_train, train_y_raw, CountVectorizer)
        test_x, test_y, _ = tokens_to_bagofwords(tokens_test, test_y_raw, CountVectorizer, feature_names=feature_names)
        train_x = train_x.toarray()
        test_x = test_x.toarray()
        #print(test_x.shape)
        #print("done converting to bag of words representation")
    elif args.REP == "tfidf":
        train_x, train_y, feature_names = tokens_to_bagofwords(tokens_train, train_y_raw, TfidfVectorizer)
        test_x, test_y, _ = tokens_to_bagofwords(tokens_test, test_y_raw, TfidfVectorizer, feature_names=feature_names)
        train_x = train_x.toarray()
        test_x = test_x.toarray()
        #print("done converting to tfidf representation")
    elif args.REP == "doc2vec":
        train_x, train_y, _ = tokens_to_doc2vec(tokens_train, train_y_raw)
        test_x, train_y, _ = tokens_to_doc2vec(tokens_test, train_y_raw)
        #print("done converting to doc2vec representation")
    elif args.REP == "pca":
        train_x, train_y, feature_names = tokens_to_bagofwords(tokens_train, train_y_raw, CountVectorizer)
        test_x, test_y, _ = tokens_to_bagofwords(tokens_test, test_y_raw, CountVectorizer, feature_names=feature_names)

        #get number of components
        pca = PCA()
        pca.fit(train_x.toarray())
        var = np.cumsum(pca.explained_variance_ratio_)
        n_comp = np.argmax(var > .9) + 1
        # fit pca
        pca = PCA(n_components=n_comp)
        pca.fit(train_x.toarray())
        train_x = pca.fit_transform(train_x.toarray())
        test_x = pca.fit_transform(test_x.toarray())

    
    VOCAB_SIZE = train_x.shape[1]
    if args.USE_AUTOENCODER:
        #print(int(len(data_reader.get_region_labels()['Code'])))
        # use an autoencoder with representation size = VOCAB_SIZE / 10
        REP_SIZE = 100
        encoder = get_encoder(train_x, test_x, REP_SIZE)
        train_x = encoder.predict(train_x)
        test_x = encoder.predict(test_x)
        #print("done converting to autoencoder representation")

    # run models
    print("TRAIN_X SHAPE = " + str(test_x.shape) + ", VOCAB_SIZE = " + str(VOCAB_SIZE) + ", NUM_CLUSTERS = " + str(num_clusters) + ", MIN_CLUSTER_SIZE = " + str(args.MIN_CLUSTER_SIZE))
    if "kmeans" in args.MODELS or "all" in args.MODELS:
        kmeans = Kmeans(num_clusters, feature_names, train_x, train_y, args.REP)
        kmeans.eval()
        labels = kmeans.get_labels()

        # print results
        print("kmeans, " + args.REP + ", " + str(args.DOWNSAMPLE_FRAC) + ", " + str(kmeans.get_sil_score()) + ", " + str(kmeans.get_db_idx_score()))
        if args.FIND_OPTIMAL_K:
            find_optimal_clusters(2000, feature_names, train_x, train_y, args.REP)
        #plot_cluster_size_frequency(train_x, labels, num_clusters) 
        # example queries
        print("getting nearest: ")
        if args.queries:
            for q in args.queries:
                kmeans.get_nearest_neighbours(str(q))

        if args.PRINT_KEYWORDS:
            # get top keywords for clusters
            print("getting top 10 keywords for each cluster: ")
            get_top_keywords(train_x, labels, feature_names, 10)
        '''
                                                                  
        # plot 500 random clusters
        plt.figure(figsize=(10, 7)) 
        fig, ax = plt.subplots()
        print("number of unique labels: " + str(len(np.unique(labels))))
        num_clusters_to_plot = 50
        tsne = TSNE(n_components=2, verbose=1)
        random_clusters = random.sample(range(1, num_clusters), num_clusters_to_plot)
        reduced_data = tsne.fit_transform(train_x.todense())
        cmap = plt.cm.get_cmap('rainbow',num_clusters_to_plot)

        for i in range(num_clusters_to_plot):
            l = random_clusters[i]
            print("cluster " + str(l))
            indices = np.where(labels == l)
            col = cmap(i)
            cluster_reduced_data = reduced_data[indices[0]]
            print(cluster_reduced_data.shape)
            plt.scatter(cluster_reduced_data[:,0], cluster_reduced_data[:,1], color=col)
        plt.savefig('kmeans_' +  args.REP + '_' + str(num_clusters_to_plot) + '.tsne.png')  '''
    if "lda" in args.MODELS or "all" in args.MODELS:
        # run lda
        lda = Lda(train_x_raw, train_y_raw, 1500, passes=15)
        lda.train()
        print("finished running lda")
    if "dbscan" in args.MODELS or "all" in args.MODELS:
        # run dbscan
        dbs = DBscan(num_clusters, feature_names, train_x, train_y)
        dbs.eval()
        print("dbscan, " + args.REP + ", " + str(dbs.get_sil_score()) + ", " + str(dbs.get_db_idx_score()))
    if "birch" in args.MODELS or "all" in args.MODELS:
        b = Birch_(num_clusters, feature_names, train_x, train_y, args.REP)
        print("birch, " + args.REP + ", " + str(b.get_sil_score()) + ", " + str(b.get_db_idx_score()))
    if "hierarchical" in args.MODELS or "all" in args.MODELS:
        h = Hierarchical(num_clusters, feature_names, train_x, train_y, args.REP)
        print("hierarchical, " + args.REP + ", " + str(h.get_sil_score()) + ", " + str(h.get_db_idx_score()))
        labels = h.get_labels()
        # get top keywords for clusters
        if args.PRINT_KEYWORDS:
            print("getting top 10 keywords for each cluster: ")
            get_top_keywords(train_x, labels, feature_names, 10)
        if args.FIND_OPTIMAL_K:
            find_optimal_clusters(2000, feature_names, train_x, train_y, args.REP)
        if args.queries:
            h.get_nearest_neighbours(args.queries)
    if "gmm" in args.MODELS or "all" in args.MODELS:
        gmm = GMM(num_clusters, feature_names, train_x, train_y)
        print("GMM, " + args.REP + ", " + str(gmm.get_sil_score()) + ", " + str(gmm.get_db_idx_score())) 
    if "meanshift" in args.MODELS or "all" in args.MODELS:
        ms = Meanshift(feature_names, train_x, train_y)
        print("meanshift, " + args.REP + ", " + str(ms.get_sil_score()) + ", " + str(ms.get_db_idx_score()))
    if "spectral" in args.MODELS or "all" in args.MODELS:
        sp = Spectral(num_clusters, feature_names, train_x, train_y)
        print("spectral, " + args.REP + ", " + str(sp.get_sil_score()) + ", " + str(sp.get_db_idx_score()))
    if "affinity" in args.MODELS or "all" in args.MODELS:
        af = Affinity(num_clusters, feature_names, train_x, train_y)
        print("affinity, " + args.REP + ", " + str(af.get_sil_score()) + ", " + str(af.get_db_idx_score()))

if __name__ == '__main__':
    main()
