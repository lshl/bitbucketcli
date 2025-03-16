#!/usr/bin/env python3

'''
Module that provides a command line interface to interact with Bitbucket.

Module requirements:
1. use atlassian-python-api module.
2. Accepts command line switches (e.g. --help, -h, --version, --tests, -T) using argparse module.
3. Python 3.6 compatible.
4. Username and password:
  4.1. May receive cloud user name and password via command line (--user, -u, --password, -p).
  4.2. May receive cloud user name and password via environment variable (BITBUCKET_USER,
       BITBUCKET_PASSWORD).
  4.3. Fail if no username is given.
  4.4. If no password is given, prompt for it.
5. With the switch --workspaces-list or -w lists all workspaces under the given account.
6. With the switch --tests or -T runs unit tests with 100% coverage.
  6.1. The tests shall be run with the command python3 -m unittest <model name>.
  6.2. The tests shall be run with the command coverage run <model name>.
  6.3. The tests shall be run with the command coverage report.
  6.4. The tests shall be run with the command coverage report -m.
  6.5. The tests shall be run with the command coverage html.
  6.6. The tests shall be run with the command coverage xml.
  6.7. The tests shall be run with the command coverage erase.
  6.8. The tests shall be run with the command coverage combine.
  6.9. The tests shall be run with the command coverage annotate.
  6.10. The tests shall be run with the command coverage html -d coverage_html.
  6.11. The tests shall be run with the command coverage xml -o coverage.xml.
  6.12. The tests shall be run with the command coverage report -m --fail-under=100.
  6.13. The tests shall be run with the command coverage report -m --fail-under=100
        --skip-covered.
  6.14. The tests shall be run with the command coverage report -m --fail-under=100
        --skip-covered --show-missing.
  6.15. The tests shall be run with the command coverage report -m --fail-under=100
        --skip-covered --show-missing --include=<model name>.
  6.16. The tests shall be run with the command coverage report -m --fail-under=100
        --skip-covered --show-missing --include=<model name> --omit=<model name>.
  6.17. The tests shall be run with the command coverage report -m --fail-under=100
        --skip-covered --show-missing --include=<model name> --omit=<model name>
        --ignore-errors.
  6.18. The tests shall receive the username and password from the environment
        variables BITBUCKET_USER and BITBUCKET_PASSWORD or from the command line.
7. The module shall be executable from the command line.
8. The module shall be importable as a library.
9. The module shall be testable with unittest.
10. The module shall be documented.
11. The module shall be PEP8 compliant.
12. The module shall be type annotated.
13. The switch --version shall print the version of the module.
14. The module shall be versioned.
15. The switches -T and -w shall be mutually exclusive.
'''

import argparse
import getpass
import os
import sys # pylint:disable=unused-import
import unittest

import atlassian

__version__ = "1.0"

class BitbucketCLIRepositoryWrapper(atlassian.bitbucket.cloud.repositories.Repository):
    """
    A class for representing a Bitbucket repository.
    """
    def __init__(self, repository: atlassian.bitbucket.cloud.repositories.Repository):
        if None is repository:
            raise ValueError("repository is None")
        if not isinstance(repository,
                          atlassian.bitbucket.cloud.repositories.Repository):
            raise TypeError("repository is not an instance of " +
                            "atlassian.bitbucket.cloud.repositories.Repository")
        super().__init__(repository.data, **repository._new_session_args) # pylint:disable=protected-access

    @property
    def links(self):
        """
        The links of the repository.
        """
        return self.data.get("links")

    @property
    def https_url(self):
        """
        The HTTPS URL of the repository.
        """
        return self.links['clone'][0]['href']

    @property
    def ssh_url(self):
        """
        The SSH URL of the repository.
        """
        return self.links['clone'][1]['href']

class BitbucketCLIProjectWrapper(atlassian.bitbucket.cloud.workspaces.projects.Project):
    """
    A class for representing a Bitbucket project.
    """
    def __init__(self, project: atlassian.bitbucket.cloud.workspaces.projects.Project):
        if None is project:
            raise ValueError("project is None")
        if not isinstance(project, atlassian.bitbucket.cloud.workspaces.projects.Project):
            raise TypeError("project is not an instance of " +
                            "atlassian.bitbucket.Cloud.projects.Project")
        super().__init__(project.data, **project._new_session_args) # pylint:disable=protected-access
        self.__inner_project = project

    def __getitem__(self, key):
        return BitbucketCLIRepositoryWrapper(self.repositories.get(key))

class BitbucketCLIWorkspaceWrapper(atlassian.bitbucket.cloud.workspaces.Workspace):
    """
    A class for representing a Bitbucket workspace.
    """
    def __init__(self, workspace: atlassian.bitbucket.cloud.workspaces.Workspace):
        if None is workspace:
            raise ValueError("workspace is None")
        if not isinstance(workspace, atlassian.bitbucket.cloud.workspaces.Workspace):
            raise TypeError("workspace is not an instance of " +
                            "atlassian.bitbucket.Cloud.workspaces.Workspace")
        super().__init__(workspace.data, **workspace._new_session_args) # pylint:disable=protected-access
        self.__inner_workspace = workspace

    def __getitem__(self, key):
        return BitbucketCLIProjectWrapper(
            self.__inner_workspace.projects.get(key))

class BitbucketWrapper: # pylint:disable=too-few-public-methods
    """
    A class for interacting with Bitbucket using the command-line interface.

    Args:
        username (str): The username for authentication.
        password (str): The password for authentication.
    """
    def __init__(self, username: str, password: str):
        self.__cloud = atlassian.bitbucket.Cloud(username=username, password=password)

    @property
    def workspaces(self) -> atlassian.bitbucket.cloud.workspaces.Workspaces:
        """
        A generator for the Workspace objects.

        API docs: https://developer.atlassian.com/bitbucket/api/2/reference/resource/workspaces#get.
        """
        return self.__cloud.workspaces

    def __getitem__(self, key):
        return BitbucketCLIWorkspaceWrapper(self.workspaces.get(key))

class BitbucketCLI:
    """
    A class for the Bitbucket Command Line Interface.

    Args:
        username (str): The username for authentication.
        password (str): The password for authentication
    """
    def __init__(self):
        self.__parser = None
        self.__args = None
        self.__for_scripting = False
        self.__username = None
        self.__password = None
        self.__bbc = None
        self.__parse_arguments()

    @property
    def args(self) -> argparse.Namespace:
        """Returns the arguments of the object."""
        return self.__args

    @property
    def bbc(self) -> BitbucketWrapper:
        """
        Returns an instance of the BitbucketWrapper class.

        If the instance has not been created yet, it will be created using
        the provided username and password.

        Returns:
            BitbucketWrapper: An instance of the BitbucketWrapper class.
        """
        if None is self.__bbc:
            self.__bbc = BitbucketWrapper(self.__username, self.__password)
        return self.__bbc

    def __create_workspace_subparser(self, subparser: argparse.ArgumentParser): # pylint:disable=no-self-use
        grp1 = subparser.add_mutually_exclusive_group(required=True)
        grp1.add_argument('--list', '-l', action='store_true', help='Lists all workspaces')
        grp1.add_argument('--workspace', '-w', type=str, help='Workspace name')

    def __create_project_subparser(self, subparser: argparse.ArgumentParser): # pylint:disable=no-self-use
        subparser.add_argument('--workspace', '-w', type=str, help='Workspace name', required=True)
        grp2 = subparser.add_mutually_exclusive_group(required=True)
        grp2.add_argument('--list', '-l', action='store_true', help='Lists all projects')
        grp2.add_argument('--project', '-P', type=str, help='Project name')

    def __create_repository_subparser(self, subparser: argparse.ArgumentParser):
        subparser.add_argument('--workspace', '-w', type=str, help='Workspace name', required=True)
        subparser.add_argument('--project', '-P', type=str, help='Project name', required=True)
        grp3 = subparser.add_mutually_exclusive_group(required=True)
        grp3.add_argument('--list', '-l', action='store_true', help='Lists all repositories')
        grp3.add_argument('--repository', '-r', type=str, help='Repository name')
        subparser_subs = subparser.add_subparsers(dest='repo_subcommand', help='repository actions')
        subparser_sub1 = subparser_subs.add_parser('show',
                                                   help='shows information about repository')
        subparser_sub2 = subparser_subs.add_parser('create', help='creates a new repository')

        subparser_sub1.add_argument('--links', '-L', action='store_true',
                                    help='Print repository links')
        subparser_sub1.add_argument('--https-url', '-u', action='store_true',
                                    help='Print repository HTTPS clone URL')
        subparser_sub1.add_argument('--ssh-url', '-s', action='store_true',
                                    help='Print repository SSH clone URL')

        grp421 = subparser_sub2.add_mutually_exclusive_group()
        grp421.add_argument('--public', action='store_true',
                            help='Create a public repository (Uses bitbucket default if omitted)')
        grp421.add_argument('--private', action='store_true',
                            help='Create a private repository (Uses bitbucket default if omitted)')
        grp422 = subparser_sub2.add_mutually_exclusive_group()
        grp422.add_argument('--allow-forks', action='store_true',
                           help='Allows forks for the created repository')
        grp422.add_argument('--no-allow-forks', action='store_true',
                           help='Disallows forks for the created repository')
        grp422.add_argument('--no-public-forks', action='store_true',
                           help='Disallows public forks for the created repository')

        temp_args = self.__parser.parse_known_args()
        # temp_args = self.__parser.parse_known_args(sys.argv[1:], argparse.Namespace())
        has_repo = temp_args[0].subcommand == "repository" or temp_args[0].subcommand == "repo"
        has_repo_name = False
        if has_repo:
            has_repo_name = temp_args[0].repository is not None
        subparser_subs.required = has_repo_name

    def __get_parser(self):
        help_at_start = True
        self.__parser = argparse.ArgumentParser(description='Bitbucket Command Line Tool',
                                                add_help=help_at_start)
        self.__parser.add_argument('--version', '-v', action='version',
                                   version=f'%(prog)s Bitbucket CLI {__version__}')
        self.__parser.add_argument('--user', '-u', help='Bitbucket username (not email)')
        self.__parser.add_argument('--password', '-p', help='Bitbucket password')
        self.__parser.add_argument('--for-scripting', '-0', action='store_true',
                                   help='Outputs will be concise and easy to parse')

        subparsers = self.__parser.add_subparsers(dest='subcommand', help='sub commands')
        subparsers.required = True
        subparser1 = subparsers.add_parser('tests', help='Run unit tests') # pylint:disable=unused-variable
        subparser2 = subparsers.add_parser('workspace', help='Workspace operations')
        subparser3 = subparsers.add_parser('project', help='Project operations')
        subparser4 = subparsers.add_parser('repository', aliases=['repo'],
                                           help='Repository operations')

        self.__create_workspace_subparser(subparser2)
        self.__create_project_subparser(subparser3)
        self.__create_repository_subparser(subparser4)

        if not help_at_start:
            self.__parser.add_argument('--help', '-h', action='help',
                                       help='Show this help message and exit')

    def __args_verify_repo_show_actions(self):
        if self.args.links:
            if self.args.subcommand != "repository" and self.args.subcommand != "repo":
                self.__parser.error("Error: --links (-L) is only valid for repository operations.")
            else:
                if self.args.repository is None:
                    self.__parser.error("Error: --repository (-r) is required with --links (-L).")
                else:
                    # print(f"Repository links: {args.links}")
                    pass

        if self.args.https_url:
            if self.args.subcommand != "repository" and self.args.subcommand != "repo":
                self.__parser.error("Error: --https-url (-u) " +
                                    "is only valid for repository operations.")
            else:
                if self.args.repository is None:
                    self.__parser.error("Error: --repository (-r) " +
                                        "is required with --https-url (-u).")
                else:
                    # print(f"HTTPS URL: {args.https_url}")
                    pass

        if self.args.ssh_url:
            if self.args.subcommand != "repository" and self.__args.subcommand != "repo":
                self.__parser.error("Error: --ssh-url (-s) " +
                                    "is only valid for repository operations.")
            else:
                if self.args.repository is None:
                    self.__parser.error("Error: --repository (-r) is required with --ssh-url (-s).")
                else:
                    # print(f"SSH URL: {args.ssh_url}")
                    pass

    def __args_verify_repo_actions(self):
        if self.args.repo_subcommand == "show":
            self.__args_verify_repo_show_actions()

    def __parse_arguments(self):
        self.__get_parser()

        # print("sys.argv: ", sys.argv)
        self.__args = self.__parser.parse_args()

        self.__username = self.args.user or os.environ.get("BITBUCKET_USER")
        self.__password = self.args.password or os.environ.get("BITBUCKET_PASSWORD")

        if self.args.subcommand == "repository" or self.args.subcommand == "repo":
            self.__args_verify_repo_actions()

        if self.__username is None and self.args.subcommand != "tests":
            self.__parser.error("Error: Bitbucket username is required.")

        if self.__password is None and self.args.subcommand != "tests":
            self.__password = getpass.getpass("Enter Bitbucket password: ")

    def __list_workspaces(self):
        """
        List all workspaces in Bitbucket.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.

        Returns:
            None
        """
        for workspace in self.bbc.workspaces.each():
            #print(dir(workspace))
            #print(type(workspace))
            print(f"Workspace: {workspace.name} ({workspace.slug})")

    def __list_projects(self, workspace: BitbucketCLIWorkspaceWrapper):
        """
        List all projects in a workspace.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.
            workspace_name (str): The name of the workspace.

        Returns:
            None
        """
        prefix = "Project: "
        if self.__for_scripting:
            prefix = ""
        for project in workspace.projects.each():
            print(prefix + f"{project.name} ({project.key})")

    def __list_repositories(self,
                            project: BitbucketCLIProjectWrapper,
                            workspace: BitbucketCLIWorkspaceWrapper):
        """
        List all repositories in a project.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.
            workspace_name (str): The name of the workspace.
            project_name (str): The name of the project.

        Returns:
            None
        """
        prefix = "Repository: "
        suffix = f" in Project: {project.name} ({project.key}) in "
        suffix += f"Workspace: {workspace.name} ({workspace.slug})"
        if self.__for_scripting:
            prefix = ""
            suffix = ""
        for repository in project.repositories.each():
            print(prefix + f"{repository.name} ({repository.slug}) in " + suffix)

    def __print_repository_links(self,
                                 repository: BitbucketCLIRepositoryWrapper):
        """
        Print the links of a repository.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.
            workspace_name (str): The name of the workspace.
            project_name (str): The name of the project.
            repository_name (str): The name of the repository.

        Returns:
            None
        """
        links = repository.links
        #print(f"Repository links: '{links}' (type: {type(links)}) (dir: {dir(links)})")
        prefix = "Link: "
        if self.__for_scripting:
            prefix = ""
        for link in links:
            print(prefix + f"{link} -> {links[link]}")

    def __print_repository_https_url(self,
                                     repository: str):
        """
        Print the HTTPS URL of a repository.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.
            workspace_name (str): The name of the workspace.
            project_name (str): The name of the project.
            repository_name (str): The name of the repository.

        Returns:
            None
        """
        if self.__for_scripting:
            print(f"{repository.https_url}")
        else:
            print(f"HTTPS URL: {repository.https_url}")

    def __print_repository_ssh_url(self,
                                   repository: BitbucketCLIRepositoryWrapper):
        """
        Print the SSH URL of a repository.

        Args:
            bitbucket_cli (BitbucketCLI): An instance of the BitbucketCLI class.
            workspace_name (str): The name of the workspace.
            project_name (str): The name of the project.
            repository_name (str): The name of the repository.

        Returns:
            None
        """
        if self.__for_scripting:
            print(f"{repository.ssh_url}")
        else:
            print(f"SSH URL: {repository.ssh_url}")

    def create_repository(self, # pylint:disable=no-self-use,too-many-arguments
                          project: BitbucketCLIProjectWrapper,
                          workspace: BitbucketCLIWorkspaceWrapper,
                          repository_name: str,
                          is_private=None,
                          fork_policy=None) -> BitbucketCLIRepositoryWrapper:
        """
        Create a repository in a project in a workspace.
        """
        if project is None:
            raise ValueError("project is None")
        if not isinstance(project, BitbucketCLIProjectWrapper):
            raise TypeError("project is not an instance of BitbucketCLIProjectWrapper")
        if workspace is None:
            raise ValueError("workspace is None")
        if not isinstance(workspace, BitbucketCLIWorkspaceWrapper):
            raise TypeError("workspace is not an instance of BitbucketCLIWorkspaceWrapper")
        if repository_name is None:
            raise ValueError("repository_name is None")
        if not isinstance(repository_name, str):
            raise TypeError("repository_name is not a string")
        if fork_policy is not None and fork_policy not in atlassian.bitbucket.cloud.repositories.WorkspaceRepositories.FORK_POLICIES: # pylint:disable=line-too-long
            raise ValueError("fork_policy is not a valid value")
        repository = workspace.repositories.create(repository_name,
                                                   project.key,
                                                   is_private,
                                                   fork_policy)
        return BitbucketCLIRepositoryWrapper(repository)

    def __create_repository(self,
                            project: BitbucketCLIProjectWrapper,
                            workspace: BitbucketCLIWorkspaceWrapper):
        is_private = None
        if self.args.public:
            is_private = False
        if self.args.private:
            is_private = True

        fork_policy = None
        if self.args.allow_forks:
            fork_policy = atlassian.bitbucket.cloud.repositories.WorkspaceRepositories.ALLOW_FORKS
        elif self.args.no_allow_forks:
            fork_policy = atlassian.bitbucket.cloud.repositories.WorkspaceRepositories.NO_FORKS
        elif self.args.no_public_forks:
            fork_policy = atlassian.bitbucket.cloud.repositories.WorkspaceRepositories.NO_PUBLIC_FORKS # pylint:disable=line-too-long

        repository_slug = self.args.repository
        repository = self.create_repository(project,
                                            workspace,
                                            repository_slug,
                                            is_private,
                                            fork_policy)
        if repository is not None:
            if not self.__for_scripting:
                print(f"Repository: {repository.name} created in " +
                      f"Project: {project.name} in Workspace: {workspace.name}")

    def repo_cmd(self):
        """
        Perform repository operations based on the provided arguments.

        Args:
            parser: The argument parser object.
            args: The parsed command-line arguments.
            bbc: The Bitbucket client object.

        Returns:
            None
        """
        if self.args.workspace is None:
            self.__parser.error("Error: --workspace (-w) is required for repository operations!")
        workspace_name = self.args.workspace
        # print(f'workspace_name: {workspace_name}')
        workspace = self.bbc[workspace_name]
        if self.args.project is None:
            self.__parser.error("Error: --project (-P) is required for repository operations!")
        project_name = self.args.project
        # print("listing projects")
        # _list_projects(workspace)
        # print("listed projects")
        # print("listing projects")
        # _list_projects(bbc.workspaces.get(workspace_name))
        # print("listed projects")
        # pexist = workspace.projects.exists(project_name)
        # print(f"Project exists: {pexist}")
        project = workspace[project_name]
        if self.args.list:
            self.__list_repositories(project, workspace)
        elif self.args.repository is not None:
            repository_name = self.args.repository
            if self.args.repo_subcommand == "show":
                self.repo_show_cmd(workspace, project, repository_name)
            elif self.args.repo_subcommand == "create":
                self.__create_repository(project, workspace)
            else:
                self.__parser.print_help()
        else:
            self.__parser.print_help()

    def repo_show_cmd(self,
                      workspace: BitbucketCLIWorkspaceWrapper,
                      project: BitbucketCLIProjectWrapper,
                      repository_name: str):
        """
        Show information about a repository.

        Args:
            workspace (BitbucketCLIWorkspaceWrapper): The workspace containing the repository.
            project (BitbucketCLIProjectWrapper): The project containing the repository.
            repository_name (str): The name of the repository.

        Returns:
            None
        """
        repository = project[repository_name]
        if not self.__for_scripting:
            print(f"Repository: {repository.name} in " +
                  f"Project: {project.name} in Workspace: {workspace.name}")
        if self.args.links:
            self.__print_repository_links(repository)
        if self.args.https_url:
            self.__print_repository_https_url(repository)
        if self.args.ssh_url:
            self.__print_repository_ssh_url(repository)
        if not self.args.links and not self.args.https_url and not self.args.ssh_url:
            self.__parser.print_help()

    def project_cmd(self):
        """
        Perform operations related to projects.

        Args:
            parser (argparse.ArgumentParser): The argument parser object.
            args (argparse.Namespace): The parsed command-line arguments.
            bbc (BitbucketClient): The Bitbucket client object.

        Raises:
            argparse.ArgumentError: If --workspace (-w) is not provided.

        Returns:
            None
        """
        if self.args.workspace is None:
            self.__parser.error("Error: --workspace (-w) is required for project operations!")
        workspace_name = self.args.workspace
        workspace = self.bbc[workspace_name]
        if self.args.list:
            self.__list_projects(workspace)
        elif self.args.project is not None:
            project_name = self.args.project
            project = workspace[project_name]
            if not self.__for_scripting:
                print(f"Project: {project.name} ({project.key})")
        else:
            self.__parser.print_help()

    def workspace_cmd(self):
        """
        Perform operations related to workspaces.

        Args:
            parser (argparse.ArgumentParser): The argument parser object.
            args (argparse.Namespace): The parsed command-line arguments.
            bbc (BitbucketClient): The Bitbucket client object.

        Returns:
            None
        """
        if self.args.list:
            self.__list_workspaces()
        elif self.args.workspace is not None:
            workspace_name = self.args.workspace
            workspace = self.bbc[workspace_name] # pylint:disable=unused-variable
            if not self.__for_scripting:
                print(f"Workspace: {workspace.name} ({workspace.slug})")
        else:
            # self.__parser.error("Error: Either --workspace (-w) or --list (-w) must be supplied!")
            self.__parser.print_help()

    def main_program(self):
        """
        Executes the main program based on the subcommand provided.

        If the subcommand is 'workspace', it calls the 'workspace_cmd' method.
        If the subcommand is 'project', it calls the 'project_cmd' method.
        If the subcommand is 'repository' or 'repo', it calls the 'repo_cmd' method.
        Otherwise, it prints the help message.
        """
        if self.args.subcommand == "workspace":
            self.workspace_cmd()
        elif self.args.subcommand == "project":
            self.project_cmd()
        elif self.args.subcommand == "repository" or self.args.subcommand == "repo":
            self.repo_cmd()
        else:
            self.__parser.print_help()

def main():
    """
    Main function of the Bitbucket CLI tool.
    Parses command line arguments and performs the corresponding actions.
    """
    bitbucket_cli = BitbucketCLI()
    if bitbucket_cli.args.subcommand == "tests":
        unittest.main(argv=[__file__])
    else:
        bitbucket_cli.main_program()

if __name__ == '__main__':
    main()
