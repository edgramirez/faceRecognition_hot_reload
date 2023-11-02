#!/usr/bin/env python3

################################################################################
# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
################################################################################

import sys
import gi
import configparser
sys.path.append('../')
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from gi.repository import GLib
from ctypes import *
import time
import math
import platform
import lib.biblioteca as biblio

from common.bus_call import bus_call
#if "aarch64" in platform.platform():
from common.is_aarch_64 import is_aarch64

from common.FPS import GETFPS
import numpy as np
import pyds
import cv2
import os
import os.path
from os import path


import lib.common as com
import lib.validate as validate
import face_recognition
from datetime import datetime, timedelta
import threading

from random import randrange
import random



fps_streams = {}
frame_count = {}

saved_count = {}

global scfg
scfg = {}
call_order_of_keys = []
global PGIE_CLASS_ID_FACE
PGIE_CLASS_ID_FACE=0
global PGIE_CLASS_ID_MAKE
PGIE_CLASS_ID_MAKE=2

MAX_DISPLAY_LEN=64
PGIE_CLASS_ID_FACE = 0

# 6-Nov-2021
# Variables no para necesarias para este modelo
#
#PGIE_CLASS_ID_PLATE = 1
#PGIE_CLASS_ID_MAKE = 2
#PGIE_CLASS_ID_MODEL = 3

MUXER_OUTPUT_WIDTH=1920
MUXER_OUTPUT_HEIGHT=1080
MUXER_BATCH_TIMEOUT_USEC=4000000
TILED_OUTPUT_WIDTH=1920
TILED_OUTPUT_HEIGHT=1080
GST_CAPS_FEATURES_NVMM="memory:NVMM"

CURRENT_DIR = os.getcwd()
# 0 cualquir cosa es reconocida como rostro, 
# 1 es la maxima confidencia de que ese objeto es un rostro
DEEPSTREAM_FACE_RECOGNITION_MINIMUM_CONFIDENCE = .86
# bytes, permite elegir solo frames de un tamaño adecuado
FRAME_SIZE = 1024*20


global known_face_encodings
global known_face_metadata
global services_dict
global known_faces_indexes_dictionary
global active_ids_per_camera # TODO los procesos que modifican este dictionario deberian ser por semaforo   Siempre y cuando alla mas de una fuente ejecutandose
global inactive_ids_per_camera # TODO los procesos que modifican este dictionario deberian ser por semaforo  Siempre y cuando alla mas de una fuente ejecutandose
global treated_ids # TODO los procesos que modifican este dictionario deberian ser por semaforo  Siempre y cuando alla mas de una fuente ejecutandose
global service_dbs
global services_encodings
global services_metas
global video_initial_time
global fake_frame_number
global found_faces_dictionary
global tracking_absence_dict
global output_file
global input_file
global face_detection_url
global image_group_type
global delta_time
global service_camera_mac_address
global header
global blacklist_db_dict
global whitelist_db_dict
global blacklist_encodings
global blacklist_metas
global whitelist_encodings
global whitelist_metas


image_group_type = {}
face_detection_url = {}
known_faces_indexes_dictionary = {}
active_ids_per_camera = {}
inactive_ids_per_camera = {}
treated_ids = {}
known_face_metadata = {}
known_face_encodings = {}
found_faces_dictionary = {}
tracking_absence_dict = {}
output_file = {}
service_dbs = {}
services_encodings = {}
services_metas = {}
input_file = {}
services_dict = {}
delta_time = {}
service_camera_mac_address = {}
fake_frame_number = 0
header = None
blacklist_db_dict = {}
whitelist_db_dict = {}
blacklist_encodings = {}
blacklist_metas = {}
whitelist_encodings = {}
whitelist_metas = {}

baseDir = 'configs/'
faceProto = baseDir + "opencv_face_detector.pbtxt"
faceModel = baseDir + "opencv_face_detector_uint8.pb"
ageProto = baseDir + "age_deploy.prototxt"
ageModel = baseDir + "age_net.caffemodel"
genderProto = baseDir + "gender_deploy.prototxt"
genderModel = baseDir + "gender_net.caffemodel"

MODEL_MEAN_VALUES=(78.4263377603, 87.7689143744, 114.895847746)
ageList = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']
genderList = ['Male','Female']

faceNet = cv2.dnn.readNet(faceModel, faceProto)
ageNet = cv2.dnn.readNet(ageModel, ageProto)
genderNet = cv2.dnn.readNet(genderModel, genderProto)



### setters ###
def set_header(token_file = None):
    if token_file is None:
        token_file = os.environ['FACE_RECOGNITION_TOKEN']

    if com.file_exists(token_file):
        global header
        token_handler = com.open_file(token_file, 'r+')
        header = {'Content-type': 'application/json', 'X-KAIROS-TOKEN': token_handler.read().split('\n')[0]}
        print('Header correctly set')
        return  header
    com.log_error('Unable to read token.')


def set_camera_mac_address(camera_service_id, camera_mac_addresss):
    global service_camera_mac_address

    if camera_service_id not in service_camera_mac_address:
        service_camera_mac_address.update({camera_service_id: camera_mac_addresss})
    else:
        service_camera_mac_address[camera_service_id] = camera_mac_addresss


def get_camera_mac_address(camera_service_id):
    global service_camera_mac_address

    if camera_service_id not in service_camera_mac_address:
        com.log_error("Unable to found mac address value for service id: {}".format(camera_service_id))
    else:
        return service_camera_mac_address[camera_service_id]


def get_group_type(camera_service_id):
    global scfg
    if camera_service_id in scfg:
        for service_name in scfg[camera_service_id].keys():
            return service_name
    else:
        com.log_error('get_group_type() - Unable to get the group type for key: {}'.format(camera_service_id))


def set_blacklist_db_outputs_and_inputs(srv_camera_id, output_db_name):
    global scfg
    search_db_name = com.BLACKLIST_DB_DIRECTORY + '/' + com.BLACKLIST_DB_NAME

    if com.file_exists_and_not_empty(search_db_name):
        # guarda el nombre de la base de datos general de todos los rostros detectados
        set_output_db_name(srv_camera_id, output_db_name)
        # guarda el nombre de la base de datos que contiene los rostros a buscar
        set_known_faces_db_name(srv_camera_id, search_db_name)
        # extrae las codificaciones y metadata de cada una de los rotros almacenados en la base de datos de rostros a buscar
        encodings, metadata = biblio.read_pickle(get_known_faces_db_name(srv_camera_id), False)
        # saving the endings and metadata en sus dictionarios globales correspondientes
        set_known_faces_db(srv_camera_id, encodings, metadata)
        return True

    com.log_error('Unable to setup blacklist input/output service variables - blacklist seach db "{}" does not exists'.format(search_db_name))


def set_whitelist_db_outputs_and_inputs(camera_service_id, output_db_name):
    global scfg

    # unique name of the DB of detected faces
    search_db_name = com.WHITELIST_DB_DIRECTORY + '/' + com.WHITELIST_DB_NAME

    if com.file_exists_and_not_empty(search_db_name):
        set_output_db_name(camera_service_id, output_db_name)
        set_known_faces_db_name(camera_service_id, search_db_name)
        encodings, metadata = biblio.read_pickle(get_known_faces_db_name(camera_service_id), False)
        set_known_faces_db(camera_service_id, encodings, metadata)
        return True

    com.log_error('Unable to setup whitelist input/output service variables - whitelist seach db "{}" does not exists'.format(search_db_name))


def set_blacklist_db(camera_id, db_name=None):
    global blacklist_db_dict

    if camera_id not in blacklist_db_dict:
        if db_name is None:
            db_name = get_default_blacklist_db()

        if com.file_exists_and_not_empty(db_name) is False:
            com.log_error('Unable to open file {}'.format(db_name))

        blacklist_db_dict.update({camera_id: db_name})


'''
def set_whitelist_db(camera_id, db_name=None):
    global whitelist_db_dict

    if camera_id not in whitelist_db_dict:
        if db_name is None:
            db_name = get_default_whitelist_db()

        if com.file_exists_and_not_empty(db_name) is False:
            com.log_error('Unable to open file {}'.format(db_name))

        whitelist_db_dict.update({camera_id: db_name})
'''

def get_default_blacklist_db():
    return com.INPUT_DB_DIRECTORY + '/blacklist_db/BlackList.dat'


def get_default_whitelist_db():
    return com.INPUT_DB_DIRECTORY + '/whitelist_db/WhiteList.dat'


def set_service_outputs_and_variables(camera_service_id, group_type):
    encodings, metadata = [], []
    output_db_name = com.RESULTS_DIRECTORY + '/found_faces_db.dat'

    if group_type == com.IMAGE_GROUPS[0]:
        db_name = com.INPUT_DB_DIRECTORY + '/blacklist_db/BlackList.dat'
    else:
        db_name = com.INPUT_DB_DIRECTORY + '/whitelist_db/WhiteList.dat'

    if com.file_exists(db_name):
        set_output_db_name(camera_service_id, output_db_name)
        set_known_faces_db_name(camera_service_id, db_name)
        encodings, metadata = biblio.read_pickle(get_known_faces_db_name(camera_service_id), False)
        set_known_faces_db(camera_service_id, encodings, metadata)
    else:
        com.log_error('Unable to open source file {}'.format(db_name))


def get_whitelist_url():
    return com.USER_SERVER_ENDPOINT + '/api/#api-Stream-Stream_-_White_list'


def get_blacklist_url(camera_service_id):
    return com.USER_SERVER_ENDPOINT + '/api/#api-Stream-Stream_-_Black_list'


def set_services_x_camera(camera_id, service_name):
    global services_dict, scfg

    '''
    print(com.SERVICE_DEFINITION[com.SERVICES['video-BlackList']])
    print(com.BLACKLIST_DB_NAME)
    print(com.SERVICE_DEFINITION[com.SERVICES['video-WhiteList']])
    print(com.WHITELIST_DB_NAME)
    quit()
    '''
    if service_name in com.SERVICES:
        if camera_id not in services_dict:
            services_dict.update({camera_id: [service_name]})
        else:
            services_dict[camera_id].append(service_name)

        return True

    '''
    if service_name not in com.SERVICES:
        # Create a unique database of detected face encodings from each video or source
        video_encodings = com.RESULTS_DIRECTORY + '/face_encodings_' + srv_camera_id + '.dat'
        video_metadatas = com.RESULTS_DIRECTORY + '/face_metadatas_' + srv_camera_id + '.dat'

        action.update({srv_camera_id: service_name})

        if service_name == com.SERVICE_DEFINITION[com.SERVICES['find']]:
            com.log_debug('Set "find" variables for service id: {}'.format(srv_camera_id))
        elif service_name in com.SERVICE_DEFINITION[com.SERVICES['video-BlackList']] and com.BLACKLIST_DB_NAME:
            com.log_debug('Set "video-BlackList" variables for service id: {}'.format(srv_camera_id))
            set_blacklist_url(srv_camera_id)
            #set_blacklist_db_outputs_and_inputs(srv_camera_id, video_encodings)
        elif service_name in com.SERVICE_DEFINITION[com.SERVICES['video-WhiteList']] and com.WHITELIST_DB_NAME:
            com.log_debug('Set "whiteList" variables for service id: {}'.format(srv_camera_id))
            set_whitelist_url(srv_camera_id)
            #set_whitelist_db_outputs_and_inputs(srv_camera_id, video_encodings)
        elif service_name in com.SERVICE_DEFINITION[com.SERVICES['ageAndGender']]:
            com.log_debug('Set "Age and Gender" variables for service id: {}'.format(srv_camera_id))

        return True
    '''

    com.log_error('Unable to set up value:{}, must be one of this: {}'.format(service_name, com.SERVICES))


def set_known_faces_db_name(camera_service_id, value):
    # TODO instead of using a separated variable to store the input file, store and read this from config scfg global dictionary 
    global input_file
    input_file.update({camera_service_id: value})


def set_output_db_name(camera_service_id, value):
    global output_file
    output_file.update({camera_service_id: value})


def set_metadata(camera_service_id, metadata):
    global known_face_metadata
    known_face_metadata.update({camera_service_id: metadata})


def set_encoding(camera_service_id, encodings):
    global known_face_encodings
    known_face_encodings.update({camera_service_id: encodings})


def set_known_faces_db(camera_service_id, encodings, metadata):
    set_encoding(camera_service_id, encodings)
    set_metadata(camera_service_id, metadata)


def set_tracking_absence_dict(camera_id, dictionary):
    global tracking_absence_dict

    if camera_id in tracking_absence_dict:
        tracking_absence_dict[camera_id] = dictionary
    else:
        tracking_absence_dict.update({camera_id: dictionary})


def set_known_faces_indexes(camera_service_id, new_list = None):
    global known_faces_indexes_dictionary

    if new_list:
        known_faces_indexes_dictionary.update({camera_service_id: new_list})
    else:
        known_faces_indexes_dictionary.update({camera_service_id: []})


def add_faces_encodings(camera_service_id, face_encoding):
    global known_face_encodings

    if camera_service_id in known_face_encodings:
        known_face_encodings[camera_service_id].append(face_encoding)
    else:
        com.log_error('add_faces_encodings() - No value found for camera_service_id: {}'.format(camera_service_id))


### getters ###
def get_face_detection_url(camera_service_id):
    global face_detection_url

    if camera_service_id in face_detection_url:
        return face_detection_url[camera_service_id]

    com.log_error('get_face_detection_url() - No value found for camera_service_id: {}'.format(camera_service_id))


def get_services_x_camera(camera_service_id):
    global services_dict

    if camera_service_id in services_dict:
        return services_dict[camera_service_id]

    com.log_error('get_services_x_camera() - No value found for camera_service_id: {}'.format(camera_service_id))


def get_output_db_name(camera_service_id):
    # TODO instead of use a serparated variable to store diferent paths 
    # use the scfg config dictionary
    global output_file

    if camera_service_id in output_file:
        return output_file[camera_service_id]

    com.log_error('get_output_db_name() - No value found for camera_service_id: {}'.format(camera_service_id))


def get_known_faces_db_name(camera_service_id):
    global input_file

    if camera_service_id in input_file:
        return input_file[camera_service_id]

    com.log_error('get_known_faces_db_name() - No value found for camera_service_id: {}'.format(camera_service_id))


def get_known_faces_db(camera_service_id):
    global known_face_metadata, known_face_encodings
    return known_face_metadata[camera_service_id], known_face_encodings[camera_service_id]


def get_known_faces_indexes(camera_service_id):
    global known_faces_indexes_dictionary

    if camera_service_id in known_faces_indexes_dictionary:
        return known_faces_indexes_dictionary[camera_service_id]
    return []


'''
def get_not_applicable_id(camera_service_id, abort = True):
    global not_applicable_id

    if camera_service_id in not_applicable_id:
        return not_applicable_id[camera_service_id]

    if abort:
        com.log_error('get_not_applicable_id() - No value found for camera_service_id: {}'.format(camera_service_id))
    else:
        return []


def set_not_applicable_id(camera_service_id, new_value, best_index = None):
    global not_applicable_id

    if best_index is not None:
        not_applicable_id[camera_service_id][best_index] = new_value
    else:
        # if key is not already in the global dictionary 
        if camera_service_id not in not_applicable_id:
            not_applicable_id.update({camera_service_id: {new_value}})
        else:
            not_applicable_id[camera_service_id].add(new_value)
'''


def get_tracking_absence_dict(camera_id):
    global tracking_absence_dict

    if camera_id in tracking_absence_dict:
        return tracking_absence_dict[camera_id]
    else:
        return {}


def get_found_faces(camera_service_id):
    #global found_faces
    global found_faces_dictionary
    if camera_service_id in found_faces_dictionary:
        return found_faces_dictionary[camera_service_id]
    else:
        return []


def get_camera_id(camera_service_id):
    global call_order_of_keys
    return call_order_of_keys[camera_service_id]


def set_recurrence_delta(camera_service_id, secs):
    global delta_time

    if not isinstance(secs, int):
        com.log_error('delta time value must be integer')

    if camera_service_id in delta_time:
        delta_time[camera_service_id] = secs
    else:
        delta_time.update({camera_service_id: secs})


def get_delta(camera_service_id):
    global delta_time
    return delta_time[camera_service_id]


def get_similarity(camera_service_id):
    return 0.6


def save_found_faces(camera_service_id, metadata_of_found_faces):
    #global found_faces
    global found_faces_dictionary
    found_faces_dictionary.update({camera_service_id: metadata_of_found_faces})


def crop_and_get_faces_locations(n_frame, obj_meta, confidence):
    # convert python array into numy array format.
    frame_image = np.array(n_frame, copy=True, order='C')

    # convert the array into cv2 default color format
    rgb_frame = cv2.cvtColor(frame_image, cv2.COLOR_RGB2BGR)

    # draw rectangle and crop the face
    crop_image = draw_bounding_boxes(rgb_frame, obj_meta, confidence)

    return crop_image


def add_new_face_metadata(camera_service_id, face_image, confidence, difference, obj_id):
    """
    Add a new person to our list of known faces
    """
    global known_face_metadata
    today_now = datetime.now()
    name = str(obj_id) + '_'+ camera_service_id + '_' + str(today_now)
    face_id = camera_service_id + '_' + str(com.get_timestamp())

    known_face_metadata[camera_service_id].append({
        'name': name,
        'face_id': face_id,
        'first_seen': today_now,
        'first_seen_this_interaction': today_now,
        'image': face_image,
        'confidence': [confidence],
        'difference': [difference],
        'last_seen': today_now,
        'seen_count': 1,
        'seen_frames': 1
    })

    # Json data format
    data = {
            'name': name,
            'faceId': face_id,
            'cameraID': camera_service_id,
            'faceType': 0,
            '#initialDate': today_now,
            'numberOfDetections': 1,
            'image': face_image
            }

    #background_result = threading.Thread(target=send_json, args=(data, 'POST', get_face_detection_url(),))
    #background_result.start()

    return known_face_metadata


def register_new_face_3(camera_service_id, face_encoding, image, confidence, difference, obj_id):
    # Add the new face metadata to our known faces metadata
    add_new_face_metadata(camera_service_id, image, confidence, difference, obj_id)
    # Add the face encoding to the list of known faces encodings
    add_faces_encodings(camera_service_id, face_encoding)
    # Add new element to the list - this list maps and mirrows the face_ids for the meta
    #add_new_known_faces_indexes(obj_id)
    update_known_faces_indexes(camera_service_id, obj_id)


def update_known_faces_indexes(camera_service_id, new_value):
    global known_faces_indexes_dictionary

    if camera_service_id in known_faces_indexes_dictionary:
        known_faces_indexes_dictionary[camera_service_id].append(new_value)
    else:
        known_faces_indexes_dictionary.update({camera_service_id: [new_value]})


def get_gender_and_age(image):
    blob = cv2.dnn.blobFromImage(image, 1.0, (227,227), MODEL_MEAN_VALUES, swapRB=False)

    genderNet.setInput(blob)
    genderPreds = genderNet.forward()
    gender = genderList[genderPreds[0].argmax()]
    print(f'Gender: {gender}')

    ageNet.setInput(blob)
    agePreds=ageNet.forward()
    age=ageList[agePreds[0].argmax()]
    print(f'Age: {age[1:-1]} years')


def encoding_image_from_source(camera_id, image, confidence, name=None):
    # codificando la imagen obtenida desde el streaming
    img_encoding, img_metadata = biblio.encode_face_image(image, name, camera_id, confidence, None, 0, model="cnn")

    # si el modelo de "face recognition" puede generar una codificacion de la imagen su valor es diferente de None
    if img_encoding is None:
        return [], [] 

    return img_encoding, img_metadata


def classify_to_known_and_unknown(camera_id, image, obj_id, name, confidence, frame_number, delta, default_similarity, known_faces_indexes, known_face_metadata, known_face_encodings, pad_index):
    # Using face_detection library, try to encode the image
    # update = False
    # best_index = None

    not_applicable_id = get_not_applicable_id(camera_id, abort = False)

    if obj_id in not_applicable_id:
        return False

    if obj_id not in known_faces_indexes:
        # codificando la imagen obtenida desde el streaming 
        img_encoding, img_metadata = biblio.encode_face_image(image, name, camera_id, confidence, None, 1, model="cnn")

        # si el modelo de "face recognition" puede generar una codificacion de la imagen su valor es diferente de None
        if img_encoding is None:
            return  False

        # comparamos el rostro codificado que se obtuvo del streaming contra la BD de rostros a buscar
        metadata, best_index, difference = biblio.lookup_known_face(img_encoding, known_face_encodings, known_face_metadata)

        current_group_type = get_group_type(camera_id)
        print('Camara Service id: {}, Current Groupt Type: {}, streaming {}'.format(camera_id, current_group_type, pad_index))

        global header
        # Acciones para cuando NO hay coincidencia del rostro 
        if best_index is None:
            # Actualizando la lista de ids de los rostros no coincidentes
            set_not_applicable_id(camera_id, obj_id)

            if current_group_type == 'video-WhiteList':
                # we use .tolist() to transform the ndarray to list:  ----  TypeError: Object of type 'ndarray' is not JSON serializable
                epoc_time = com.get_timestamp()
                #img_encoding_as_list = img_encoding.tolist()
                img_encoding_as_list = str(img_encoding)
                data  = {
                        'id': str(obj_id) + '_' + str(epoc_time),
                        'camera-id': get_camera_mac_address(camera_id),
                        'date': epoc_time,
                        'image_encoding': img_encoding_as_list,
                        'img_metadata': str(metadata)
                        }
                #biblio.send_json(data, 'POST', get_whitelist_url())
                background_result = threading.Thread(target=biblio.send_json, args=(header, data, 'POST', get_whitelist_url(),))
                background_result.start()
                print('Rostro con id: {}, streaming {}, no esta en la White list. Reportando incidente'.format(obj_id, pad_index))
                # Activar solo para visualizar imagen ---- cv2.imwrite(com.RESULTS_DIRECTORY + '/notInWhiteList_' + str(obj_id) + ".jpg", image)
            else:
                print('Rostro con id: {}, streaming {}, no esta en la Black list, todo ok'.format(obj_id, pad_index))
                # Activar solo para visualizar imagen ---- cv2.imwrite(com.RESULTS_DIRECTORY + '/notInBlackList_' + str(obj_id) + ".jpg", image)

            return False

        # Acciones para cuando hay coincidencia del rostro 
        if current_group_type == 'video-BlackList':
            # we use .tolist() to transform the ndarray to list:  ----  TypeError: Object of type 'ndarray' is not JSON serializable
            epoc_time = com.get_timestamp()
            #img_encoding_as_list = img_encoding.tolist()
            #img_encoding_as_list = img_encoding.tolist()
            #json_metadata = metadata
            #print(json_metadata.keys())
            #print(type(json_metadata))
            #quit()
            data  = {
                'id': str(obj_id) + '_' + str(epoc_time),
                'camera-id': get_camera_mac_address(camera_id),
                'date': epoc_time,
                'blacklist_match_name': metadata['name'],
                'image_encoding': str(img_encoding),
                'img_metadata': str(metadata)
                }
            #biblio.send_json(data, 'POST', get_blacklist_url())
            background_result = threading.Thread(target=biblio.send_json, args=(header, data, 'POST', get_blacklist_url(),))
            background_result.start()
            print('Rostro con id: {} coincide con elemento {} en la Black list , streaming {}'.format(obj_id, metadata['name'], pad_index))
            # Activar solo para visualizar imagen ---- cv2.imwrite(com.RESULTS_DIRECTORY + '/BlackListMatch_' + str(obj_id) + "_with_" + metadata['name'] + ".jpg", image)
        else:
            print('Rostro con id: {} coincide con elemento {} en la White list, streaming {}, todo Ok nada que reportar'.format(obj_id, metadata['name'], pad_index))
            # Activar solo para visualizar imagen ---- cv2.imwrite(com.RESULTS_DIRECTORY + '/WhiteListMatch_' + str(obj_id) + "_with_" + metadata['name'] + ".jpg", image)

        update_known_faces_indexes(camera_id, obj_id)
        return True

        # ID already in the list of IDs
    else:
        return False # no hace nada para ids ya identificados


def set_active_ids_x_camera(camera_id, id_from_source, frame_number):
    global scfg, active_ids_per_camera

    if camera_id not in scfg:
        com.log_error("wrong camera_id: {} - This id is not part of the configuration\n".format(camera_id))

    if camera_id not in active_ids_per_camera:
        active_ids_per_camera.update({camera_id: {id_from_source}})
    else:
        active_ids_per_camera[camera_id].add(id_from_source)


def remove_inactive_ids_x_camera(camera_id, item_to_delete):
    global active_ids_per_camera, inactive_ids_per_camera

    if camera_id in active_ids_per_camera:
        active_ids_per_camera[camera_id].remove(item_to_delete)
        del inactive_ids_per_camera[camera_id][item_to_delete]


def get_active_ids_x_camera(camera_id):
    global active_ids_per_camera

    if camera_id in active_ids_per_camera:
        return active_ids_per_camera[camera_id]


def set_inactive_ids_x_camera(camera_id, id_from_source):
    global scfg, inactive_ids_per_camera

    if camera_id not in scfg:
        com.log_error("wrong camera_id: {} - This id is not part of the configuration\n".format(camera_id))

    if camera_id not in inactive_ids_per_camera:
        inactive_ids_per_camera.update({camera_id: {id_from_source: 1}})
    else:
        if id_from_source not in inactive_ids_per_camera[camera_id]:
            inactive_ids_per_camera[camera_id].update({id_from_source: 1})
        else:
            inactive_ids_per_camera[camera_id][id_from_source] += 1


def get_inactive_ids_x_camera(camera_id):
    global inactive_ids_per_camera

    if camera_id in inactive_ids_per_camera:
        return inactive_ids_per_camera[camera_id]

    return {}


def add_to_treated_face_ids(camera_id, id_already_treated):
    global treated_ids

    if camera_id in treated_ids:
        treated_ids[camera_id].add(id_already_treated)
    else:
        treated_ids.update({camera_id: {id_already_treated}})


def get_treated_face_ids(camera_id):
    global treated_ids

    if camera_id in treated_ids:
        return treated_ids[camera_id]

    return {}


def set_whitelist_known_faces_db(camera_id, db_name = None):
    global service_dbs

    if db_name:
        whitelist_db = com.INPUT_DB_DIRECTORY + '/whitelist_db/' + db_name
    else:
        # setup the default whitelist db
        whitelist_db = com.INPUT_DB_DIRECTORY + '/whitelist_db/WhiteList.dat'

    if camera_id not in service_dbs:
        service_dbs.update({camera_id: {'whitelist_db': whitelist_db}})
    else:
        service_dbs[camera_id]['whitelist_db'] = whitelist_db
        

def get_whitelist_known_faces_db(camera_id, db_name = None):
    global service_dbs

    if camera_id in service_dbs and 'whitelist_db' in service_dbs[camera_id]:
        return biblio.read_pickle(service_dbs[camera_id]['whitelist_db'], False)

    return [], []


def set_blacklist_known_faces_db(camera_id, db_name = None):
    global service_dbs

    if db_name:
        blacklist_db = com.INPUT_DB_DIRECTORY + '/blacklist_db/' + db_name
    else:
        # setup the default whitelist db
        blacklist_db = com.INPUT_DB_DIRECTORY + '/blacklist_db/BlackList.dat'

    if camera_id not in service_dbs:
        service_dbs.update({camera_id: {'blacklist_db': blacklist_db}})
    else:
        service_dbs[camera_id]['blacklist_db'] = blacklist_db


def get_blacklist_known_faces_db(camera_id, db_name = None):
    global service_dbs

    if camera_id in service_dbs and 'blacklist_db' in service_dbs[camera_id]:
        return biblio.read_pickle(service_dbs[camera_id]['blacklist_db'], False)

    return {}


def whitelist_process(image_encoding, image_meta):
    global whitelist_encodings, services_whitelist_metas

    metadata, best_index, difference = biblio.lookup_known_face(image_encoding, known_face_encodings, known_face_metadata)


def tiler_sink_pad_buffer_probe(pad, info, u_data):
    global fake_frame_number
    frame_number = 0		# Faltaba del archivo Original deepstream_imagedata_multistream
    num_rects = 0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    contador = 0
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        is_first_obj = True
        save_image = False
        obj_counter = { PGIE_CLASS_ID_FACE:0 }
        camera_id = get_camera_id(pyds.NvDsFrameMeta.cast(l_frame.data).pad_index)
        service_per_camera = get_services_x_camera(camera_id)
        delta = get_delta(camera_id)
        default_similarity = get_similarity(camera_id)
        #known_face_metadata, known_face_encodings = get_known_faces_db(camera_id)
        #whitelist_metas whitelist_encodings Loaded already in this global variables
        tracking_absence_dict = get_tracking_absence_dict(camera_id)
        id_set = set()

        while l_obj is not None:
            contador += 1

            try: 
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            # Save the annotated frame to file.
            if obj_meta.class_id == 0 and obj_meta.confidence > DEEPSTREAM_FACE_RECOGNITION_MINIMUM_CONFIDENCE:
                # Getting Image data using nvbufsurface
                # the input should be address of buffer and batch_id
                n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                frame_image = crop_and_get_faces_locations(n_frame, obj_meta, obj_meta.confidence)

                # El tamaño del frame mayor que 0 evita recuadros de rostros vacios
                # se se aumenta el tamaño se estará selecionando frames mas grandes y visibles
                if frame_image.size > FRAME_SIZE: 
                    #known_faces_indexes = get_known_faces_indexes(camera_id)
                    #not_applicable_id = get_not_applicable_id(camera_id, abort = False)

                    id_set.add(obj_meta.object_id)
                    set_active_ids_x_camera(camera_id, obj_meta.object_id, frame_number)
                    previous_treated_elements = get_treated_face_ids(camera_id)

                    if obj_meta.object_id not in previous_treated_elements:
                        print("Trying to process image ................", obj_meta.object_id, obj_meta.confidence)
                        # tratar de generar un codificado de la imagen
                        image_encoding, image_meta = encoding_image_from_source(camera_id, frame_image, obj_meta.confidence)

                        # si se logro codificar (es decir, no es vacio "[]"), entonces se registra como rostro analizado y solo se vuelve a analizar si la confianza es mayor
                        if image_meta:
                            print("Image successfully processed ................", obj_meta.object_id, obj_meta.confidence)
                            add_to_treated_face_ids(camera_id, obj_meta.object_id)
                            whitelist_process(image_encoding, image_meta)     


                    '''
                    if obj_meta.object_id not in known_faces_indexes and obj_meta.object_id not in not_applicable_id:
                                                                

                    if classify_to_known_and_unknown(camera_id, frame_image, obj_meta.object_id, name, obj_meta.confidence, fake_frame_number, delta, default_similarity, known_faces_indexes, known_face_metadata, known_face_encodings, frame_meta.pad_index):
                        save_image = True
                        #cv2.imwrite('/tmp/found_elements/found_multiple_' + str(fake_frame_number) + ".jpg", frame_image)
                    '''

            try: 
                l_obj = l_obj.next
            except StopIteration:
                break

        # Cleaning up the active elements
        #Every n frames, get register the ids that are not present any more / ids that are not present in more 3 cycles are deleted from the list
        if frame_number % 23 == 0:
            current_active_ids_x_camera = get_active_ids_x_camera(camera_id)
            if current_active_ids_x_camera is not None:
                if len(id_set) == 0:
                    for value in current_active_ids_x_camera:
                        set_inactive_ids_x_camera(camera_id, value)
                else:
                    for value in id_set:
                        set_inactive_ids_x_camera(camera_id, value)
                
                inactive_items = get_inactive_ids_x_camera(camera_id)

                elements_to_delete = [key for key in inactive_items if inactive_items[key] > 2]

                for item in elements_to_delete:
                    remove_inactive_ids_x_camera(camera_id, item)

        #print("Frame Number=", frame_number, "Number of Objects=",num_rects,"Face_count=",obj_counter[PGIE_CLASS_ID_FACE],"Object ID =",obj_meta.object_id)
        # Get frame rate through this probe
        fps_streams["stream{0}".format(frame_meta.pad_index)].get_fps()
        #print(frame_meta.pad_index)
        
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def write_to_db(face_metadata, face_encodings, output_db_name):
    biblio.write_to_pickle(face_encodings, face_metadata, output_db_name)


def draw_bounding_boxes(image, obj_meta, confidence):
    #confidence = '{0:.2f}'.format(confidence)
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)
    #obj_name = pgie_classes_str[obj_meta.class_id]
    #image=cv2.rectangle(image,(left,top),(left+width,top+height),(0,0,255,0),2)
    #image=cv2.line(image, (left,top),(left+width,top+height), (0,255,0), 9)
    # Note that on some systems cv2.putText erroneously draws horizontal lines across the image
    #image=cv2.putText(image,obj_name+',C='+str(confidence),(left-5,top-5),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255,0),2)
    #image = cv2.putText(image, obj_name, (left-5,top-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255,0), 2)
    crop_image = image[top-20:top+height+20, left-20:left+width+20]
    return crop_image

def cb_newpad(decodebin, decoder_src_pad,data):
    print("In cb_newpad\n")
    caps=decoder_src_pad.get_current_caps()
    gststruct=caps.get_structure(0)
    gstname=gststruct.get_name()
    source_bin=data
    features=caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not
    # audio.
    if(gstname.find("video")!=-1):
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad=source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                com.log_error("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            com.log_error(" Error: Decodebin did not pick nvidia decoder plugin.\n")

def decodebin_child_added(child_proxy,Object,name,user_data):
    print("Decodebin child added:", name, "\n")
    if(name.find("decodebin") != -1):
        Object.connect("child-added",decodebin_child_added,user_data)   
    if(is_aarch64() and name.find("nvv4l2decoder") != -1):
        print("Seting bufapi_version\n")
        Object.set_property("bufapi-version",True, None)

def create_source_bin(index, uri):
    print("Creating source bin")

    # Create a source GstBin to abstract this bin's content from the rest of the
    # pipeline
    #bin_name = "source-bin-%s" %index     diferente al original deestram_imagedata_multistream
    bin_name = "source-bin-%02d" %index
    com.log_debug(bin_name)
    nbin=Gst.Bin.new(bin_name)
    if not nbin:
        com.log_error(" Unable to create source bin")

    # Source element for reading from the uri.
    # We will use decodebin and let it figure out the container format of the
    # stream and the codec and plug the appropriate demux and decode plugins.
    uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        com.log_error(" Unable to create uri decode bin")
    # We set the input uri to the source element
    uri_decode_bin.set_property("uri", uri)
    # Connect to the "pad-added" signal of the decodebin which generates a
    # callback once a new pad for raw data has beed created by the decodebin
    uri_decode_bin.connect("pad-added",cb_newpad,nbin)
    uri_decode_bin.connect("child-added",decodebin_child_added,nbin)

    # We need to create a ghost pad for the source bin which will act as a proxy
    # for the video decoder src pad. The ghost pad will not have a target right
    # now. Once the decode bin creates the video decoder and generates the
    # cb_newpad callback, we will set the ghost pad target to the video decoder
    # src pad.
    Gst.Bin.add(nbin, uri_decode_bin)
    bin_pad=nbin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
    if not bin_pad:
        com.log_error(" Failed to add ghost pad in source bin")
        return None
    return nbin

def main(args):
    global scfg, call_order_of_keys, header

    header = set_header()
    scfg = biblio.get_server_info(header)
    com.log_debug("Final configuration: \n\n {}\n\n".format(scfg))

    number_sources = 0
    sources_by_camera = {}
    for camera_mac in scfg:
        for srv_camera_id in scfg[camera_mac]:
            for service_definition in scfg[camera_mac][srv_camera_id]:
                set_camera_mac_address(srv_camera_id, scfg[camera_mac][srv_camera_id][service_definition])
                # check if the source the camera is the same as for other service
                if camera_mac not in sources_by_camera:
                    sources_by_camera.update({camera_mac: scfg[camera_mac][srv_camera_id][service_definition]['source']})
                    number_sources += 1
    is_live = False

    global blacklist_encodings, services_blacklist_metas
    global whitelist_encodings, services_whitelist_metas
    for camera_id in scfg:

        call_order_of_keys.append(camera_id)
        set_recurrence_delta(camera_id, 10)

        for srv_camera_id  in scfg[camera_id]:
            # get the service name
            service_name = srv_camera_id.split('_')[-1]

            if service_name in com.SERVICE_DEFINITION[com.SERVICES['video-BlackList']]:
                # set the blacklist db # this function assigns by default the default blacklist db but it can specified another db
                # TODO: creaar variable del nombre de la base de datos en el archivo Json 
                db_name = None  # HARDCODED db_name value to get the default db
                set_blacklist_known_faces_db(camera_id, db_name)
                #set_blacklist_db(camera_id)
                # load black list db in memory
                #blacklist_known_face_metadata, blackilst_known_face_encodings = get_known_faces_db(camera_id)
                # TODO: crear una variable en el archivo o Json que contenga el nombre de la base de datos 
                #blacklist_known_face_metadata, blackilst_known_face_encodings = get_blacklist_known_faces_db(camera_id)
                encoding, metadata = get_blacklist_known_faces_db(camera_id)
                blacklist_encodings.update({camera_id: encoding})
                blacklist_metas.update({camera_id: metadata})

            if service_name in com.SERVICE_DEFINITION[com.SERVICES['video-WhiteList']]:
                # set the whitelist db # this function assigns by default the default whitelist db but it can specified another db
                db_name = None  # HARDCODED db_name value to get the default db
                set_whitelist_known_faces_db(camera_id, db_name)
                #set_whitelist_db(camera_id)
                # load white list db in memory
                # TODO: crear una variable en el archivo o Json que contenga el nombre de la base de datos 
                encoding, metadata = get_whitelist_known_faces_db(camera_id)
                whitelist_encodings.update({camera_id: encoding})
                services_whitelist_metas.update({camera_id: metadata})

            # saving the service in the list of services for this camera
            set_services_x_camera(camera_id, service_name)

        for encoding in blacklist_encodings[camera_id]:
            metadata, best_index, difference = biblio.lookup_known_face(encoding, whitelist_encodings[camera_id], services_whitelist_metas[camera_id])
            if metadata:
                print('match: ', metadata, best_index, difference)
                for encoding22 in blacklist_encodings[camera_id]:
                    best_m, distancesss = biblio.compare_against_encoding_list(encoding, [encoding22])
                    print(best_m, distancesss)

    quit()
    com.log_debug("Numero de fuentes :{}".format(number_sources))
    print("\n------ Fps_streams: ------n", fps_streams)

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements */
    # Create Pipeline element that will form a connection of other elements
    com.log_debug("Creating Pipeline")
    pipeline = Gst.Pipeline()

    if not pipeline:
        com.log_error(" Unable to create Pipeline")
    com.log_debug("Creating streamux")

    # Create nvstreammux instance to form batches from one or more sources.
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        com.log_error(" Unable to create NvStreamMux")

    pipeline.add(streammux)
    i = 0
    for ordered_key in call_order_of_keys:
        fps_streams["stream{0}".format(i)]=GETFPS(i)    
        frame_count["stream_"+str(i)] = 0
        saved_count["stream_"+str(i)] = 0

        # Getting the service from the id (is the last element of the key after the last '_')
        service_name = ordered_key.split('_')[-1]
        uri_name = sources_by_camera[ordered_key]

        com.log_debug("Creating source_bin: {}.- {} with uri_name: {}\n".format(i, ordered_key, uri_name))
        
        if uri_name.find("rtsp://") == 0 :
            is_live = True

        source_bin = create_source_bin(i, uri_name)
        if not source_bin:
            com.log_error("Unable to create source bin")

        pipeline.add(source_bin)
        padname = "sink_%u" % i

        sinkpad = streammux.get_request_pad(padname)
        if not sinkpad:
            com.log_error("Unable to create sink pad bin")
        srcpad = source_bin.get_static_pad("src")
        if not srcpad:
            com.log_error("Unable to create src pad bin")
        srcpad.link(sinkpad)
        i += 1
   
    com.log_debug("Creating Pgie")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        com.log_error(" Unable to create pgie")
    
    # Creation of tracking to follow up the model face
    # April 21th
    # ERM
    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        com.log_error(" Unable to create tracker")
    
    # Add nvvidconv1 and filter1 to convert the frames to RGBA
    # which is easier to work with in Python.

    com.log_debug("Creating nvvidconv1 ")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
    if not nvvidconv1:
        com.log_error(" Unable to create nvvidconv1")
    com.log_debug("Creating filter1")
    caps1 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
    filter1 = Gst.ElementFactory.make("capsfilter", "filter1")
    if not filter1:
        com.log_error(" Unable to get the caps filter1")
    filter1.set_property("caps", caps1)
    com.log_debug("Creating tiler")

    tiler=Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    if not tiler:
        com.log_error("Unable to create tiler")
    com.log_debug("Creating nvvidconv")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        com.log_error(" Unable to create nvvidconv")
    com.log_debug("Creating nvosd")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        com.log_error(" Unable to create nvosd")
    if(is_aarch64()):
        com.log_debug("Creating transform")
        transform=Gst.ElementFactory.make("nvegltransform", "nvegl-transform")
        if not transform:
            com.log_error(" Unable to create transform")

    com.log_debug("Creating EGLSink")

    # edgar: cambio esta linea para no desplegar video - 
    # 6-nov-2021
    # Reprogramar para que el elemento sink tome el valor de nvegldessink ( video output ) o de fakesink (Black hole for data)
    # dependiendo si estamos en modo DEMO o produccion respectivamente

    demo_status = com.FACE_RECOGNITION_DEMO
    #print("Demo Status ",demo_status)
    if demo_status == "True":
        sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
    else:
        sink = Gst.ElementFactory.make("fakesink", "fakesink")

    if not sink:
        com.log_error(" Unable to create egl sink")

    if is_live:
        com.log_debug("At least one of the sources is live")
        streammux.set_property('live-source', 1)
    
    # Camaras meraki 720p
    # 6-Nov-2021
    # se definen las variables width y height con valores definidos al inicio

    streammux.set_property('width', MUXER_OUTPUT_WIDTH)
    streammux.set_property('height', MUXER_OUTPUT_HEIGHT)
    streammux.set_property('batch-size', number_sources)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)

    #fin de la definicion

    pgie.set_property('config-file-path',CURRENT_DIR + "/configs/pgie_config_facenet.txt")
    pgie_batch_size=pgie.get_property("batch-size")
    if(pgie_batch_size != number_sources):
        com.log_debug("WARNING: Overriding infer-config batch-size '{}', with number of sources {}".format(pgie_batch_size, number_sources))
        pgie.set_property("batch-size", number_sources)

    # Set properties of tracker
    # April 21th
    # ERM

    config = configparser.ConfigParser()
    config.read('configs/tracker_config.txt')
    config.sections()
    
    for key in config['tracker']:
        if key == 'tracker-width':
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        elif key == 'tracker-height':
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        elif key == 'gpu-id':
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        elif key == 'll-lib-file':
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        elif key == 'll-config-file':
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)
        elif key == 'enable-batch-process':
            tracker_enable_batch_process = config.getint('tracker', key)
            tracker.set_property('enable_batch_process', tracker_enable_batch_process)

    tiler_rows=int(math.sqrt(number_sources))
    tiler_columns=int(math.ceil((1.0*number_sources)/tiler_rows))
    tiler.set_property("rows",tiler_rows)
    tiler.set_property("columns",tiler_columns)
    tiler.set_property("width", TILED_OUTPUT_WIDTH)
    tiler.set_property("height", TILED_OUTPUT_HEIGHT)

    sink.set_property("sync", 0)                    # Sync on the clock 
    sink.set_property("qos", 0)                     # faltaba del archivo original deepstream_imagedata_multistream.py  Generate Quality-of-Service events upstream

    if not is_aarch64():
        # Use CUDA unified memory in the pipeline so frames
        # can be easily accessed on CPU in Python.
        #print("Arquitectura x86 ")
        mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
        streammux.set_property("nvbuf-memory-type", mem_type)
        nvvidconv.set_property("nvbuf-memory-type", mem_type)
        nvvidconv1.set_property("nvbuf-memory-type", mem_type)
        tiler.set_property("nvbuf-memory-type", mem_type)

    com.log_debug("Adding elements to Pipeline")

    # Add tracker in pipeline
    # April 21th
    # ERM

    pipeline.add(pgie)
    pipeline.add(tracker)     # Tracker
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(filter1)
    pipeline.add(nvvidconv1)
    pipeline.add(nvosd)
    if is_aarch64():
        pipeline.add(transform)
    pipeline.add(sink)

    com.log_debug("Linking elements in the Pipeline")

    # 6-nov-2021
    # Revision de elementos del pipeline
    # el filtro después del tiler no me hace sentido
    # por el momento se queda como el archivo original deepstream_imagedata_multistream.py

    streammux.link(pgie)
    pgie.link(tracker)        # se añade para tracker
    # pgie.link(nvvidconv1)     se modifica
    tracker.link(nvvidconv1)  # se añade para ligar tracker con los demas elementos
    nvvidconv1.link(filter1)
    filter1.link(tiler)
    tiler.link(nvvidconv)
    nvvidconv.link(nvosd)
    if is_aarch64():
        nvosd.link(transform)
        transform.link(sink)
    else:
        nvosd.link(sink)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    tiler_sink_pad=tiler.get_static_pad("sink")
    if not tiler_sink_pad:
        com.log_error(" Unable to get src pad")
    else:
        tiler_sink_pad.add_probe(Gst.PadProbeType.BUFFER, tiler_sink_pad_buffer_probe, 0)

    # List the sources
    com.log_debug("Now playing...")
    for source in sources_by_camera:
        com.log_debug("Now playing ... {}".format(sources_by_camera[source]))

    com.log_debug("Starting pipeline")
    # start play back and listed to events		
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    com.log_debug("Exiting app\n")
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
