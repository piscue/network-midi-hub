import os
import sys


sys.path.insert(0, 
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client import *


def test_get_args_defaults():
    args = get_args()
    assert args.host == '127.0.0.1'
    assert args.port == 8141
    assert args.thru == False


def test_matches_transport():
    matches = matches_transport('[111]')
    assert len(matches) == 1
    matches = matches_transport('[111][112]')
    assert len(matches) == 2
    assert matches == ['[111]', '[112]']
    # TODO messeges between transport messages


def test_check_transports():
    msg_list = check_transports('[204][205]', [])
    assert len(msg_list) == 2
