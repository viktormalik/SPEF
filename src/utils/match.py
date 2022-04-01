
import re
import os
import glob
import traceback
import tarfile
import zipfile

from utils.logger import *
from utils.loading import *


############################ CHECK PATH ############################
# if path is not specified, check current working directory path (env.cwd.path)


# return True if path is a zipfile or a tarfile
def is_archive_file(path):
    if path is not None:
        if os.path.isfile(path):
            return zipfile.is_zipfile(path) or tarfile.is_tarfile(path)
    return False


# return True it path is root project directory (has proj conf file)
# ex: path = "subj1/2021/projA"           --> True
# ex: path = "subj1/2021/projA/xlogin00"  --> False
# ex: path = "subj1/2021"                 --> False
def is_root_project_dir(env, path=None):
    try:
        if path is None:
            path = env.cwd.path

        if os.path.isdir(path):
            file_list = os.listdir(path)
            if PROJECT_FILE in file_list:
                return True
        return False
    except:
        return False


# return True it path is some project subdirectory or file (parent has proj conf file)
# ex: path = "subj1/2021/projA/xlogin00/file1"  --> True
# ex: path = "subj1/2021/projA/xlogin00"        --> True
# ex: path = "subj1/2021/projA"                 --> True
# ex: path = "subj1/2021"                       --> False
def is_in_project_dir(env, path=None):
    try:
        if path is None:
            path = env.cwd.path

        cur_dir = path if os.path.isdir(path) else os.path.dirname(path)
        while True:
            parent_dir = os.path.dirname(cur_dir)
            if is_root_project_dir(env, cur_dir):
                return True
            else:
                if cur_dir == parent_dir:
                    return False
                else:
                    cur_dir = parent_dir
    except:
        return False


# pre-condition: check if is_in_project_dir(env, path)
# return True it path is root solution directory (path matches solution identifier)
# if path is not specified, check current working directory path
# ex: path = "subj1/2021/projA/xlogin00"        --> True
# ex: path = "subj1/2021/projA/xlogin00/file1"  --> False
# ex: path = "subj1/2021/projA"                 --> False
def is_root_solution_dir(env, solution_id, path=None):
    try:
        if path is None:
            path = env.cwd.path

        if os.path.isdir(path) and solution_id is not None:
            return match_regex(solution_id, path)
        return False
    except:
        return False


# pre-condition: check if is_in_project_dir(env, path)
# return True if path is file in project dir and matches solution id
def is_solution_file(env, solution_id, path=None):
    if path is not None:
        if os.path.isfile(path) and solution_id is not None:
            return match_regex(solution_id, path)
    return False


# pre-condition: check if is_in_project_dir(env, path)
# return True it path is some project solution subdirectory or file
# parent matches solution identifier
# if path is not specified, check current working directory path
def is_in_solution_dir(env, solution_id, path=None):
    try:
        if path is None:
            path = env.cwd.path

        cur_dir = path if os.path.isdir(path) else os.path.dirname(path)
        solution_dir_found = get_parent_regex_match(solution_id, path)
        return solution_dir_found is not None
    except:
        return False


# pre-condition: check if is_in_project_dir(env, path)
# return True if path is root tests dir (matches given tests dir)
# if path is not specified, check current working directory path
def is_root_tests_dir(env, tests_dir, path=None):
    try:
        if path is None:
            path = env.cwd.path

        if os.path.isdir(path) and tests_dir is not None:
            return match_regex(tests_dir, path)
        return False
    except:
        return False


# pre-condition: check if is_in_project_dir(env, path)
# return True if path is dir in root tests dir
# if path is not specified, check current working directory path
# with_check=True means it returns True only for valid testcase dirs (with 'dotest.sh' file in it)
def is_testcase_dir(env, tests_dir, path=None, with_check=True):
    try:
        if path is None:
            path = env.cwd.path

        if os.path.isdir(path) and tests_dir is not None:
            parent_dir = os.path.dirname(path)
            if is_root_tests_dir(env, tests_dir, parent_dir):
                if with_check:
                    file_list = os.listdir(path)
                    if TEST_FILE in file_list:
                        return True
                else:
                    return True
        return False    
    except:
        return False


########################## GET DIRS/FILES ##########################

# dst: regex for match
# src: dir path which is tested to regex
def match_regex(dst_regex, src_path):
    return bool(re.match(dst_regex, os.path.basename(src_path)))


# try match regex on dir parents
# returns parent dir name which matches regex or None
# ex: "x[a-z]{5}[0-9]{2}", "subj1/projA/xlogin00/test1/file" --> "subj1/projA/xlogin00"
def get_parent_regex_match(reg, dir_path):
    if dir_path is None:
        return None
    try:
        cur_dir = dir_path
        while True:
            parent_dir = os.path.dirname(cur_dir)
            if match_regex(reg, cur_dir):
                return cur_dir
            else:
                if cur_dir == parent_dir:
                    return None
                else:
                    cur_dir = parent_dir
    except Exception as err:
        log("get parent regex match | "+str(err)+" | "+str(traceback.format_exc()))


"""
proj_conf_file = get_proj_conf_path(env, path)
if proj_conf_file is not None:
    proj_data = load_proj_from_conf_file(cur_dir)

    # create Project obj from proj data
    proj = Project(proj_data['path'])
    proj.set_values_from_conf(proj_data)
"""

# return path to proj conf file if given path is in proj dir
def get_proj_conf_path(env, path):
    try:
        if path is None:
            path = env.cwd.path

        cur_dir = path if os.path.isdir(path) else os.path.dirname(path)
        while True:
            parent_dir = os.path.dirname(cur_dir)
            if is_root_project_dir(env, cur_dir):
                return cur_dir
            else:
                if cur_dir == parent_dir:
                    return None
                else:
                    cur_dir = parent_dir
    except:
        return None


# pre-condition: check if is_in_project_dir(env, path)
# return path to root solution dir if given path is in some solution dir
# ex: "x[a-z]{5}[0-9]{2}", "subj1/projA/xlogin00/test1/file" --> "subj1/projA/xlogin00"
def get_root_solution_dir(env, solution_id, path):
    return get_parent_regex_match(solution_id, path)


# return list of solution dirs in current project directory (cwd)
def get_solution_dirs(env):
    result = set()
    if env.cwd.proj is not None:
        solution_id = env.cwd.proj.solution_id
        for dir_name in env.cwd.dirs:
            if is_root_solution_dir(env, solution_id, dir_name):
                result.add(dir_name)
    else:
        log("get_solution_dirs | cwd is not project root directory")
    return list(result)


# return list of solution files in current project directory (cwd)
def get_solution_files(env):
    result = set()
    if env.cwd.proj is not None:
        solution_id = env.cwd.proj.solution_id
        for file_name in env.cwd.files:
            if is_solution_file(env, solution_id, file_name):
                result.add(file_name)
    else:
        log("get_solution_files | cwd is not project root directory")
    return list(result)


# return list of solution archive dirs in current directory (cwd) if its project directory
def get_solution_archives(env):
    solution_archives = set() # zipfile or tarfile
    solution_files = set() # other solution matched file
    for file_name in get_solution_files(env):
        if is_archive_file(file_name):
            solution_archives.add(file_name)
        else:
            log("solution file but not zipfile or tarfile: "+str(file_name))
            solution_files.add(file_name)
    return list(solution_archives), list(solution_files)


# return list of test dirs (dirs from project_dir/tests_dir/*)
# with_check=True means it returns only valid test dirs (with 'dotest.sh' file in it)
def get_test_dirs(with_check=True):
    pass

