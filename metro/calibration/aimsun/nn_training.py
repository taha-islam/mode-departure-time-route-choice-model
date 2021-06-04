# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 16:05:37 2020

@author: islam
"""

import os
import sys
'''if __name__ == "__main__":
    package_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                "../../../.."))
    sys.path.append(package_path)
'''
import tensorflow as tf
from keras import backend as K, regularizers
from keras.models import Model, save_model, load_model
from keras.layers import Input, Dense, Dropout, BatchNormalization, Activation, multiply, add, concatenate
from keras.optimizers import adam
from matplotlib import pyplot as plt
from sklearn.metrics import r2_score
import numpy as np
import evaluate
import csv
import fnmatch

OUTPUT_INDICES = [0,1,2,3,4,5,9]
PARAMETERS = {0:'simStep',
              1:'CFAggressivenessMean',
              2:'maxAccelMean',
              3:'normalDecelMean',
              4:'aggressiveness',
              5: 'cooperation',
              6: 'onRampMergingDistance',
              7: 'distanceZone1',
              8: 'distanceZone2',
              9: 'clearance'}
OUTPUT_RANGES = [[0.1, 1.5], [-1, 1], [1, 4], [1, 5], [0, 100], [0, 100], [0.1, 2.0]]

AIMSUM_PROGRAM_NAME = 'calibration_data_gen.py'
DATASET_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                             'datasets//'))
DATASET_PATH_OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                             'prediction_output.csv'))

def file_name_to_id(file_name):
    try:
        return int(file_name.partition(".")[0][1:])
    except:
        assert False, F"Can't get id number from {file_name}."

def id_to_output_file_name(id):
    return 'y' + str(id) + '.csv'
        
def get_output_file_name(input_file_name):
    id = file_name_to_id(input_file_name)
    return id_to_output_file_name(id)

def read_data(directory):
    all_files = os.listdir(directory)
    input_file_names = fnmatch.filter(all_files, 'x*.csv')
    output_file_names = fnmatch.filter(all_files, 'y*.csv')

    assert len(input_file_names) == len(output_file_names), \
        "Sizes of input & output don't match"
    
    x = []
    y = []
    for input_file_name in input_file_names:
        output_file_name = get_output_file_name(input_file_name)

        input_file_path  = directory + '/' + input_file_name
        output_file_path = directory + '/' + output_file_name

        #Read output data: append output for every row in x table
        output = []
        with open(output_file_path, newline='') as outputcsvfiles:      
            outputcsvreader = csv.reader(outputcsvfiles)
            for outputrow in outputcsvreader:
                if outputrow[0] == '':
                    output.append(0.0)
                else:
                    output.append(float(outputrow[0]))

        with open(input_file_path, newline='') as inputcsvfiles:
            inputcsvreader = csv.reader(inputcsvfiles)
            next(inputcsvreader)
            for inputrow in inputcsvreader:
                id, interval, _, speed, _, _, flow_per_lane, density_per_lane, \
                    before_onramp, after_onramp, before_offramp, after_offramp = np.array(inputrow, dtype=float)

                x.append([id, interval, speed, flow_per_lane, before_onramp, after_onramp, before_offramp, after_offramp])
                y.append(output)

    return np.array(x), np.array(y)

def csv_write(data, indices, path_to_file):
    with open(path_to_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)    
        writer.writerow(indices)
        for row in data:
            writer.writerow(row)

# Limit outputs as a set of sigmoid activation functions at the output layer.
def output_limits(x, beta, ranges):
    assert x.shape[1] == len(OUTPUT_INDICES), F"Input shape into the limit activation is {np.shape(x)}, \
                                                however the expected shape is ({np.shape(x)[0]}, {len(OUTPUT_INDICES)})"

    x = add([multiply([tf.reshape(K.sigmoid(x * beta), [len(OUTPUT_INDICES), ]), (ranges[:, 1] - ranges[:, 0])]), ranges[:, 0]])

def main():
    global DATASET_PATH, DATASET_PATH_OUT
    def aimsun_loss(y_true, y_predict):
        evaluate_args = {PARAMETERS[i]:j for i, j in zip(OUTPUT_INDICES, y_predict)}
        row_index = np.where(y == y_true)[0][0]

        detector_id = detector_input[row_index]
        #interval    = interval_input[row_index]
        #value       = value_input[row_index]
        true_speed = value_input.take([0], axis=1)
        true_flow = value_input.take([1], axis=1)
        #x_true = (detector_id, interval, value)

        #return evaluate.evaluate(x_true, y_predict)
        return evaluate.evaluate(true_flow, true_speed,
             ini_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/generate_calibration_data.ini',
             id = 890,
             index = 0,
             dataset_dir = os.path.normpath(os.path.dirname(__file__)),
             objects_file = 'C:/Aimsun Projects/Calibration Using Neural Networks/list_detectors.csv',
             w_flow=0.5,
             w_speed=0.5,
             **evaluate_args)
      

    cwd = os.getcwd()
    x, y = read_data(DATASET_PATH)
    #x1, y1 = csv_read_structure2(cwd + '/../data2/dataset1')
    #x2, y2 = csv_read_structure2(cwd + '/../data3/dataset2')
    #x = np.concatenate((x1, x2), axis=0)
    #y = np.concatenate((y1, y2), axis=0)
    #data_size = len(x)

    #Split inputs & select output
    detector_input  = x.take([0], axis=1)
    interval_input  = x.take([1], axis=1)
    value_input     = x.take([2,3], axis=1)
    location_input  = x.take([4,5,6,7], axis=1)

    selected_output = y.take(OUTPUT_INDICES, axis=1)

    #Detector input
    detector_input_layer = Input(shape=(1, ))   # No forward pass on this layer, only to keep track of data

    #Interval input
    interval_input_layer = Input(shape=(1, )) 
    interval_dense_1     = Dense(5, kernel_regularizer=regularizers.l1_l2())(interval_input_layer)

    #Value input
    value_input_layer = Input(shape=(2, )) 
    value_normalize   = BatchNormalization(axis=1, momentum=0.99, epsilon=0.0001)(value_input_layer)
    value_dense_1     = Dense(10, kernel_regularizer=regularizers.l1_l2())(value_normalize)
    value_dense_2     = Dense(20, kernel_regularizer=regularizers.l1_l2())(value_dense_1)

    #Location input
    location_input_layer = Input(shape=(4, ))
    location_dense_1     = Dense(4, kernel_regularizer=regularizers.l1_l2())(location_input_layer)
    location_dense_2     = Dense(2, kernel_regularizer=regularizers.l1_l2())(location_dense_1)

    #Concatenate inputs
    combined_layer  = concatenate([interval_dense_1, value_dense_2, location_dense_2])
    combined_dense1 = Dense(50, kernel_regularizer=regularizers.l1_l2())(combined_layer)
    combined_dense2 = Dense(50, kernel_regularizer=regularizers.l1_l2())(combined_dense1)
    output          = Dense(len(OUTPUT_INDICES), kernel_regularizer=regularizers.l1_l2())(combined_dense2)
    limited_output  = Activation(output_limits(output, beta=1, ranges=tf.convert_to_tensor(OUTPUT_RANGES, dtype=tf.float32)))(output) 

    #model = Model([detector_input_layer, interval_input_layer, value_input_layer, location_input_layer], limited_output)
    model = Model([interval_input_layer, value_input_layer, location_input_layer], limited_output)

    #model.compile(loss=aimsun_loss, optimizer=adam(learning_rate = 0.0005))
    model.compile(loss='mean_squared_error', optimizer=adam(learning_rate = 0.0005))

    max_epoch = 500

    history = model.fit([interval_input, value_input, location_input], selected_output, batch_size=1000, epochs=max_epoch, validation_split=0.2, verbose=1, shuffle=True)

    save_model(model, cwd + '/../model/prediction_model_structure2.h5')

    y_predict = model.predict([interval_input, value_input, location_input])

    r2 = r2_score(selected_output, y_predict, multioutput='raw_values')
    print(F"\nR2: {r2}")

    #csv_parser.csv_write(y, cwd + '/../output/true.csv')
    csv_write(y_predict, OUTPUT_INDICES, DATASET_PATH_OUT)

    val_loss = history.history['val_loss']

    min_val_loss = min(val_loss)
    min_val_loss_index = val_loss.index(min_val_loss)

    print(F"\nMinimum validation mse: {min_val_loss:.5f}\nEpoch: {min_val_loss_index}")

    # summarize history for loss
    #plot_min_epoch = 500
    
    #plt.xlim([plot_min_epoch, max_epoch])
    plt.ylim([0, 500])
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title(F'mean squared loss: Indices {OUTPUT_INDICES} \
                \nMinimum validation mse: {min_val_loss:.5f}(Epoch: {min_val_loss_index})')
    plt.ylabel('msl')
    plt.xlabel('epoch')
    plt.legend([F'train (final loss: {history.history["loss"][-1]:.2f})', \
                F'test (final loss: {history.history["val_loss"][-1]:.2f})'], loc='upper right')
    plt.show()



if __name__ == "__main__":
    sys.exit(main())




