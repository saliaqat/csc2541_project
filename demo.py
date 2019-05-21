import numpy as np
import pandas as pd
import os

from data_reader import DataReader
from data_manipulator_interface import get_train_validate_test_split
from data_manipulator import tokenize, tokens_to_bagofwords
from Models.neural_net import MultiClassNNScratch, top_3_accuracy
from keras.models import load_model
from nltk.tokenize import RegexpTokenizer
from sklearn.feature_extraction.text import CountVectorizer


np.warnings.filterwarnings('ignore')

def main():
    data_reader = DataReader()
    df = data_reader.get_all_data()

    top_x_predictions = 10

    # Split data
    train_x_raw, train_y_raw, val_x_raw, val_y_raw, test_x_raw, test_y_raw = get_train_validate_test_split(df)

    # get bag of words
    train_x, train_y, val_x, val_y, test_x, test_y, feature_names = get_bag_of_words(train_x_raw, train_y_raw,
                                                                                    val_x_raw, val_y_raw,
                                                                                    test_x_raw, test_y_raw)
    # get all labels
    labels = data_reader.get_region_labels()['Code']


    if not os.path.isfile('demo_nn.h5'):
        # train neural net
        model = MultiClassNNScratch(train_x.shape, np.array(labels), epochs=150, batch_size=1024)
        model.set_train_data(train_x, train_y)
        model.train(val_x, val_y)

        # save neural net
        model.model.save('demo_nn.h5')
    else:
        # load neural net
        model = MultiClassNNScratch(train_x.shape, np.array(labels), epochs=150, batch_size=1024)
        model.set_train_data(train_x, train_y)
        model.model = load_model('demo_nn.h5', custom_objects={'top_3_accuracy': top_3_accuracy})

    # from IPython import embed
    # embed()

    regex_string = r'[a-zA-Z0-9]+'
    while True:
        stdin = input("Enter all information:")
        if stdin == 'quit':
            break
        try:
            top_x_predictions = int(stdin)
            print("Will return top " + str(top_x_predictions) + " predictions")
        except ValueError:
            tokenizer = RegexpTokenizer(regex_string)
            tokens = tokenizer.tokenize(stdin.lower())

            vectorizer = CountVectorizer(tokenizer=lambda x: x, lowercase=False, strip_accents=False,
                                          vocabulary=feature_names)

            model_input = vectorizer.fit_transform([tokens])
            pred = model.model.predict(model_input)


            # Top X Predictions
            rows = []
            for i in range(top_x_predictions):
                one_hot_pred = np.zeros_like(pred)
                one_hot_pred[np.arange(len(pred)), (np.argpartition(pred[0], -top_x_predictions)[-top_x_predictions:][i])] = 1
                id = model.encoder.inverse_transform(one_hot_pred)[0][0]
                row = data_reader.regional_df[data_reader.regional_df['Code'] == id]
                row['Prediction Confidence'] = (pred[0][(np.argpartition(pred[0], -top_x_predictions)[-top_x_predictions:][
                    i])]) * 100
                rows.append(row)

            rows = (pd.concat(rows)).sort_values('Prediction Confidence', ascending=False)
            print(rows)








def get_bag_of_words(train_x_raw, train_y_raw, val_x_raw, val_y_raw, test_x_raw, test_y_raw):
    tokens, train_y_raw = tokenize(train_x_raw, train_y_raw, save_missing_feature_as_string=False, remove_empty=True)
    train_x, train_y, feature_names = tokens_to_bagofwords(tokens, train_y_raw)

    tokens, val_y_raw = tokenize(val_x_raw, val_y_raw, save_missing_feature_as_string=False, remove_empty=True)
    val_x, val_y, _ = tokens_to_bagofwords(tokens, val_y_raw, feature_names=feature_names)

    tokens, test_y_raw = tokenize(test_x_raw, test_y_raw, save_missing_feature_as_string=False, remove_empty=True)
    test_x, test_y, _ = tokens_to_bagofwords(tokens, test_y_raw, feature_names=feature_names)

    return train_x, train_y, val_x, val_y, test_x, test_y, feature_names


if __name__ == '__main__':
    main()