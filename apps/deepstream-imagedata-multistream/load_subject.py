#!/usr/bin/python3
import sys
import os
import shutil
from pathlib import Path
import lib.common as com
import lib.biblioteca as biblio

base_input_dir = com.BASE_INPUT_DB_DIRECTORY
whitelist_db_dir = com.WHITELIST_DB_BASE_DIR
blacklist_db_dir = com.BLACKLIST_DB_BASE_DIR


msg = 'Usage: ' + sys.argv[0] + ' [-newBlackList | -newWhiteList] + -dbName "file_name.dat" -srcDir "DIR_NAME_OF_THE_IMAGES"'

if len(sys.argv) < 5:
    com.log_error(msg)

del sys.argv[0]

if sys.argv[0] == '-newBlackList':
    list_type = 'blacklist'
    db_directory = blacklist_db_dir
    sys.argv.remove('-newBlackList')
elif sys.argv[0] == '-newWhiteList':
    list_type = 'whitelist'
    db_directory = whitelist_db_dir
    sys.argv.remove('-newWhiteList')
else:
    com.log_error(msg)

if True:
    if sys.argv[0] != '-dbName':
        com.log_error(msg)
    sys.argv.remove('-dbName')
        
    if sys.argv[0][-4:] != '.dat':
        com.log_error(msg)
    db_file_name = sys.argv[0]
    del sys.argv[0]

    if sys.argv[0] != '-srcDir':
        com.log_error(msg)
    sys.argv.remove('-srcDir')

    faces_dir = base_input_dir + '/' + sys.argv[0]
    files_count = 0
    if com.dir_exists(faces_dir):
        for item in os.listdir(faces_dir):
            if Path(faces_dir + '/' + item).is_file() is True:
                files_count = 1
                break
    else:
        com.log_error('Source directory: {} does not exist.'.format(faces_dir))

    if files_count > 0:
        #if base db directory does not exist, create it
        if not com.dir_exists(db_directory):
            #create directory
            com.log_debug("Creating directory: {}".format(db_directory))
            os.makedirs(db_directory)
            if not com.dir_exists(db_directory):
                com.log_error('Unable to create directory: {}'.format(db_directory))

        #removing the previous database
        db_file_full_path = db_directory + db_file_name
        try:
            com.log_debug("Removing file: {}".format(db_file_full_path))
            os.remove(db_file_full_path)
        except FileNotFoundError:
            com.log_debug("File {} does not exist - nothing to remove".format(db_file_full_path))

        # validating previous db was deleted
        if com.file_exists(db_file_full_path):
            com.log_error('Unable to remove file: {}'.format(db_file_full_path))
            
        # reading files and making their numerical representation
        result = biblio.encode_known_faces_from_images_in_dir(faces_dir, db_file_full_path, list_type)

        if result == 0:
            com.log_error('Unable to create any numerical face representation from the files in: {}'.format(faces_dir))
        com.log_debug('Saving numerical -{}- faces and metadata in: {}'.format(result, db_file_full_path))
        
    else:
        com.log_warning("Directory: {} does not any contain files".format(faces_dir))

