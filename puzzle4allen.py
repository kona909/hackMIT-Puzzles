from keras.models import Sequential
from keras.layers import Dense
from keras.models import model_from_json
from keras.datasets import cifar10
import tensorflow as tf
from keras import backend as K
import cv2
from keras import utils
import numpy as np
import matplotlib
import scipy.misc
import PIL
from PIL import Image
import os
import time
import keras

(x_train, y_train), (x_test, y_test) = cifar10.load_data()

# load json and create model
json_file = open('/home/bill/Downloads/model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("/home/bill/Downloads/model.hdf5")
print("Loaded model from disk")
img_width = 32
img_height = 32

# evaluate loaded model on test data
loaded_model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])
x_train /= 255
# y_test = utils.to_categorical(y_test, 10)

print(x_train.shape, 'train samples')
print(x_test.shape, 'test samples')
y_test = utils.to_categorical(y_train, 10)
# score = loaded_model.evaluate(x_train, y_test, verbose=0)
# print("%s: %.2f%%" % (loaded_model.metrics_names[1], score[1]*100))
loaded_model.summary()

# this is the placeholder for the input images
input_img = loaded_model.input

# get the symbolic outputs of each "key" layer (we gave them unique names).

def deprocess_image(x):
    # normalize tensor: center on 0., ensure std is 0.1
    x -= x.mean()
    x /= (x.std() + 1e-5)
    x *= 0.1

    # clip to [0, 1]
    x += 0.5
    x = np.clip(x, 0, 1)

    # convert to RGB array
    x *= 255
    if K.image_data_format() == 'channels_first':
        x = x.transpose((1, 2, 0))
    x = np.clip(x, 0, 255).astype('uint8')
    return x

def normalize(x):
    # utility function to normalize a tensor by its L2 norm
    return x / (K.sqrt(K.mean(K.square(x))) + 1e-5)

layer_dict = dict([(layer.name, layer) for layer in loaded_model.layers[1:]])
kept_filters = []
# for filter_index in range(0, 32):
    # # we only scan through the first 200 filters,
    # # but there are actually 512 of them
    # print('Processing filter %d' % filter_index)
    # start_time = time.time()
    #
    # # we build a loss function that maximizes the activation
    # # of the nth filter of the layer considered
    # layer_output = layer_dict[layer_name].output
    # if K.image_data_format() == 'channels_first':
    #     loss = K.mean(layer_output[:, filter_index, :, :])
    # else:
    #     loss = K.mean(layer_output[:, :, :, filter_index])
# prediction = loaded_model.predict(input_img)
# print(prediction[:,1])
layer_output = layer_dict['predictions'].output
loss = K.mean(loaded_model.output[:, 1])
# we compute the gradient of the input picture wrt this loss
grads = K.gradients(loss, input_img)[0]

# normalization trick: we normalize the gradient
grads = normalize(grads)

# this function returns the loss and grads given the input picture

iterate = K.function([input_img], [loss, grads])
# iterate2 = K.function([], [loss, grads])
#
# step size for gradient ascent
step = 15.6
# we start from a gray image with some random noise
if K.image_data_format() == 'channels_first':
    input_img_data = np.random.random((1, 3, img_width, img_height))
    print ("channels first")
else:
    input_img_data = np.random.random((1, img_width, img_height, 3))
input_img_data = (input_img_data - 0.5) * 20 + 128

prediction = loaded_model.predict(input_img_data)
#while(prediction[:,1].astype('float32') < 0.1):
    #input_img_data = np.random.random((1, img_width, img_height, 3))
    #input_img_data = (input_img_data - 0.5) * 20 + 128
#prediction = loaded_model.predict(input_img_data)
#print(prediction[:,1].astype('float32'))
# we run gradient ascent for 20 steps
#print(layer_output = layer_dict['predictions'].output())
while (prediction[:,1].astype('float32') < 0.999):
    loss_value, grads_value = iterate([input_img_data])
    input_img_data += grads_value * step
    #input_img_data = np.random.random((1, img_width, img_height, 3))
    #input_img_data = (input_img_data - 0.5) * 20 + 128

    print('Current loss value:', loss_value)
    scipy.misc.imsave('winner.jpg', input_img_data[0])
    img = Image.open("winner.jpg")
    img.load()
    data = np.asarray(img, dtype="uint8").reshape(1, 32, 32, 3)
    prediction = loaded_model.predict(data)
    #print(prediction)
    #y_classes = np_utils.probas_to_classes(prediction)
    print (prediction)
    
    if loss_value <= 0.:
        # some filters get stuck to 0, we can skip them
        break
# #
# # # decode the resulting input image
# # # if loss_value > 0:
# # img = deprocess_image(input_img_data[0])
# prediction = loaded_model.predict(input_img_data)
# # print(prediction)
# image = input_img_data.reshape(1,256,256,3)
#
# # image = input_img_data[0]
# scipy.misc.imsave('winner.jpg', real_image[0])

    # end_time = time.time()
    # print('Filter %d processed in %ds' % (filter_index, end_time - start_time))

# we will stich the best 64 filters on a 8 x 8 grid.
n = 32

# the filters that have the highest loss are assumed to be better-looking.
# we will only keep the top 64 filters.
kept_filters.sort(key=lambda x: x[1], reverse=True)
kept_filters = kept_filters[: 25]

# build a black picture with enough space for
# our 8 x 8 filters of size 128 x 128, with a 5px margin in between
# margin = 5
# width = 8 * img_width + 7 * margin
# height = 8 * img_height + 7 * margin
# stitched_filters = np.zeros((width, height, 3))
#
# # fill the picture with our saved filters
print(len(kept_filters))
for i in range(32):
    img, loss = kept_filters[i]
    stitched_filters[(img_width + margin) * i: (img_width + margin) * i + img_width, (img_height + margin) * i: (img_height + margin) * i + img_height, :] = img
    scipy.misc.imsave(str(i)+'outfile.jpg', img)

# save the result to disk
imsave('stitched_filters_%dx%d.png' % (n, n), stitched_filters)
