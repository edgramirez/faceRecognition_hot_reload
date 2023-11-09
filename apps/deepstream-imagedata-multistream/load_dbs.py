#!/usr/bin/python3
import sys
import os
import shutil
from pathlib import Path
import lib.common as com
import lib.biblioteca as biblio
import lib.server as srv

base_input_dir   = com.BASE_INPUT_DB_DIRECTORY
whitelist_db_dir = com.WHITELIST_DB_BASE_DIR
blacklist_db_dir = com.BLACKLIST_DB_BASE_DIR


msg = 'Usage: \n\n' + sys.argv[0] + ' -new + -type [white|black] + -dbName "file_name" + [-srcDir "DIR_NAME_OF_THE_IMAGES" | -srcFiles "path_to_file1 path_to_file2 ..."]\n' + sys.argv[0] + ' -addTo + -dbName "file_name" + -srcFiles path_to_file1 path_to_file2 ...path_to_file3\n' + sys.argv[0] + ' -delFrom + -dbName "file_name" + -srcFiles path_to_file1 path_to_file2 ...path_to_file3\n' + sys.argv[0] + ' -update + -type [white|black] + -dbName "file_name"'


action_type = ''
list_type = ''
source_type = ''
db_directory = ''


def write_to_trigger_file(db_files_list):
    trigger_file = base_input_dir + '/db_to_update.txt'
    with open(trigger_file, mode='w') as f:
        for file_name in db_files_list:
            f.write(file_name + '\n')
            com.log_debug('Trigger file {}, was correctly created'.format(trigger_file))
            return True
    return False


min_length = 3
if len(sys.argv) < min_length:
    com.log_error(msg)

#removing file script name
del sys.argv[0]

if sys.argv[0] == '-new' or sys.argv[0] == '-update':
    if sys.argv[0] == '-new':
        action_type = 'new'
        min_length = 4
    else:
        action_type = 'update'
        min_length = 2

    del sys.argv[0]

    if sys.argv[0] != '-type':
        com.log_error(msg)
    else:
        del sys.argv[0]
        list_type = sys.argv[0]

    if list_type == 'white' or list_type == 'black':
        list_type = sys.argv[0]
        del sys.argv[0]
        if list_type == 'white':
            db_directory = whitelist_db_dir
        if list_type == 'black':
            db_directory = blacklist_db_dir
    else:
        com.log_error(msg)
elif sys.argv[0] == '-add':
    min_length = 4
    action_type = 'add'
elif sys.argv[0] == '-delFrom':
    min_length = 4
    action_type = 'remove'
else:
    com.log_error(msg)

if len(sys.argv) < min_length:
    com.log_error(msg)

if sys.argv[0] != '-dbName':
    com.log_error(msg)

del sys.argv[0]

if action_type == 'new' or action_type == 'update':
    # check if the db file already exist
    db_file_name = sys.argv[0]+'_'+list_type+'.dat'
    file_already_exists = False
    for item in os.listdir(db_directory):
        if db_file_name == item:
            file_already_exists = True
    if file_already_exists and action_type == 'new':
            com.log_error('File {}, already exists in this path {}'.format(db_file_name, db_directory+db_file_name))
    elif file_already_exists is False and action_type == 'update':
        com.log_error('File {}, does not exist in this path: {}'.format(db_file_name, db_directory+db_file_name))

if action_type == 'update':
    header = {
                'Accept': '*/*',
                'Content-type': 'application/json; charset=utf-8',
                'Connection': 'keep-alive',
                'Keep-alive': 'timeout=5'
                }
    scfg, client_name = srv.get_server_info(header)
    active_dbs = set()
    # get the active databases from the config file 
    for item in scfg:
        for item2 in scfg[item]['services']:
            for item3 in item2.keys():
                if 'blackList' in item2[item3]:
                    active_dbs.add(item2[item3]['blackList']['dbName'])
                if 'whiteList' in item2[item3]:
                    active_dbs.add(item2[item3]['whiteList']['dbName'])

    #This list will contain the databases name that are valid to update
    list_of_dbs = []
    for item in sys.argv:
        if whitelist_db_dir+item+'_'+list_type+'.dat' in active_dbs:
            if not com.file_exists(whitelist_db_dir+item+'_'+list_type+'.dat'):
                com.log_error('File {}, is defined in the configuration but does not exist'.format(whitelist_db_dir+item+'_'+list_type+'.dat'))
            list_of_dbs.append(whitelist_db_dir+item+'_'+list_type+'.dat')
        elif blacklist_db_dir+item+'_'+list_type+'.dat' in active_dbs:
            if not com.file_exists(blacklist_db_dir+item+'_'+list_type+'.dat'):
                com.log_error('File {}, is defined in the configuration but does not exist'.format(blacklist_db_dir+item+'_'+list_type+'.dat'))
            list_of_dbs.append(blacklist_db_dir+item+'_'+list_type+'.dat')
        else:
            com.log_error('Requested database {}, not defined in config file: config/Services_configuration.py'.format(item))

    #TODO:  escribir todos los nombre de los archivos en un archivo que disparara la actualizacion de esos mismo archivos
    if len(list_of_dbs) > 0 and write_to_trigger_file(list_of_dbs):
        com.log_debug('DBs will be updated soon')
    quit()

db_file_name = sys.argv[0]
del sys.argv[0]

#source can be a directory or a file (directory path is relative to the base directory ~/faceRecognition/input_data and files need to use full path)
if sys.argv[0] == '-srcDir' or sys.argv[0] == '-srcFiles':
    source_type = sys.argv[0]
    if sys.argv[0] == '-srcDir':
        if len(sys.argv) != 2:
            com.log_error(msg)
else:
    com.log_error(msg)

del sys.argv[0]

if source_type == '-srcDir':
    faces_dir = base_input_dir + '/' + sys.argv[0]
    files_count = 0
    if com.dir_exists(faces_dir):
        for item in os.listdir(faces_dir):
            if Path(faces_dir + '/' + item).is_file() is True:
                files_count = 1
                break
    else:
        com.log_error('Source directory: {} does not exist.'.format(faces_dir))

    if files_count == 0:
        com.log_warning("Directory: {} does not contain any file".format(faces_dir))
    else:
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
        com.log_debug('Saving -{}- numerical faces and metadatas in: {}'.format(result, db_file_full_path))
elif action_type == sys.argv[0] == '-srcFiles':
    sys.argv.remove('-srcFiles')


