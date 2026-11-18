import os
import subprocess
import configparser
import warnings
import pytest
import tempfile
import shutil
import itertools
from git_extract import run_extract, GitPath, GitClone, parse_args
from unittest import mock


def use_fixture(**kwargs):
    """
    Replacement for pytest.mark.parameterize that allows for single-length arguments.
    Paired with the pytest_generate_tests function, this also allows the single-length
    arguments to be omitted from the test name (which is a bit tidier).

    Keywords:
        kwargs-
            Arguments and values to the fixture function in keyword format,
            i.e. use_fixture(arg1=[val1a, val1b], arg2=val, ...)

    Returns:
        A wrapper function.
    """
    def patch(func):
        setattr(func, '_fixtures', kwargs)
        return func

    return patch


# Fast tests (<1s, external commands are mocked)
@pytest.mark.fast
class TestGitPath(object):
    """"""
    @use_fixture(calling_test='attrs', url_type=['ssh', 'https'], commit=['no_commit', 'commit'],
                 branch=['no_branch', 'branch'], path_type=['absolute', 'relative'], clone_dir=['no_root', 'root'])
    def test_git_attrs(self, git_fixture):
        """"""
        with git_patch():
            expected, test = git_fixture
            for attr, exp in expected.items():
                if attr == 'str':
                    assert str(test) == exp, 'str() has unexpected value'
                else:
                    assert getattr(test, attr) == exp, f'Attribute "{attr}" has unexpected value'

    @use_fixture(calling_test='attrs', commit=['no_commit', 'commit'], path_type=['absolute', 'relative'],
                 branch='no_branch')
    def test_svn_attrs(self, svn_fixture):
        """"""
        expected, test = svn_fixture
        for attr, exp in expected.items():
            if attr == 'str':
                assert str(test) == exp, 'str() has unexpected value'
            else:
                assert getattr(test, attr) == exp, f'Attribute "{attr}" has unexpected value'

    @use_fixture(calling_test='attrs', path_type=['absolute', 'relative'])
    def test_file_attrs(self, filepath_fixture):
        """"""
        expected, test = filepath_fixture
        for attr, exp in expected.items():
            if attr == 'str':
                assert str(test) == exp, 'str() has unexpected value'
            else:
                assert getattr(test, attr) == exp, f'Attribute "{attr}" has unexpected value'

    @use_fixture(calling_test='attrs', url_type=['rhost', 'rhost_user'])
    def test_other_attrs(self, otherpath_fixture):
        """"""
        expected, test = otherpath_fixture
        for attr, exp in expected.items():
            if attr == 'str':
                assert str(test) == exp, 'str() has unexpected value'
            else:
                assert getattr(test, attr) == exp, f'Attribute "{attr}" has unexpected value'


@pytest.mark.fast
class TestGitClone(object):
    """"""
    @use_fixture(calling_test='clone', url_type=['ssh', 'https'], commit=['no_commit', 'commit'],
                 branch=['no_branch', 'branch'], path_type='absolute', clone_dir=['no_root', 'root'])
    def test_clone(self, git_fixture):
        """"""
        with git_patch():
            expected, test = git_fixture
            stdout, stderr = test._clone()
            assert stdout == expected['stdout']
            assert stderr == ''

    @use_fixture(calling_test='checkout', url_type=['ssh', 'https'], commit=['no_commit', 'commit'],
                 branch=['no_branch', 'branch'], path_type='absolute', clone_dir=['no_root', 'root'])
    def test_checkout(self, git_fixture):
        """"""
        with git_patch():
            expected, test = git_fixture
            stdout, stderr = test._checkout()
            assert stdout == expected['stdout']
            assert stderr == ''

    @use_fixture(calling_test='clone', commit='no_commit', branch='no_branch', path_type='absolute')
    def test_FAIL_svn_path(self, svn_fixture):
        """"""
        expected, test = svn_fixture
        with pytest.raises(ValueError, match='not a git path'), git_patch():
            test.clone()

    @use_fixture(calling_test='clone', path_type='absolute')
    def test_FAIL_file_path(self, filepath_fixture):
        """"""
        expected, test = filepath_fixture
        with pytest.raises(ValueError, match='not a git path'), git_patch():
            test.clone()

    @use_fixture(calling_test='clone', url_type='rhost')
    def test_FAIL_other_path(self, otherpath_fixture):
        """"""
        expected, test = otherpath_fixture
        with pytest.raises(ValueError, match='not a git path'), git_patch():
            test.clone()


# Slow tests (~1s-5m, external commands are run)
@pytest.mark.slow
class TestGitRunExtract(object):
    """"""
    @use_fixture(calling_test='print', url_type=['ssh', 'https'], commit=['no_commit', 'commit'],
                 branch=['no_branch', 'branch'], path_type=['absolute', 'relative'], clone_dir=['no_root', 'root'])
    def test_extract_git_base(self, git_fixture):
        """"""
        expected, fixture = git_fixture

        with git_patch():
            test = run_extract(fixture)

        assert test == expected

    @use_fixture(calling_test='print', commit=['no_commit', 'commit'], path_type=['absolute', 'relative'],
                 branch=['no_branch', 'branch'])
    def test_extract_svn_base(self, svn_fixture):
        """"""
        expected, fixture = svn_fixture

        with git_patch():
            test = run_extract(fixture)

        assert test == expected

    @use_fixture(calling_test='rose-conf', url_type=['ssh', 'https'], commit=['no_commit', 'commit'],
                 branch=['no_branch', 'branch'], path_type=['absolute', 'relative'], clone_dir=['no_root', 'root'])
    def test_extract_file_git_base(self, git_fixture):
        """"""
        fname_result, fname_exp, fixture = git_fixture

        with git_patch():
            run_extract(fixture, cmd='rose-conf')

        with open(fname_result) as fh:
            test = fh.read()
        with open(fname_exp) as fh:
            expected = fh.read()

        assert test == expected

    @use_fixture(calling_test='rose-conf', commit=['no_commit', 'commit'], path_type=['absolute', 'relative'],
                 branch=['no_branch', 'branch'])
    def test_extract_file_svn_base(self, svn_fixture):
        """"""
        fname_result, fname_exp, fixture = svn_fixture

        with git_patch():
            run_extract(fixture, cmd='rose-conf')

        with open(fname_result) as fh:
            test = fh.read()
        with open(fname_exp) as fh:
            expected = fh.read()

        assert test == expected


@pytest.mark.slow
class TestGitSlow(object):
    """"""
    def teardown_method(self):
        """"""
        clone_dir = os.path.expanduser(os.path.expandvars('/scratch/$USER/test_git_extract'))
        if os.path.isdir(clone_dir):
            shutil.rmtree(clone_dir)
            print(f'Removed "{clone_dir}"')

    @use_fixture(calling_test='clone', url_type=['ssh', 'https'], commit='commit',
                 branch=['no_branch', 'real_branch'], path_type='absolute', clone_dir='real_root')
    def test_clone(self, git_fixture):
        """"""
        expected, test = git_fixture

        test.clone()
        with pytest.warns(UserWarning, match='already exists- will not clone'):
            test.clone()

    @use_fixture(calling_test='clone', url_type='ssh', commit='no_commit',
                 branch='bad', path_type=['absolute', 'relative'], clone_dir='real_root')
    def test_clone_FAIL_invalid_git_path(self, git_fixture):
        """"""
        expected, test = git_fixture
        with pytest.raises(ValueError, match='No such remote'):
            test.clone()


# Test fixtures
@pytest.fixture
def git_fixture(url_type, clone_dir, path_type, branch, commit, calling_test):
    """"""
    default_branch = 'main'
    default_commit = {'no_branch': '38d6856256fa965ad93fdf3ee241d2dd2431575f',
                      'branch': '5cf0c3d61b751a102fe9de9c8ffe61a7216946cc',
                      'real_branch': '87b2c6a483f59118bfa4358f78aaa71ff6b3c872',
                      'bad': ''}[branch]
    url = {'ssh': 'git@forge.nemo-ocean.eu:nemo/nemo.git',
           'https': 'https://forge.nemo-ocean.eu/nemo/nemo.git'}[url_type]
    clone_dir = {'no_root': None,
                 'root': os.path.expanduser(os.path.expandvars('$LOCALTEMP')),
                 'real_root': '/scratch/$USER/test_git_extract'}[clone_dir]
    root_path = {'absolute': None,
                 'relative': url}[path_type]
    commit = {'no_commit': None,
              'commit': default_commit[:6]}[commit]
    branch = {'no_branch': None,
              'branch': 'branch',
              'real_branch': '4.2.0',
              'bad': 'NULL'}[branch]

    # Format of local clone path
    if clone_dir:
        local_dir_fmt = '{clone_dir}/forge.nemo-ocean.eu/nemo/nemo/{branch}/{short_commit}'
    else:
        local_dir_fmt = 'forge.nemo-ocean.eu/nemo/nemo/{branch}/{short_commit}'

    # Fixtures for GitPath and GitClone classes
    if calling_test in ('attrs', 'clone', 'checkout'):
        repos = {'ssh': 'forge.nemo-ocean.eu:nemo/nemo',
                 'https': 'forge.nemo-ocean.eu/nemo/nemo'}[url_type]

        # Test relative paths if a root_path is specified, otherwise test absolute paths
        if root_path:
            path_fmt = '{branch}{commit}'
            path = path_fmt.format(branch=branch if branch else default_branch,
                                   commit='@{}'.format(commit) if commit else '')
        else:
            path_fmt = '{url}{branch}{commit}'
            path = path_fmt.format(url=url,
                                   branch='/{}'.format(branch) if branch else '',
                                   commit='@{}'.format(commit) if commit else '')
        local_dir = local_dir_fmt.format(clone_dir=clone_dir,
                                         branch=branch if branch else default_branch,
                                         short_commit=commit if commit else default_commit[:8])

        # Expected class attributes
        expected = {'url': url,
                    'repository': repos,
                    'type': 'git',
                    'branch': branch if branch else default_branch,
                    'commit_as_specified': commit,
                    'commit': commit if commit else default_commit,
                    'short_commit': (commit if commit else default_commit)[:8],
                    'path': path,
                    'str': local_dir}

        if calling_test == 'attrs':
            print(f'\nFixture: GitPath({path}, {clone_dir}, {root_path})')
            fixture = GitPath(path, clone_dir, root_path)

        else:
            # Expected stdout from mocked git commands
            cmd = {'clone': 'git clone -q --branch {branch} --single-branch {depth}{url} {dir}',
                   'checkout': 'git checkout {commit}'}[calling_test]
            expected['stdout'] = cmd.format(branch=expected['branch'],
                                            commit=expected['commit'],
                                            depth='' if commit else '--depth 1 ',
                                            url=expected['url'],
                                            dir=expected['str'])

            print(f'\nFixture: GitClone({path}, {clone_dir}, {root_path})')
            fixture = GitClone(path, clone_dir, root_path)

        yield expected, fixture

    # Fixtures for command line interface
    elif calling_test in ('print', 'rose-conf'):
        # Input paths
        sources = ['/path/to/working_copy',
                   'relative/path/somewhere',
                   '4.2.0',
                   '4.2.0@5cf0c3',
                   'git@forge.nemo-ocean.eu:nemo/nemo.git',
                   'git@forge.nemo-ocean.eu:nemo/nemo.git/main',
                   'fcm:nemo.xm/NEMO/branches/UKMO',
                   'fcm:nemo.xm/NEMO/branches/UKMO/branches/NEMO_4.0.1_GO8_package_fix']

        # Absolute git paths resolve to local clones
        expected = {'sources': sources[:]}
        expected['sources'][4] = local_dir_fmt.format(clone_dir=clone_dir, branch='main', short_commit='38d68562')
        expected['sources'][5] = expected['sources'][4]

        # Relative git paths and project/branch/revision point to local clones only if
        # project was specified, otherwise these are not altered
        if root_path:
            # Relative source paths become absolute paths
            expected['sources'][2] = local_dir_fmt.format(clone_dir=clone_dir, branch='4.2.0', short_commit='5cf0c3d6')
            expected['sources'][3] = local_dir_fmt.format(clone_dir=clone_dir, branch='4.2.0', short_commit='5cf0c3')
            if calling_test == 'rose-conf':
                # Local clone is split into project/branch/revision as {forge.nemo-ocean.eu/nemo/nemo}/{main}/{38d685}
                # branch/revision are determined automatically if not specified
                expected['project'] = local_dir_fmt.format(clone_dir=clone_dir, branch='', short_commit='').rstrip('/')
                expected['branch'] = branch if branch else default_branch
                expected['revision'] = commit if commit else default_commit[:8]

        if calling_test == 'print':
            # Fixture is the result of parsing the command line arguments
            args = ['print'] + sources + ['-v']
            if clone_dir:
                args += ['-l', clone_dir]
            if root_path:
                args += ['-r', root_path]
            expected = ' '.join(expected['sources'])
            fixture = parse_args(args)

            yield expected, fixture

        else:
            # Create temporary working directory
            tmp_dir = tempfile.mkdtemp()
            print(f'Created "{tmp_dir}"')

            # Create configuration files
            fname_result = f'{tmp_dir}/result.conf'
            fname_in = test_conf(tmp_dir, 'in', sources, root_path, branch, commit)
            fname_exp = test_conf(tmp_dir, 'expected', **expected)

            # Fixture is the result of parsing the command line arguments
            args = ['rose-conf', fname_in, 'nemo_sources', '-v', '-o', fname_result]
            if clone_dir:
                args += ['-l', clone_dir]
            fixture = parse_args(args)

            yield fname_result, fname_exp, fixture

            # Clean up temporary working directory
            shutil.rmtree(tmp_dir)
            print(f'Removed "{tmp_dir}"')

    else:
        msg = f'No fixture implemented for calling_test="{calling_test}"'
        raise ValueError(msg)


@pytest.fixture
def svn_fixture(path_type, branch, commit, calling_test):
    """"""
    url = 'fcm:nemo.xm/NEMO/branches/UKMO'
    root_path = {'absolute': None,
                 'relative': url}[path_type]
    commit = {'no_commit': None,
              'commit': '12345'}[commit]

    if calling_test in ('attrs', 'clone', 'checkout'):
        if root_path:
            path_fmt = '{branch}{commit}'
            path = path_fmt.format(branch='trunk',
                                   commit='@{}'.format(commit) if commit else '')
        else:
            path_fmt = '{url}{branch}{commit}'
            path = path_fmt.format(url=url,
                                   branch='/trunk',
                                   commit='@{}'.format(commit) if commit else '')

        expected = {'url': url,
                    'repository': None,
                    'type': 'svn',
                    'branch': 'trunk',
                    'commit_as_specified': commit,
                    'commit': commit,
                    'short_commit': commit,
                    'path': path}
        expected['str'] = expected['path']

        if calling_test == 'attrs':
            print(f'\nFixture: GitPath({path})')
            fixture = GitPath(path, root_path=root_path)

        else:
            print(f'\nFixture: GitClone({path})')
            fixture = GitClone(path, root_path=root_path)

        yield expected, fixture

    elif calling_test in ('print', 'rose-conf'):
        branch = {'no_branch': None,
                  'branch': 'branch'}[branch]
        sources = ['/path/to/working_copy',
                   'relative/path/somewhere',
                   '4.2.0',
                   '4.2.0@5cf0c3',
                   'git@forge.nemo-ocean.eu:nemo/nemo.git',
                   'git@forge.nemo-ocean.eu:nemo/nemo.git/4.2.0',
                   'fcm:nemo.xm/NEMO/branches/UKMO',
                   'fcm:nemo.xm/NEMO/branches/UKMO/branches/NEMO_4.0.1_GO8_package_fix']

        # Absolute git paths resolve, no change to project/branch/revision
        expected = {'sources': sources[:]}
        expected['sources'][4] = 'forge.nemo-ocean.eu/nemo/nemo/main/38d68562'
        expected['sources'][5] = 'forge.nemo-ocean.eu/nemo/nemo/4.2.0/5cf0c3d6'

        if calling_test == 'print':
            args = ['print'] + sources + ['-v']
            if root_path:
                args += ['-r', root_path]
            expected = ' '.join(expected['sources'])
            fixture = parse_args(args)

            yield expected, fixture

        else:
            #
            tmp_dir = tempfile.mkdtemp()
            print(f'Created "{tmp_dir}"')

            fname_result = f'{tmp_dir}/result.conf'
            fname_in = test_conf(tmp_dir, 'in', sources, root_path, branch, commit)
            fname_exp = test_conf(tmp_dir, 'expected', **expected)

            args = ['rose-conf', fname_in, 'nemo_sources', '-v', '-o', fname_result]
            fixture = parse_args(args)

            yield fname_result, fname_exp, fixture

            shutil.rmtree(tmp_dir)
            print(f'Removed "{tmp_dir}"')
    else:
        msg = f'No fixture implemented for calling_test="{calling_test}"'
        raise ValueError(msg)


@pytest.fixture
def filepath_fixture(path_type, calling_test):
    """"""
    url = {'absolute': '/test/path/to/repository',
           'relative': 'relative/path/to/repository'}[path_type]
    _type = {'absolute': 'localpath',
             'relative': 'relativepath'}[path_type]

    path = url

    expected = {'url': url,
                'repository': None,
                'type': _type,
                'branch': None,
                'commit_as_specified': None,
                'commit': None,
                'short_commit': None,
                'path': path,
                'str': path}

    if calling_test == 'attrs':
        print(f'\nFixture: GitPath({path})')
        fixture = GitPath(path)
    elif calling_test in ('clone', 'checkout'):
        print(f'\nFixture: GitClone({path})')
        fixture = GitClone(path)
    else:
        msg = f'No fixture implemented for calling_test="{calling_test}"'
        raise ValueError(msg)

    return expected, fixture


@pytest.fixture
def otherpath_fixture(url_type, calling_test):
    """"""
    url = {'rhost': 'host:/path/to/remote/repository',
           'rhost_user': 'user@host:/path/to/remote/repository'}[url_type]

    expected = {'url': url,
                'repository': None,
                'type': 'other',
                'branch': None,
                'commit_as_specified': None,
                'commit': None,
                'short_commit': None,
                'path': url,
                'str': url}

    if calling_test == 'attrs':
        print(f'\nFixture: GitPath({expected["path"]})')
        fixture = GitPath(expected['path'])
    elif calling_test in ('clone', 'checkout'):
        print(f'\nFixture: GitClone({expected["path"]})')
        fixture = GitClone(expected['path'])
    else:
        msg = f'No fixture implemented for calling_test="{calling_test}"'
        raise ValueError(msg)

    return expected, fixture


def test_conf(clone_dir, fname, sources=None, project=None, branch=None, revision=None):
    """"""
    fname_conf = f'{clone_dir}/{fname}.conf'

    with open(fname_conf, 'w') as fh:
        conf = configparser.ConfigParser()
        conf.add_section('env')
        if sources is not None:
            conf.set('env', 'nemo_sources', ' '.join(sources) if sources else '')
        if project is not None:
            conf.set('env', 'nemo_project_location', project if project else '')
        if branch is not None:
            conf.set('env', 'nemo_base', branch if branch else '')
        if revision is not None:
            conf.set('env', 'nemo_rev', revision if revision else '')
        conf.write(fh)
        fh.seek(0)

    return fname_conf


def pytest_generate_tests(metafunc):
    """Parameterises and renames tests generated with use_fixture"""
    fixtures = getattr(metafunc.function, '_fixtures', None)

    if fixtures:
        names = list(fixtures.keys())
        params = [i if isinstance(i, (list, tuple)) else [i] for i in fixtures.values()]
        params_prod = list(itertools.product(*params))
        ids = ['-'.join([j for i_j, j in enumerate(i) if len(params[i_j]) > 1]) for i in params_prod]
        metafunc.parametrize(names, params_prod, ids=ids, scope='function')


# Mocks for external commands
def git_patch():
    """"""
    actual_popen = subprocess.Popen

    def git_mock(exe, **kwargs):
        if exe[0] == 'git':
            p = mock.Mock()
            stdout = ''
            stderr = ''

            if exe[1] == 'ls-remote':
                branch = exe[4]
                if branch == 'main':
                    stdout = '38d6856256fa965ad93fdf3ee241d2dd2431575f\trefs/heads/main\n'
                else:
                    stdout = (f'f784e73a73fda53b8bc56b424756911e8efd72f8\trefs/tags/{branch}\n' +
                              f'5cf0c3d61b751a102fe9de9c8ffe61a7216946cc\trefs/tags/{branch}^{{}}\n')
            elif exe[1] == 'clone':
                stdout = ' '.join(exe)
            elif exe[1] == 'checkout':
                stdout = ' '.join(exe)
            else:
                raise ValueError(f'No mock implemented for "git {exe[1]}"')

            p.returncode = 1 if stderr else 0
            p.communicate.return_value = (stdout, stderr)
        else:
            msg = f'Command will not be mocked: {" ".join(exe)}'
            warnings.warn(msg)
            p = actual_popen(exe, **kwargs)

        return p

    patch = mock.patch('subprocess.Popen', spec_set=subprocess.Popen, side_effect=git_mock)

    return patch
