# -*- coding: utf-8 -*-
"""
Created on Wed Dec  4 21:59:03 2019

@author: islam
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import pandas as pd
import os

def load_data(input_path):
    data = []
    labels = []
    for file in os.listdir(input_path):
        if file.startswith("x"):
            data.append(pd.read_csv(os.path.join(input_path, file), 
                                    index_col=False, 
                                    usecols=['speed',
                                    'flow_per_lane',
                                    'before_on_ramp',
                                    'after_on_ramp',
                                    'before_off_ramp',
                                    'after_off_ramp']).to_numpy())
        if file.startswith("y"):
            labels.append(pd.read_csv(os.path.join(input_path, file), index_col=False, header=None).to_numpy().transpose()[0])
            #print(labels)
            #break
    return np.array(data), np.array(labels)
    #return tf.data.Dataset.from_tensor_slices((np.array(data), np.array(labels)))

features, labels = load_data("C:\Aimsun Projects\Calibration Using Neural Networks\dataset")
# shuffling and splitting data
indices = np.random.permutation(features.shape[0])
training_idx, test_idx = indices[:450], indices[450:]
train_features, test_features = features[training_idx,:], features[test_idx,:]
train_labels, test_labels = labels[training_idx,:], labels[test_idx,:]
print("Training set: {}, {}".format(train_features.shape, train_labels.shape))
print("Test set: {}, {}".format(test_features.shape, test_labels.shape))
#features[training_idx[0]][:5], train_features[0][:5]
#labels[training_idx[0]][:5], train_labels[0][:5]


model = keras.Sequential([
    keras.layers.Flatten(input_shape=(162,6)),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(9)
])
#model.summary()
model.compile(loss='mse', optimizer=tf.train.RMSPropOptimizer(0.001), metrics=['mae'])
model.fit(train_features, train_labels, epochs=500, validation_split=0.2)



[loss, mae] = model.evaluate(test_features, test_labels)
print("Testing set Mean Abs Error: {}".format(mae))


# Normalizing speed and flow (normal distribution)
mean_features = train_features[:,:,:2].mean(axis=0).mean(axis=0)
std_features = train_features[:,:,:2].std(axis=0).mean(axis=0)
print("mean={}, std={}".format(mean_features, std_features))
train_features_norm = np.zeros_like(train_features)
test_features_norm = np.zeros_like(test_features)
train_features_norm[:,:,:2] = (train_features[:,:,:2] - mean_features) / std_features
train_features_norm[:,:,2:] = train_features[:,:,2:]
test_features_norm[:,:,:2] = (test_features[:,:,:2] - mean_features) / std_features
test_features_norm[:,:,2:] = test_features[:,:,2:]


model_norm = keras.Sequential([
    keras.layers.Flatten(input_shape=(162,6)),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(9)
])
model_norm.compile(loss='mse', optimizer=tf.train.RMSPropOptimizer(0.001), metrics=['mae'])
model_norm.fit(train_features_norm, train_labels, epochs=500, validation_split=0.2)


[loss, mae] = model_norm.evaluate(test_features_norm, test_labels)
print("Testing set Mean Abs Error: {}".format(mae))


model_norm.predict(test_features_norm[:1])


test_labels[0]


# Normalizing outputs
mean_labels = train_labels.mean(axis=0)
std_labels = train_labels.std(axis=0)
print("mean={}, std={}".format(mean_labels, std_labels))
train_labels_norm = (train_labels - mean_labels) / std_labels
test_labels_norm = (test_labels - mean_labels) / std_labels


model_norm_inout = keras.Sequential([
    keras.layers.Flatten(input_shape=(162,6)),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(9, activation=tf.nn.sigmoid)
])
model_norm_inout.compile(loss='mse', optimizer=tf.train.RMSPropOptimizer(0.001), metrics=['mae'])
model_norm_inout.fit(train_features_norm, train_labels_norm, epochs=500, validation_split=0.2)


[loss, mae] = model_norm_inout.evaluate(test_features_norm, test_labels_norm)
print("Testing set Mean Abs Error: {}".format(mae))


model_norm.predict(test_features_norm[:1]) * std_labels + mean_labels


test_labels[0]

# Min/Max Normalizing
minimum_features = train_features[:,:,:2].min(axis=0).min(axis=0)
maximum_features = train_features[:,:,:2].max(axis=0).max(axis=0)
print("min={}, max={}".format(minimum_features, maximum_features))
train_features_minmax = train_features
test_features_minmax = test_features
train_features_minmax[:,:,:2] = (train_features[:,:,:2] - minimum_features) / (maximum_features - minimum_features)
test_features_minmax[:,:,:2] = (test_features[:,:,:2] - minimum_features) / (maximum_features - minimum_features)

minimum_labels = train_labels.min(axis=0)
maximum_labels = train_labels.max(axis=0)
print("min={}, max={}".format(minimum_labels, maximum_labels))
train_labels_minmax = (train_labels - minimum_labels) / (maximum_labels - minimum_labels)
test_labels_minmax = (test_labels - minimum_labels) / (maximum_labels - minimum_labels)


model_norm_minmax = keras.Sequential([
    keras.layers.Flatten(input_shape=(162,6)),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(128, activation=tf.nn.relu),
    keras.layers.Dense(9, activation=tf.nn.sigmoid)
])
model_norm_minmax.compile(loss='mse', 
                          optimizer=tf.train.RMSPropOptimizer(0.001), 
                          metrics=['mae'])
model_norm_minmax.fit(train_features_minmax, train_labels_minmax, epochs=500, validation_split=0.2)


[loss, mae] = model_norm_minmax.evaluate(test_features_minmax, test_labels_minmax)
print("Testing set Mean Abs Error: {}".format(mae))


model_norm_minmax.predict(test_features_minmax).min(axis=0)


model_norm_minmax.predict(test_features_minmax).max(axis=0)


test_labels_minmax.min(axis=0)


test_labels_minmax.max(axis=0)


model_norm_minmax.predict(test_features_minmax[:1]) * (maximum_labels - minimum_labels) + minimum_labels


test_labels_minmax[0] * (maximum_labels - minimum_labels) + minimum_labels


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
model_norm_minmax.predict(sample1) * (maximum_labels - minimum_labels) + minimum_labels


labels[0]


'''model_norm_minmax.save("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model.h5")
np.save("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_min_x.npy", minimum_features)
np.save("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_max_x.npy", maximum_features)
np.save("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_min_y.npy", minimum_labels)
np.save("C:/Aimsun Projects/Calibration Using Neural Networks/normalized_minmax_model_max_y.npy", maximum_labels)'''

model_dir = "C:/Aimsun Projects/Departure-Time Travel-Mode and Route Choice Model/metro3/trip_assignment/calibration_models"
model_norm_minmax.save(os.path.join(model_dir,"normalized_minmax_model.h5"))
np.save(os.path.join(model_dir,"normalized_minmax_model_min_x.npy"), minimum_features)
np.save(os.path.join(model_dir,"normalized_minmax_model_max_x.npy"), maximum_features)
np.save(os.path.join(model_dir,"normalized_minmax_model_min_y.npy"), minimum_labels)
np.save(os.path.join(model_dir,"normalized_minmax_model_max_y.npy"), maximum_labels)

#==============================================================================
model_norm_minmax2 = keras.Sequential([
    keras.layers.Flatten(input_shape=(162,6)),
    keras.layers.Dense(256, activation=tf.nn.relu),
    keras.layers.Dense(9, activation=tf.nn.sigmoid)
])
model_norm_minmax2.compile(loss='mse', 
                          optimizer=tf.train.RMSPropOptimizer(0.001), 
                          metrics=['mae'])
model_norm_minmax2.fit(train_features_minmax, train_labels_minmax, epochs=500, validation_split=0.2)


[loss, mae] = model_norm_minmax2.evaluate(test_features_minmax, test_labels_minmax)
print("Testing set Mean Abs Error: {}".format(mae))


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
model_norm_minmax2.predict(sample1) * (maximum_labels - minimum_labels) + minimum_labels


labels[0]


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
model_norm_minmax.predict(sample1) * (maximum_labels - minimum_labels) + minimum_labels


def singleVarModel(x, y, hidden_neurons=32):
    # one variable only
    model = keras.Sequential([
        keras.layers.Flatten(input_shape=(162,6)),
        keras.layers.Dense(hidden_neurons, activation=tf.nn.relu),
        keras.layers.Dense(1, activation=tf.nn.sigmoid)
    ])
    model.compile(loss='mse', 
                              optimizer=tf.train.RMSPropOptimizer(0.001), 
                              metrics=['mae'])
    model.fit(x, y, epochs=500, validation_split=0.2)
    return model


reactionTimeModel = singleVarModel(train_features_minmax, train_labels_minmax[:,0])
[loss, mae] = reactionTimeModel.evaluate(test_features_minmax, test_labels_minmax[:,0])
print("Testing set Mean Abs Error: {}".format(mae))


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
reactionTimeModel.predict(sample1) * (maximum_labels[0] - minimum_labels[0]) + minimum_labels[0]


vehAggModel = singleVarModel(train_features_minmax, train_labels_minmax[:,1])
[loss, mae] = vehAggModel.evaluate(test_features_minmax, test_labels_minmax[:,1])
print("Testing set Mean Abs Error: {}".format(mae))


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
vehAggModel.predict(sample1) * (maximum_labels[1] - minimum_labels[1]) + minimum_labels[1]


models = []
for i in range(9):
    models.append(singleVarModel(train_features_minmax, train_labels_minmax[:,i]))


sample1 = np.zeros_like(features[:1])
sample1[:1,:,:2] = (features[:1,:,:2] - minimum_features) / (maximum_features - minimum_features)
sample1[:1,:,2:] = features[:1,:,2:]
y = []
for i in range(9):
    y.append(np.asscalar(models[i].predict(sample1)))
y = np.array(y) * (maximum_labels - minimum_labels) + minimum_labels
y


labels[0]




