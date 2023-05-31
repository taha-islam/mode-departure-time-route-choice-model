# -*- coding: utf-8 -*-
"""
Created on Thu Dec  5 07:29:27 2019

@author: islam
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import pandas as pd
import os

def load_data(x, y=None):
    data = []
    for file in x:
        data.append(pd.read_csv(file, index_col=False, 
                            usecols=['speed','flow_per_lane','before_on_ramp','after_on_ramp',
                                     'before_off_ramp','after_off_ramp']).to_numpy())
    if y is not None:
        labels = []
        for file in y:
            labels.append(pd.read_csv(file, index_col=False, header=None).to_numpy().transpose()[0])
        return np.array(data), np.array(labels)
    else:
        return np.array(data)


'''model = keras.models.load_model("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model.h5")
features_min = np.load("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_min_x.npy")
features_max = np.load("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_max_x.npy")
labels_min = np.load("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_min_y.npy")
labels_max = np.load("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_max_y.npy")'''
model_dir = "C:/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/metro3/trip_assignment/calibration_models"
model = keras.models.load_model(os.path.join(model_dir,"normalized_minmax_model.h5"))
features_min = np.load(os.path.join(model_dir,"normalized_minmax_model_min_x.npy"))
features_max = np.load(os.path.join(model_dir,"normalized_minmax_model_max_x.npy"))
labels_min = np.load(os.path.join(model_dir,"normalized_minmax_model_min_y.npy"))
labels_max = np.load(os.path.join(model_dir,"normalized_minmax_model_max_y.npy"))

model.compile(loss='mse', optimizer=tf.train.RMSPropOptimizer(0.001), metrics=['mae'])

model.summary()


#features, labels = load_data(["C:/Aimsun Projects/Calibration Using Neural Networks/dataset/x25.csv"],
#                            ["C:/Aimsun Projects/Calibration Using Neural Networks/dataset/y25.csv"])
features = load_data(["C:/Aimsun Projects/testing METRO/QEW/detector_data_detailed.csv"])

features.shape
features = features[:,:162,:]
#labels[0]

features_norm = features
features_norm[:,:,:2] = (features[:,:,:2] - features_min) / (features_max - features_min)
model.predict(features_norm) * (labels_max - labels_min) + labels_min
