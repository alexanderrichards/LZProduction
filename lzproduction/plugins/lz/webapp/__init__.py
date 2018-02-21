import os


def modify_argparser(parser, lzprod_root):
    parser.add_argument('-r', '--git-repo', default='git@lz-git.ua.edu:sim/TDRAnalysis.git',
                        help="Git repo url [default: %(default)s]")
    parser.add_argument('-g', '--git-dir', default=os.path.join(lzprod_root, 'git', 'TDRAnalysis'),
                        help="Path to the directory where to clone TDRAnalysis git repo "
                             "[default: %(default)s]")