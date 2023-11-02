#!/usr/bin/python3
import sys
import os
import shutil
from pathlib import Path
import lib.common as com

base_input_dir = com.BASE_INPUT_DB_DIRECTORY
base_output_dir = com.BASE_OUTPUT_DB_DIRECTORY

msg = 'Usage: ' + sys.argv[0] + ' -newBlackList | -newWhiteList '

if len(sys.argv) < 2:
    com.log_error(msg)

del sys.argv[0]

if sys.argv[0] == '-newBlackList':
    sys.argv.remove('-newBlackList')
    
    if isinstance(sys.argv[0], str) and sys.argv[0][-4:] == '.dat':
        print('...',sys.argv[0],'---')
        a = sys.argv[0].strip()
        print('...{}---'.format(a))
        print(sys.argv[0].strip().split('/'))
        print(a.strip().split('/'))
        print(a)
        b = a.rfind('/')
        print(b)
        print(a[:b])
        if com.dir_exists(a[:b]):
            print('hola')
        quit()
        db_name = sys.argv[0]
        del sys.argv[0]
    else:
        com.log_error('Parater most has the *.dat extension')

    if len(sys.argv) >= 1:
        files_list = sys.argv
        blacklist_face_images = '/tmp/blacklist_faces'

        #removing directory
        try:
            shutil.rmtree(blacklist_face_images)
        except FileNotFoundError:
            com.log_debug("Directory does not exist - nothing to remove")

        #recreate directory
        os.makedirs(blacklist_face_images)

        #copy files to directory
        for item in files_list:
            item_splitted = item.split('/')
            shutil.copy2(item, blacklist_face_images+'/'+item_splitted[-1])
    else:
        blacklist_face_images = base_input_dir + '/blacklist_faces'
        com.create_data_dir(blacklist_face_images)

        blacklist_results_dir = base_input_dir + '/blacklist_db'
        com.create_data_dir(blacklist_results_dir)
        try:
            blacklist_data = blacklist_results_dir + '/' + com.BLACKLIST_DB_NAME
        except AttributeError:
            com.log_error("Configuration error - environment variable 'BLACKLIST_DB_NAME' not set")

    com.log_debug("Saving data in directory: {}".format(blacklist_results_dir))

    import lib.biblioteca as biblio 
    if sys.argv[1] == 'newBlackList':
        biblio.encode_known_faces_from_images_in_dir(blacklist_face_images, blacklist_data, 'blacklist')
    else:
        biblio.encode_known_faces_from_images_in_dir(blacklist_face_images, blacklist_data, 'blacklist', True)
elif sys.argv[1] == 'newWhiteList' or sys.argv[1] == 'addToWhiteList':
    if param_length > 1:
        if param_length > 2:
            files_list = sys.argv[2:]
            whitelist_face_images = '/tmp/whitelist_faces'

            #removing directory
            try:
                shutil.rmtree(whitelist_face_images)
            except FileNotFoundError:
                com.log_debug("Directory does not exist - nothing to remove")

            #recreate directory
            os.makedirs(whitelist_face_images)

            #copy files to directory
            for item in files_list:
                item_splitted = item.split('/')
                shutil.copy2(item, whitelist_face_images+'/'+item_splitted[-1])

        else:
            whitelist_face_images = base_input_dir + '/whitelist_faces'
            com.create_data_dir(whitelist_face_images)

        whitelist_results_dir = base_input_dir + '/whitelist_db'
        com.create_data_dir(whitelist_results_dir)

        try:
            whitelist_data = whitelist_results_dir + '/' + com.WHITELIST_DB_NAME
        except AttributeError:
            com.log_error("Configuration error - environment variable 'WHITELIST_DB_NAME' not set")
    else:
        com.log_error(msg)

    com.log_debug("Saving data in directory: {}".format(whitelist_results_dir))

    import lib.biblioteca as biblio 
    if sys.argv[1] == 'newWhiteList':
        biblio.encode_known_faces_from_images_in_dir(whitelist_face_images, whitelist_data, 'whitelist')
    else:
        biblio.encode_known_faces_from_images_in_dir(whitelist_face_images, whitelist_data, 'whitelist', True)
else:
    com.log_error(msg)
