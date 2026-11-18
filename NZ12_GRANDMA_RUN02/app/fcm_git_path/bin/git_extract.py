#! /usr/bin/env python

import argparse
import collections
import re
import os
import subprocess
import warnings
import configparser
from functools import cached_property


class GitPath(object):
    def __init__(self, path, clone_dir=None, root_path=None, verbosity=1):
        """
        Class describing the properties of an fcm_make path.

        Parameters
        ----------
        path : str
            An fcm_make path.
        clone_dir : str or None
            A path for local git clones.
        root_path : str or None
            A path to be prepended to relative path `path` types.
        verbosity : int
            Verbosity level.
                0 = No prints
                1 = Print the main actions
                2 =     + print the stdout from subprocess calls
                3 =     + print the stderr from subprocess calls
        """
        # Input arguments
        self.path = self._check_path(path, strict=True)
        self.root_path = self._check_path(root_path)
        self.clone_dir = self._check_path(clone_dir, resolve_path=True)
        self.verbosity = verbosity

        # Properties of the parsed path
        self._parsed, self.type = self._parse_path(self.path, self.root_path)
        self.url = self._parsed.url
        self.repository = self._parsed.repository
        self.commit_as_specified = self._parsed.commit

    def __str__(self):
        return self.local_path

    def __hash__(self):
        return hash(self.local_path)

    def _check_path(self, path, strict=False, resolve_path=False):
        """
        Format the path and check it is a string

        Parameters
        ----------
        path : str
            An fcm_make path.
        strict : bool
            If True, perform some checks on `path`.
        resolve_path : bool
            If True, expand environment variables and user "~"

        Returns
        -------
        path_out : str
            Reformatted `path`.
        """
        if isinstance(path, str):
            path = path.strip()
        if strict:
            if not isinstance(path, str):
                msg = f'path should be a string, not {type(path)}'
                raise TypeError(msg)
            if not path:
                msg = 'path is an empty string'
                raise ValueError(msg)
        if resolve_path and path:
            path = os.path.expanduser(os.path.expandvars(path))

        return path

    def _call(self, cmd, cwd=None):
        """
        Run a command via subprocess.Popen.

        Parameters
        ----------
        cmd : str
            The command to be run.
        cwd : str or None
            The current working directory to run from.

        Returns
        -------
        stdout : str
            The stdout from the command.
        stderr : str
            The stderr from the command.
        """
        if self.verbosity >= 1:
            print(f'\nRunning command "{cmd}"')

        stdout, stderr = sp_call(cmd, cwd=cwd)

        if self.verbosity >= 2:
            print('\tSTDOUT from command:\n\t\t{}'.format(stdout.replace('\n', '\n\t\t')))
        if self.verbosity >= 3:
            print('\tSTDERR from command:\n\t\t{}'.format(stderr.replace('\n', '\n\t\t')))

        return stdout, stderr

    @cached_property
    def _regex(self):
        """
        Return regular expression objects to match different path types.

        Returns
        -------
        regex : dict
            A dictionary of `re.Pattern` objects returned by `re.compile`.
        """
        re_dict = {'git': {'url': '(?P<url>(git@|http[s]?://)(?P<repository>.+).git)',      # Git URL
                           'branch': '(?P<branch>/[^@/]+)?',
                           'commit': '(?P<commit>@[0-9a-f]+)?'},
                   'svn': {'url': '(?P<url>(svn|fcm):.+)',                                  # SVN/FCM URL
                           'branch': '(?P<branch>/[^@]+)',
                           'commit': '(?P<commit>@[0-9]+)?'},
                   'localpath': {'url': '(?P<url>/[^><|:&*?@]+)$',                          # Absolute file path
                                 'branch': '',
                                 'commit': ''},
                   'relativepath': {'url': '(?P<url>[^/][^><|:&*?]+)',                      # Relative path
                                    'branch': '',
                                    'commit': ''}}
        regex = {k: re.compile('^{url}{branch}{commit}$'.format(**v)) for k, v in re_dict.items()}

        return regex

    @cached_property
    def commit(self):
        """
        Return the commit parsed from `path` (if any).
        If no commit was found in the parse and `path` is a git type,
        attempt to automatically determine the commit by running `git ls-remote`.
        """
        # Determine the git hash of the HEAD via "git ls-remote"
        if (self.type == 'git') and (self._parsed.commit is None):
            return self._commit()
        # Return the commit parsed from self.path
        else:
            return self.commit_as_specified

    @cached_property
    def short_commit(self):
        """
        Return the first 8 characters of the commit if `path` is a git type,
        otherwise just return the commit.
        """
        commit = self.commit
        if commit:
            if self.type == 'git':
                commit = commit[:8]

        return commit

    def _commit(self):
        """
        Run `git ls-remote` to determine the commit hash of `path`.
        """
        cmd = f'git ls-remote --exit-code {self.url} {self.branch} {self.branch}^{{}}'
        try:
            stdout, stderr = self._call(cmd)
        except:
            msg = f'No such remote url or branch:\n\tURL: {self.url}\n\tBranch: {self.branch}'
            raise ValueError(msg)

        # git tags have two commits: "tag" and "tag^{}". The former is for the tag itself, and the latter
        # is the actual "dereferenced" commit that the tag is a pointer to. We want this latter commit.
        tag_hash = re.search('([a-f0-9]+)\t(.+[/].*\^{})\n', stdout)
        commit_hash = re.search('([a-f0-9]+)\t(.*)\n', stdout)
        if tag_hash:                        # Matched "tag^{}"
            commit = tag_hash.group(1)
        elif commit_hash:
            commit = commit_hash.group(1)   # Matched "tag"
        else:
            msg = f'Could not parse a commit hash from output of "git ls-remote":\n\t{stdout}'
            raise ValueError(msg)

        return commit

    @cached_property
    def branch(self):
        """
        Return the branch parsed from `path` (if any).
        If no branch was found in the parse, return a default branch
        ("main"/"trunk" for git/svn `path` types).
        """
        branch = self._parsed.branch

        # Return a default branch
        if branch is None:
            if self.type == 'git':
                branch = 'main'
            elif self.type == 'svn':
                branch = 'trunk'

        return branch

    def _parse_path(self, path, root_path=None):
        """
        Match `path` against the regular expressions returned by `self._regex`.

        Parameters
        ----------
        path : str
            An fcm_make path.
        root_path : str or None
            A path to be prepended to relative path `path` types.

        Returns
        -------
        parsed : collections.namedtuple
            Named group results from the regular expression match.
        path_type : str
            The path type as determined by the regular expression match, one of:
                'git' = A git path
                'svn' = An svn path
                'localpath' = An absolute file path
                'relative' = A relative file, git or svn path
                'other' = An unknown path type (no regular expression matched)
        """
        # Each regex may have these named groups- 'url' is mandatory at the moment
        attrs = ['url', 'repository', 'branch', 'commit']
        match_dict = {i: None for i in attrs}
        nt = collections.namedtuple('parsed_path', attrs)

        # Loop over each regex type until one matches `path`
        for path_type, regex in self._regex.items():
            match = regex.match(path)

            if match:
                match_dict.update(match.groupdict())
                if match_dict['branch']:
                    match_dict['branch'] = match_dict['branch'].strip('/')
                if match_dict['commit']:
                    match_dict['commit'] = match_dict['commit'].strip('@')
                break
        else:
            path_type = 'other'
            match_dict['url'] = path

        # Return named group matches as a namedtuple
        parsed = nt(**match_dict)

        # If `path` is determined to be a relative path, this function
        # is rerun with `root_path` prepended to path
        if root_path and (path_type == 'relativepath'):
            path = f'{root_path}/{path}'
            parsed, path_type = self._parse_path(path)

        return parsed, path_type

    @cached_property
    def local_root(self):
        """
        If `path` is a git type, return the path root of its local clone.
        Otherwise, return None.
        """
        if self.type == 'git':
            path = self.repository.replace(':', '/')
            if self.clone_dir:
                path = f'{self.clone_dir}/{path}'
        else:
            path = None

        return path

    @cached_property
    def local_path(self):
        """
        If `path` is a git type, return the full path of its local clone.
        Otherwise, return `path`.
        """
        if self.type == 'git':
            path = f'{self.local_root}/{self.branch}/{self.short_commit}'
        else:
            path = self.path

        return path


class GitClone(GitPath):
    def __init__(self, path, clone_dir=None, root_path=None, verbosity=1):
        """
        Class describing the properties of an fcm_make path and, for git `path` types,
        methods to locally clone the path.

        Parameters
        ----------
        path : str
            An fcm_make path.
        clone_dir : str or None
            A path for local git clones.
        root_path : str or None
            A path to be prepended to relative path `path` types.
        verbosity : int
            Verbosity level.
                0 = No prints
                1 = Print the main actions
                2 =     + print the stdout from subprocess calls
                3 =     + print the stderr from subprocess calls
        """
        super(GitClone, self).__init__(path, clone_dir, root_path, verbosity)

    @property
    def is_cloned(self):
        """Check if there is already a local clone for `path`."""
        return self._check_local_dir()

    def _check_local_dir(self):
        """Check if there is already a local clone for `path`."""
        if self.type == 'git':
            return os.path.isdir(self.local_path)
        else:
            return False

    def clone(self):
        """
        Create a local clone of `path` by running `git clone`, if one does not exist.
        If `path` is not a git type, an error is raised.
        """
        if self.type != 'git':
            msg = f'"{self.path}" is not a git path- cannot clone'
            raise ValueError(msg)

        if self.verbosity >= 1:
            msg = f'Cloning "{self.url}" (branch "{self.branch}", commit "{self.short_commit}") into "{self.local_path}"'
            print(msg)

        # Perform the clone if it does not exist
        if not self.is_cloned:
            self._clone()

            if not self.is_cloned:
                msg = f'Path "{self.local_path}" does not exist- clone was unsuccessful'
                raise FileNotFoundError(msg)

            # If `path` contains a specific commit, also run `git checkout` to switch to this commit
            elif self.commit_as_specified:
                self._checkout()
        else:
            msg = f'Path "{self.local_path}" already exists- will not clone'
            warnings.warn(msg)

        # Check that we have the expected commit
        self._validate()

    def _clone(self):
        """Run `git clone` to clone the branch."""
        # Unless we want a specific commit, "--depth 1" is used so we don't fetch the full commit history
        depth = '' if self.commit_as_specified else '--depth 1'

        # We use --branch with --single-branch to checkout the branch instead of main
        cmd = f'git clone -q --branch {self.branch} --single-branch {depth} {self.url} {self.local_path}'

        stdout, stderr = self._call(cmd)

        return stdout, stderr

    def _checkout(self):
        """Run `git checkout` to switch to a specific commit."""
        cmd = f'git checkout {self.commit}'
        stdout, stderr = self._call(cmd, cwd=self.local_path)

        return stdout, stderr

    def _validate(self):
        """Run `git show-ref` to check that the clone is on the correct commit."""
        cmd = 'git show-ref --verify HEAD'
        stdout, stderr = self._call(cmd, cwd=self.local_path)
        commit = re.match('^[a-f0-9]+', stdout)

        if not commit:
            msg = f'Could not parse a commit hash from the output of "{cmd}":\n\t{stdout}'
            raise ValueError(msg)
        else:
            commit = commit.group()[:len(self.commit)]
            if commit != self.commit:
                msg = f'Commit hash:\n\t{commit}\ndoes not match the expected hash:\n\t{self.commit}'
                raise ValueError(msg)


def sp_call(cmd, cwd=None):
    """
    Run a command via subprocess.Popen.

    Parameters
    ----------
    cmd : str
        The command to be run.
    cwd : str or None
        The current working directory to run from.

    Returns
    -------
    stdout : str
        The stdout from the command.
    stderr : str
        The stderr from the command.
    """
    # universal_newlines is needed in python 3, otherwise stdout/stderr will be byte objects
    p = subprocess.Popen([i for i in cmd.split(' ') if i],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True, cwd=cwd)
    stdout, stderr = p.communicate()
    if p.returncode:
        raise ChildProcessError(stderr)

    return stdout, stderr


## Command line interface

def run_extract(args, cmd='print'):
    """
    Main command-line interface run script.

    Parameters
    ----------
    args : `argparse.Namespace`
        Object returned by `argparse.ArgumentParser.parse_args()`.
    cmd : str
        Command being run, one of:
            'print' = 'git_extract print' on the command line
            'rose-conf' = 'git_extract rose-conf' on the command line

    Returns
    -------
    new_paths : str or None
        All paths provided as input, with git paths replaced with paths to their local clones.
    """
    # "git_extract rose-conf": paths are provided as a Rose fcm_make app configuration file
    if cmd == 'rose-conf':
        if not os.path.isfile(args.conf):
            msg = f'File "{args.conf}" does not exist'
            raise FileNotFoundError(msg)

        # Use "rose config" to read the configuration file
        sp_cmd = f'rose config --default "" --file {args.conf} env {{}}'
        branch = sp_call(sp_cmd.format(args.branch))[0].rstrip('\n"')
        commit = sp_call(sp_cmd.format(args.revision))[0].rstrip('\n"')
        project = sp_call(sp_cmd.format(args.project))[0].rstrip('\n"')
        paths = sp_call(sp_cmd.format(args.sources))[0].rstrip('\n"')

        root_path = project if project else None
        paths = paths.split(' ') if paths else []

        # Convert project/branch/revision into a path for the root repository and add it to the sources.
        # Note that project is mandatory- its absence implies that there is no root repository.
        if root_path:
            path = '{url}{branch}{commit}'.format(url=root_path,
                                                  branch='/{}'.format(branch) if branch else '',
                                                  commit='@{}'.format(commit) if commit else '')
            root_clone = GitClone(path, args.clone_dir, None, args.verbosity - 1)
        else:
            root_clone = None

    # "git_extract print": paths are provided as command-line input
    else:
        root_path = args.root_path
        paths = args.paths
        root_clone = None

    # Create GitClone objects for each path, including the root if we are in "rose-conf" mode and
    # the root was specified via the "project" entry in the configuration file
    clones = [GitClone(i, args.clone_dir, root_path, args.verbosity - 1) for i in paths]
    if root_clone is not None:
        clones.insert(0, root_clone)

    # Categorise GitClone objects by type
    git = [i for i in clones if i.type == 'git']
    svn = [i for i in clones if i.type == 'svn']
    git_to_clone = [i for i in git if not i.is_cloned]
    other = [i for i in clones if i.type != 'git']
    clone_tag = '[TO BE CLONED]\t'
    noact_tag = '[PATH EXISTS] \t'

    # Print what will be done
    if args.verbosity >= 1:
        if git:
            msg = '\nThe following git URLs are mapped to local clones:'
            for i_clone, clone in enumerate(git, start=1):
                tag_str = clone_tag if clone in git_to_clone else noact_tag if git_to_clone else ''
                msg += f'\n\t{i_clone}. {clone.path} =>\n\t\t{tag_str}{clone}'
            print(msg)
        if other:
            msg = '\nThe following paths are not git URLs and require no action:'
            for i_clone, clone in enumerate(other, start=1):
                msg += f'\n\t{i_clone}. {clone}'
            print(msg)

    # Perform the git clones
    if args.clone:
        for clone in git_to_clone:
            clone.clone()

    # Get the converted paths (except for the root in "rose-conf" mode- this is handled separately)
    if clones:
        new_paths = ' '.join([str(i) for i in clones if i is not root_clone])
    else:
        new_paths = None

    # In "rose-conf" mode, we can output a Rose optional configuration file that
    # can be used to override the sources/project/branch/revision entries
    if cmd == 'rose-conf' and args.out_file:
        # Make the output directory
        out_dir = os.path.dirname(args.out_file)
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        # Make the configuration file
        with open(args.out_file, 'w') as fh:
            # [env] section
            conf = configparser.ConfigParser()
            conf.add_section('env')

            # "Sources" entry (if any)
            if new_paths:
                conf.set('env', args.sources, new_paths)

            # If the root repository is a git path, point instead to the local clone.
            # fcm make will interpret "project"/"branch"/"revision" as an absolute path to the clone.
            # This requires that fcm-make.cfg defines "extract.location[nemo] = ${branch}${revision}"
            if root_clone in git:
                conf.set('env', args.project, root_clone.local_root)
                conf.set('env', args.branch, root_clone.branch)
                conf.set('env', args.revision, '/{}'.format(root_clone.short_commit))

            # Because fcm-make.cfg requires "extract.location[nemo] = ${branch}${revision}",
            # we must insert the "@" for svn revisions
            elif root_clone in svn:
                if commit:
                    conf.set('env', args.revision, '@{}'.format(commit))

            conf.write(fh)
            fh.seek(0)

        if args.verbosity >= 1:
            with open(args.out_file) as fh:
                conf = fh.read().rstrip('\n')
                msg = f'\nContents of {args.out_file}:\n{"=" * 50}\n{conf}\n{"=" * 50}'
                print(msg)
        return None

    # In "print" mode or "rose-conf" mode without configuration file output, just print the converted paths
    else:
        return new_paths


def parse_args(args=None, namespace=None):
    parent_parser = argparse.ArgumentParser(add_help=False)
    parser = argparse.ArgumentParser(add_help=False)
    sp = parser.add_subparsers()

    parent_parser.add_argument('-c', '--clone', help='Clone git paths', action='store_true')
    parent_parser.add_argument('-l', '--clone_dir', help='Root directory for local git clones', type=str)
    parent_parser.add_argument('-v', '--verbosity', dest='verbosity', help='Verbosity level', action='count', default=0)

    parser_print = sp.add_parser('print', parents=[parent_parser],
                                 description='Convert git URLs to local clone paths and optionally perform ' + \
                                             'these clones, leaving non-git paths as specified. This mode ' + \
                                             '("print") accepts paths as command-line input, then prints the ' + \
                                             'converted paths to stdout.')
    parser_print.add_argument('paths', help='Repository paths', type=str, nargs='*')
    parser_print.add_argument('-r', '--root_path', help='Base path for relative paths in `paths`', type=str)
    parser_print.set_defaults(cmd='print')

    parser_conf = sp.add_parser('rose-conf', parents=[parent_parser],
                                description='Convert git URLs to local clone paths and optionally perform ' + \
                                            'these clones, leaving non-git paths as specified. This mode ' + \
                                            '("rose-conf") accepts paths as input from a Rose configuration ' + \
                                            'file for an fcm_make app, looking for entries describing a root ' + \
                                            'path (specified by the --project/--branch/--revision options, ' + \
                                            'such that the root path is constructed from the corresponding ' + \
                                            'values as {project}/{branch}@{revision}) and a list of additional ' + \
                                            'sources based on this root (specified as positional arguments). ' + \
                                            'A configuration file may be optionally output containing these ' + \
                                            'entries replaced by converted paths, which can be used as a Rose ' + \
                                            'optional configuration. Otherwise, the converted paths are ' + \
                                            'printed to stdout.')
    parser_conf.add_argument('conf', help='Rose fcm_make app configuration file to be read', type=str)
    parser_conf.add_argument('sources', help='`conf` entry containing repository paths', type=str)
    parser_conf.add_argument('-p', '--project', help='`conf` entry containing path to base repository',
                             type=str, default='nemo_project_location')
    parser_conf.add_argument('-b', '--branch', help='`conf` entry containing the name of the branch to use ' + \
                                                    'from the base repository',
                             type=str, default='nemo_base')
    parser_conf.add_argument('-r', '--revision', help='`conf` entry containing the revision/hash to use from ' + \
                                                      'the base repository',
                             type=str, default='nemo_rev')
    parser_conf.add_argument('-o', '--out_file', help='Name of the Rose configuration file to write converted ' + \
                                                      'paths into',
                             type=str)
    parser_conf.set_defaults(cmd='rose-conf')

    return parser.parse_args(args, namespace)


if __name__ == '__main__':
    args = parse_args()
    extract = run_extract(args, cmd=args.cmd)
    if extract:
        print(extract)
