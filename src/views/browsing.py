
import curses
import curses.ascii
import os
import traceback
import tarfile
import zipfile

from controls.control import *
from controls.functions import brows_menu_functions

from views.filtering import filter_management
from views.help import show_help
from views.menu import brows_menu

from modules.directory import Directory, Project

from utils.loading import *
from utils.screens import *
from utils.printing import *
from utils.logger import *
from utils.reporting import *
from utils.match import *


def get_directory_content(env):
    if env.filter_not_empty():
        cwd = Directory(env.filter.project, files=env.filter.files)
        cwd.proj_conf_path = env.filter.project
        return cwd

    path = os.getcwd() # current working directory path
    files, dirs = [], []
    for dir_path, dir_names, file_names in os.walk(path):
        if env.show_cached_files:
            files.extend(file_names)
        else:
            for file_name in file_names:
                if not file_name.endswith((REPORT_SUFFIX,TAGS_SUFFIX)):
                    files.append(file_name)
        dirs.extend(dir_names)
        break
    dirs.sort()
    files.sort()
    cwd = Directory(path, dirs, files)
    cwd.get_proj_conf()
    return cwd



def directory_browsing(stdscr, env):
    curses.curs_set(0)
    screen, win = env.get_screen_for_current_mode()

    env.cwd = get_directory_content(env)

    while True:
        screen, win = env.get_screen_for_current_mode()

        """ try to load buffer and tag for current file in directory structure """
        idx = win.cursor.row
        if env.quick_view and idx < len(env.cwd):
            dirs_and_files = env.cwd.get_all_items()
            # if its file, show its content and tags
            if idx >= len(env.cwd.dirs):
                selected_file = os.path.join(env.cwd.path, dirs_and_files[idx])
                # if its archive file, show its content (TODO)
                if is_archive_file(selected_file):
                    pass
                else:
                    env.set_file_to_open(selected_file)
                    env, buffer, succ = load_buffer_and_tags(env) # try to load file
                    if not succ: # couldnt load buffer and/or fags for current file
                        env.set_file_to_open(None)
                        env.set_brows_mode() # contnue to browsing without showing file content (instead of exit mode)
                    else:
                        """ set line numbers """
                        if env.line_numbers or env.start_with_line_numbers:
                            env.start_with_line_numbers = False
                            env.enable_line_numbers(buffer)
                            env = resize_all(stdscr, env, True)
            # if its project directory, show project info and test results
            else:
                if env.cwd.proj is not None: # current working directory is a project subdirectory (ex: "proj1/")
                    # env.cwd.proj
                    selected_dir = dirs_and_files[idx]
                    # if proj.match_solution_id(selected_dir): # selected item is solution directory (ex: "proj1/xlogin00/")
                        # if proj.quick_view_file in selected_dir.files():
                        #    show_file_and_tags(proj.quick_view_file)
                    # elif proj.is_solution_subdirectory(selected_dir): # selected item is inside some solution subdirectory (ex: "proj1/xlogin00/dir/")
                        # if proj.is_test_directory(selected_dir): # is test directory == 
                        #    tests_conf = load_tests_from_conf_file(selected_dir)
                        #    show_file()
                        #    show_test_tags()

                pass # TODO: show project info and test tags
            env.update_win_for_current_mode(win)


        """ print all screens """
        rewrite_all_wins(env)


        key = stdscr.getch()

        try:
            function = get_function_for_key(env, key)
            if function is not None:
                env, exit_program = run_function(stdscr, env, function, key)
                if exit_program:
                    return env

        except Exception as err:
            log("browsing with quick view | "+str(err)+" | "+str(traceback.format_exc()))
            env.set_exit_mode()
            return env



""" implementation of functions for directory browsing """
def run_function(stdscr, env, fce, key):
    screen, win = env.get_screen_for_current_mode()

    # ======================= EXIT =======================
    if fce == EXIT_PROGRAM:
        env.set_exit_mode()
        return env, True
    # ======================= FOCUS =======================
    elif fce == CHANGE_FOCUS:
        env.switch_to_next_mode()
        return env, True
    # ======================= RESIZE =======================
    elif fce == RESIZE_WIN:
        env = resize_all(stdscr, env)
        screen, win = env.get_screen_for_current_mode()
    # ======================= ARROWS =======================
    elif fce == CURSOR_UP:
        win.up(env.cwd, use_restrictions=False)
    elif fce == CURSOR_DOWN:
        win.down(env.cwd, filter_on=env.path_filter_on(), use_restrictions=False)
    elif fce == CURSOR_RIGHT:
        idx = win.cursor.row
        if not env.filter_not_empty() and idx < len(env.cwd.dirs):
            """ go to subdirectory """
            os.chdir(os.path.join(env.cwd.path, env.cwd.dirs[idx]))
            env.cwd = get_directory_content(env)
            win.reset(0,0) # set cursor on first position (first item)
    elif fce == CURSOR_LEFT:
        current_dir = os.path.basename(env.cwd.path) # get directory name
        if not env.filter_not_empty() and current_dir: # if its not root
            """ go to parent directory """
            os.chdir('..')
            env.cwd = get_directory_content(env)
            win.reset(0,0)
            """ set cursor position to prev directory """
            dir_position = env.cwd.dirs.index(current_dir) # find position of prev directory
            if dir_position:
                for i in range(0, dir_position):
                    win.down(env.cwd, filter_on=env.path_filter_on(), use_restrictions=False)
    # ======================= SHOW HELP =======================
    elif fce == SHOW_HELP:
        env = show_help(stdscr, env)
        screen, win = env.get_screen_for_current_mode()
        curses.curs_set(0)
    # ======================= OPEN MENU =======================
    elif fce == OPEN_MENU:
        menu_functions = brows_menu_functions()
        title = "Select function from menu: "
        color = curses.color_pair(COL_TITLE)
        menu_options = [key for key in menu_functions]
        env, option_idx = brows_menu(stdscr, env, menu_options, color=color, title=title)
        if env.is_exit_mode():
            return env, True
        screen, win = env.get_screen_for_current_mode()
        curses.curs_set(0)
        if option_idx is not None:
            for i, key in enumerate(menu_functions):
                if i == option_idx:
                    rewrite_all_wins(env)
                    function = menu_functions[key]
                    env, exit_program = run_menu_function(stdscr, env, function, key)
                    if exit_program:
                        return env, True
    # ======================= QUICK VIEW =======================
    elif fce == QUICK_VIEW_ON_OFF:
        env.quick_view = not env.quick_view
    # ======================= OPEN FILE =======================
    elif fce == OPEN_FILE:
        idx = win.cursor.row
        if idx >= len(env.cwd.dirs) or env.filter: # cant open directory
            dirs_and_files = env.cwd.get_all_items()
            env.set_file_to_open(os.path.join(env.cwd.path, dirs_and_files[idx]))
            env.switch_to_next_mode()
            return env, True
    # ======================= DELETE FILE =======================
    elif fce == DELETE_FILE:
        idx = win.cursor.row
        dirs_and_files = env.cwd.get_all_items()
        file_to_delete = os.path.join(env.cwd.path, dirs_and_files[idx])
        if os.path.exists(file_to_delete) and os.path.isfile(file_to_delete):
            os.remove(file_to_delete)
            win.up(env.cwd, use_restrictions=False)
            # actualize current working directory
            env.cwd = get_directory_content(env)
    # ======================= FILTER =======================
    elif fce == FILTER:
        env = filter_management(stdscr, screen, win, env)
        if env.is_exit_mode():
            return env, True
        screen, win = env.get_screen_for_current_mode()
        # actualize current working directory
        env.cwd = get_directory_content(env)
        win.reset(0,0)
        curses.curs_set(0)

    env.update_win_for_current_mode(win)
    return env, False



def run_menu_function(stdscr, env, fce, key):
    screen, win = env.get_screen_for_current_mode()

    # ======================= ADD PROJECT =======================
    if fce == ADD_PROJECT:
        if env.cwd.proj is not None:
            return env, False
        # create project object
        proj = Project(env.cwd.path)
        proj.set_default_values()
        # create project config file
        proj_data = proj.to_dict()
        save_proj_to_conf_file(proj.path, proj_data)
        # actualize current working directory
        env.cwd = get_directory_content(env)
    elif fce == EXPAND_HERE:
        pass
    elif fce == EXPAND_TO:
        pass
    elif fce == CREATE_DIR:
        pass
    elif fce == CREATE_FILE:
        pass
    elif fce == REMOVE_FILE:
        pass
    elif fce == RENAME_FILE:
        pass
    elif fce == COPY_FILE:
        pass
    elif fce == MOVE_FILE:
        pass
    # ====================== EDIT PROJ CONFIG ======================
    elif fce == EDIT_PROJ_CONF:
        if env.cwd.proj is not None:
            env.set_file_to_open(os.path.join(env.cwd.proj.path, PROJECT_FILE))
            env.switch_to_next_mode()
            return env, True
        pass
    # ====================== EXPAND AND RENAME ======================
    elif fce == EXPAND_ALL_SOLUTIONS: # ALL STUDENTS
        if env.cwd.proj is not None:
            solutions, problem_files = get_solution_archives(env)
            problem_solutions = set(problem_files)
            for solution in solutions:
                opener, mode = None, None
                if solution.endswith('.zip'):
                    dest_dir = solution.removesuffix('.zip')
                    opener, mode = zipfile.ZipFile, 'r'
                elif solution.endswith('.tar'):
                    dest_dir = solution.removesuffix('.tar')
                    opener, mode = tarfile.open, 'r'
                elif solution.endswith('.tar.gz') or solution.endswith('.tgz'):
                    dest_dir = solution.removesuffix('.tar.gz').removesuffix('.tgz')
                    opener, mode = tarfile.open, 'r:gz'
                elif solution.endswith('.tar.bz2') or solution.endswith('.tbz'):
                    dest_dir = solution.removesuffix('.tar.bz2').removesuffix('.tbz')
                    opener, mode = tarfile.open, 'r:bz2'
                elif solution.endswith('.tar.xz') or solution.endswith('.txz'):
                    dest_dir = solution.removesuffix('.tar.xz').removesuffix('.txz')
                    opener, mode = tarfile.open, 'r:xz'
                else:
                    problem_solutions.append(solution)

                try:
                    if opener and mode:
                        with opener(solution, mode) as arch_file:
                            if not os.path.exists(dest_dir):
                                os.mkdir(dest_dir)
                            arch_file.extractall(dest_dir)
                except Exception as err:
                    log("expand solution archive | "+str(err)+" | "+str(traceback.format_exc()))

            log("problem archives: "+str(problem_solutions))
            env.cwd = get_directory_content(env)

    elif fce == RENAME_ALL_SOLUTIONS: # ALL STUDENTS
        if env.cwd.proj is not None:
            pass
            # if proj.solution_is_dir():
            #    solutions = get_solution_dirs(env)
            # elif proj.solution_is_file():
            #    solutions = get_solution_files(env)


    elif fce == EXPAND_AND_RENAME_SOLUTION: # on solution dir
        # if is_project_dir:
        # if is_solution_dir:
        # if is_archive:
        # try unzip (podla typu .zip, .tar)
        # if proj.solution_file_name and proj.extended_solution_file_name:
        # for file in solution_dir:
        # try
        pass
    # ======================= RUN TEST SET =======================
    elif fce == TEST_ALL_STUDENTS: # ALL STUDENTS
        pass
    elif fce == TEST_STUDENT: # on solution dir
        pass
    elif fce == TEST_CLEAN: # on solution dir
        pass
    # =================== GENERATE REPORT ===================
    # elif fce == GEN_AUTO_REPORT: # on solution dir
        # pass
    elif fce == GEN_CODE_REVIEW: # on solution dir
        idx = win.cursor.row
        dirs_and_files = env.cwd.get_all_items()
        generate_code_review(env, os.path.join(env.cwd.path, dirs_and_files[idx]))
    # ======================= SHOW INFO =======================
    elif fce == SHOW_OR_HIDE_PROJ_INFO:
        pass
    elif fce == SHOW_STATS:
        pass
    elif fce == SHOW_HISTOGRAM:
        pass
    elif fce == SHOW_TEST_RESULTS: # on solution dir
        pass
    elif fce == SHOW_AUTO_REPORT:
        pass
    elif fce == SHOW_CODE_REVIEW:
        pass
    elif fce == SHOW_TOTAL_REPORT:
        pass
    # =================== TESTS ===================
    elif fce == ADD_TEST:
        pass
    elif fce == EDIT_TEST:
        pass
    elif fce == REMOVE_TEST:
        pass
    elif fce == EDIT_TESTSUITE:
        pass
    elif fce == DEFINE_TEST_FAILURE:
        pass

    env.update_win_for_current_mode(win)
    return env, False