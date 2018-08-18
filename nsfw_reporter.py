#!/usr/bin/env python
"""
Copyright 2016 Yahoo Inc.
Licensed under the terms of the 2 clause BSD license.
Please see LICENSE file in the project root for terms.
"""

import numpy as np
import os
import sys
import argparse
import glob
import time
import urllib2
import json
from bottle import get, run, template, request, HTTPResponse
from PIL import Image
from StringIO import StringIO
import caffe
from mastodon import Mastodon, StreamListener
from requests.exceptions import ChunkedEncodingError

def resize_image(data, sz=(256, 256)):
    """
    Resize image. Please use this resize logic for best results instead of the
    caffe, since it was used to generate training dataset
    :param str data:
        The image data
    :param sz tuple:
        The resized image dimensions
    :returns bytearray:
        A byte array with the resized image
    """
    img_data = str(data)
    im = Image.open(StringIO(img_data))
    if im.mode != "RGB":
        im = im.convert('RGB')
    imr = im.resize(sz, resample=Image.BILINEAR)
    fh_im = StringIO()
    imr.save(fh_im, format='JPEG')
    fh_im.seek(0)
    return bytearray(fh_im.read())

def caffe_preprocess_and_compute(pimg, caffe_transformer=None, caffe_net=None,
    output_layers=None):
    """
    Run a Caffe network on an input image after preprocessing it to prepare
    it for Caffe.
    :param PIL.Image pimg:
        PIL image to be input into Caffe.
    :param caffe.Net caffe_net:
        A Caffe network with which to process pimg afrer preprocessing.
    :param list output_layers:
        A list of the names of the layers from caffe_net whose outputs are to
        to be returned.  If this is None, the default outputs for the network
        are returned.
    :return:
        Returns the requested outputs from the Caffe net.
    """
    if caffe_net is not None:

        # Grab the default output names if none were requested specifically.
        if output_layers is None:
            output_layers = caffe_net.outputs

        img_data_rs = resize_image(pimg, sz=(256, 256))
        image = caffe.io.load_image(StringIO(img_data_rs))

        H, W, _ = image.shape
        _, _, h, w = caffe_net.blobs['data'].data.shape
        h_off = max((H - h) / 2, 0)
        w_off = max((W - w) / 2, 0)
        crop = image[h_off:h_off + h, w_off:w_off + w, :]
        transformed_image = caffe_transformer.preprocess('data', crop)
        transformed_image.shape = (1,) + transformed_image.shape

        input_name = caffe_net.inputs[0]
        all_outputs = caffe_net.forward_all(blobs=output_layers,
                    **{input_name: transformed_image})

        outputs = all_outputs[output_layers[0]][0].astype(float)
        return outputs
    else:
        return []

pycaffe_dir = os.path.dirname(__file__)

model_def = 'open_nsfw/nsfw_model/deploy.prototxt'
pretrained_model = 'open_nsfw/nsfw_model/resnet_50_1by2_nsfw.caffemodel'

# Pre-load caffe model.
nsfw_net = caffe.Net(model_def,  # pylint: disable=invalid-name
    pretrained_model, caffe.TEST)

# Load transformer
# Note that the parameters are hard-coded for best results
caffe_transformer = caffe.io.Transformer({'data': nsfw_net.blobs['data'].data.shape})
caffe_transformer.set_transpose('data', (2, 0, 1))  # move image channels to outermost
caffe_transformer.set_mean('data', np.array([104, 117, 123]))  # subtract the dataset-mean value in each channel
caffe_transformer.set_raw_scale('data', 255)  # rescale from [0, 1] to [0, 255]
caffe_transformer.set_channel_swap('data', (2, 1, 0))  # swap channels from RGB to BGR

def print_log(str):
    now = time.ctime()
    cnvtime = time.strptime(now)
    print(time.strftime("%Y/%m/%d %H:%M", cnvtime)+" "+str)

def setup_mastodon_config():
    config = {}
    config["client_id"] = os.getenv('CLIENT_ID')
    config["api_base_domain"] = os.getenv('API_DOMAIN')
    config["api_base_url"] = "https://" + config["api_base_domain"]
    config["client_secret"] = os.getenv('CLIENT_SECRET')
    config["access_token"] = os.getenv('ACCESS_TOKEN')
    config["threshold"] = float(os.getenv('THRESHOLD'))
    if not config["client_id"] or not config["api_base_domain"] or not config["client_secret"] or not config["access_token"] or not config["threshold"]:
        print_log("require environment value CLIENT_ID, API_DOMAIN, CLIENT_SECRET, ACCESS_TOKEN, and THRESHOLD.")
        exit()
    if config["threshold"] > 1.0 or config["threshold"] < 0.0:
        print_log("threshold is out of range (0.0<=threshold<=1.0)")
        exit()
    return config

class Listener(StreamListener):
    def __init__(self, mstdn):
        self.mstdn = mstdn

    def on_notification(self, data):
        return

    def on_update(self, data):
        if len(data['media_attachments']) > 0 and data['sensitive'] == False:
            for media in data['media_attachments']:
                image_url = media['preview_url']
                try:
                    response = urllib2.urlopen(image_url)
                    image_data = response.read()
                    scores = caffe_preprocess_and_compute(image_data, caffe_transformer=caffe_transformer, caffe_net=nsfw_net, output_layers=['prob'])
                    if scores[1] > config['threshold']:
                        self.mstdn.report(data['account']['id'], data['id'], "open_nsfw score is "+str(scores[1]))
                except urllib2.URLError as e:
                    print_log("url error: "+image_url)
                except urllib2.HTTPError as e:
                    print_log("http error: "+image_url)

    def on_delete(self, data):
        return

def try_streaming(mstdn):
    try: 
        mstdn.stream_public(Listener(mstdn))
    except ChunkedEncodingError as e:
        print_log("restart streaming")
        try_streaming(mstdn)

config = setup_mastodon_config()
mstdn = Mastodon(config["client_id"], config["client_secret"], config["access_token"], config["api_base_url"])
print_log("start streaming")
try_streaming(mstdn)
